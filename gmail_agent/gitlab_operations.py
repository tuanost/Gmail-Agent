"""
Module xử lý các thao tác với Gitlab từ email.
Module này cung cấp các chức năng xử lý email từ Gitlab, phân tích và trích xuất thông tin.
"""

import re
import requests
from bs4 import BeautifulSoup
import base64
import logging
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

# Import các module liên quan
from gmail_agent.gitlab_auth import check_pipeline_url_accessibility

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import tùy chọn cho mock data (nếu URL pipeline không thể truy cập)
try:
    from gmail_agent.pipeline_mock_handler import integrate_mock_pipeline_logs_to_gitlab_analysis
    MOCK_HANDLER_AVAILABLE = True
except ImportError:
    MOCK_HANDLER_AVAILABLE = False

# Import module phân tích AI
try:
    from gmail_agent.pipeline_ai_analyzer import (
        analyze_pipeline_error_with_ai,
        discover_available_models,
        list_ollama_models
    )
    OPEN_AI_ANALYZER_AVAILABLE = True
except ImportError:
    OPEN_AI_ANALYZER_AVAILABLE = False

def extract_raw_html_content(message):
    """
    Trích xuất nội dung HTML gốc từ email để xử lý các hyperlink.

    Args:
        message: Đối tượng tin nhắn từ Gmail API

    Returns:
        Chuỗi HTML gốc của email
    """
    parts = []

    # Hàm để đệ quy trích xuất các phần
    def get_html_parts(payload):
        if 'parts' in payload:
            for part in payload['parts']:
                get_html_parts(part)
        elif 'body' in payload and 'data' in payload['body']:
            mime_type = payload.get('mimeType', '')
            if mime_type == 'text/html':
                parts.append(payload['body']['data'])

    # Bắt đầu đệ quy từ payload gốc
    if 'payload' in message:
        get_html_parts(message['payload'])

    # Nếu có phần HTML, giải mã base64
    if parts:
        combined_content = ''.join(parts)
        try:
            decoded_bytes = base64.urlsafe_b64decode(combined_content)
            html_content = decoded_bytes.decode('utf-8')
            return html_content
        except Exception as e:
            print(f"Lỗi khi giải mã nội dung HTML: {str(e)}")

    return ""

def is_gitlab_pipeline_email(message, sender_filter="git_nhs@bidv.com.vn"):
    """
    Kiểm tra xem email có phải là thông báo từ Gitlab về pipeline hay không.

    Args:
        message: Đối tượng tin nhắn từ Gmail API
        sender_filter: Địa chỉ email của hệ thống Gitlab (mặc định là git_nhs@bidv.com.vn)

    Returns:
        True nếu là email thông báo từ Gitlab về pipeline, ngược lại False
    """
    # Kiểm tra người gửi
    from gmail_agent.gmail_operations import get_sender
    sender = get_sender(message)

    if sender_filter not in sender:
        return False

    # Kiểm tra tiêu đề email có chứa từ khóa pipeline
    from gmail_agent.gmail_operations import get_email_subject
    subject = get_email_subject(message)

    return "pipeline" in subject.lower()

def is_failed_pipeline_email(message):
    """
    Kiểm tra xem email có phải là thông báo về pipeline thất bại hay không.

    Args:
        message: Đối tượng tin nhắn từ Gmail API

    Returns:
        True nếu là email thông báo pipeline thất bại, ngược lại False
    """
    if not is_gitlab_pipeline_email(message):
        return False
    from gmail_agent.gmail_operations import get_email_subject
    subject = get_email_subject(message).lower()
    return "failed pipeline" in subject

def extract_pipeline_url(message):
    """
    Trích xuất URL của pipeline từ email Gitlab.

    Args:
        message: Đối tượng tin nhắn từ Gmail API

    Returns:
        URL của pipeline hoặc None nếu không tìm thấy
    """
    # Lấy nội dung HTML
    html_content = extract_raw_html_content(message)

    if not html_content:
        return None

    # Sử dụng BeautifulSoup để phân tích HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # Tìm các liên kết chứa từ khóa "pipeline"
    pipeline_links = []
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and 'pipeline' in href.lower():
            pipeline_links.append(href)

            # Nếu từ "Pipeline" nằm trong văn bản của liên kết, đây có thể là liên kết chính
            if link.text and "pipeline" in link.text.lower():
                return href

    # Trả về liên kết đầu tiên tìm thấy nếu không tìm thấy liên kết chính
    return pipeline_links[0] if pipeline_links else None

def extract_job_urls(message):
    """
    Trích xuất trực tiếp các URL job từ email Gitlab và tên step tương ứng.

    Args:
        message: Đối tượng tin nhắn từ Gmail API

    Returns:
        Dict[str, str]: Mapping từ tên step đến job URL
    """
    import re
    html_content = extract_raw_html_content(message)
    job_map = {}

    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        job_url_pattern = re.compile(r"https?://[\w\.-]+.*/-/jobs/\d+")
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and job_url_pattern.match(href):
                # Try to get step name from anchor text
                step_name = link.text.strip()
                # If anchor text is empty, try to get from previous sibling or parent
                if not step_name:
                    parent = link.parent
                    if parent:
                        # Try previous sibling text
                        prev = link.find_previous(string=True)
                        if prev:
                            step_name = prev.strip()
                        # Try parent text
                        elif parent.text:
                            step_name = parent.text.strip()
                # Fallback: use job URL as step name if not found
                if not step_name:
                    step_name = href
                job_map[step_name] = href
    else:
        payload = message.get('payload', {})
        text_content = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                    try:
                        text_content += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    except Exception:
                        pass
        elif 'body' in payload and 'data' in payload['body']:
            try:
                text_content += base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            except Exception:
                pass
        job_url_pattern = re.compile(r"https?://[\w\.-]+.*/-/jobs/\d+")
        for match in job_url_pattern.finditer(text_content):
            url = match.group(0)
            # Fallback: use URL as step name
            job_map[url] = url

    print("Danh sách job URLs:")
    for step, url in job_map.items():
        print(f"{step}: '{url}',")
    return job_map

def extract_pipeline_logs(pipeline_url):
    """
    Truy cập URL pipeline để lấy log lỗi.

    Args:
        pipeline_url: URL của pipeline cần truy cập

    Returns:
        Dictionary chứa thông tin log và lỗi
    """
    if not pipeline_url:
        return {
            "success": False,
            "error": "Không có URL pipeline",
            "logs": None
        }

    try:
        # Truy cập URL pipeline
        response = requests.get(pipeline_url, timeout=10)
        if response.status_code >= 400:
            return {
                "success": False,
                "error": f"Không thể truy cập URL. Mã trạng thái: {response.status_code}",
                "logs": None
            }

        # Phân tích HTML để lấy log
        soup = BeautifulSoup(response.text, 'html.parser')

        # Tìm thẻ chứa log errors
        error_sections = []

        # Tìm phần chứa log lỗi (có thể thay đổi tùy theo cấu trúc trang Gitlab)
        log_containers = soup.find_all('div', class_='job-log')
        if not log_containers:
            log_containers = soup.find_all('pre', class_='build-log')
        if not log_containers:
            log_containers = soup.find_all('div', class_='build-trace')

        # Thử tìm phần logs theo nhiều cách khác nhau
        logs_text = ""
        error_lines = []

        # Nếu tìm thấy container chứa log
        if log_containers:
            for container in log_containers:
                logs_text += container.get_text() + "\n"

            # Tìm các dòng có chứa lỗi trong log
            for line in logs_text.split('\n'):
                if any(err_term in line.lower() for err_term in ['error', 'exception', 'failed', 'failure', 'lỗi']):
                    error_lines.append(line.strip())
        else:
            # Nếu không tìm thấy container cụ thể, tìm tất cả các phần tử có chứa thông tin lỗi
            for elem in soup.find_all(['div', 'span', 'p']):
                text = elem.get_text().strip()
                if any(err_term in text.lower() for err_term in ['error', 'exception', 'failed', 'failure', 'lỗi']):
                    error_lines.append(text)

        # Tìm nút/liên kết đến trang job details nếu có
        job_links = []
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and ('job' in href or 'build' in href) and 'pipeline' in href:
                job_links.append(href)

        # Nếu không tìm thấy lỗi cụ thể, ghi lại toàn bộ logs để phân tích
        return {
            "success": True,
            "error": None,
            "logs": logs_text[:5000] if logs_text else None,  # Giới hạn độ dài để tránh quá tải
            "error_lines": error_lines[:20],  # Chỉ lấy 20 dòng lỗi đầu tiên
            "job_links": job_links[:5]  # Lưu các liên kết đến job details
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Kết nối đến URL pipeline bị time out",
            "logs": None
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Không thể kết nối đến URL pipeline",
            "logs": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Lỗi khi truy cập URL pipeline: {str(e)}",
            "logs": None
        }

def extract_project_info_from_email(message):
    """
    Trích xuất thông tin dự án từ email Gitlab.

    Args:
        message: Đối tượng tin nhắn từ Gmail API

    Returns:
        Dictionary chứa thông tin dự án (project_name, commit_id, environment)
    """
    from gmail_agent.gmail_operations import get_email_subject
    subject = get_email_subject(message)

    # Khởi tạo kết quả
    project_info = {
        "project_name": "",
        "commit_id": "",
        "environment": ""
    }

    # Trích xuất tên dự án và commit ID từ tiêu đề
    # Mẫu thường gặp: "project-name  Pipeline status  commit-id"
    parts = subject.split()

    # Tìm các phần tử tiêu đề
    for i, part in enumerate(parts):
        # Tìm tên dự án (thường là phần đầu tiên)
        if i == 0 and not project_info["project_name"]:
            project_info["project_name"] = part

        # Tìm commit ID (thường là phần cuối và có dạng mã hash)
        if i == len(parts) - 1 and re.match(r'^[0-9a-f]{7,40}$', part):
            project_info["commit_id"] = part

    # Tìm môi trường từ tiêu đề (thường là phần giữa như "for branch-name")
    branch_match = re.search(r'for\s+(\S+)', subject)
    if branch_match:
        project_info["environment"] = branch_match.group(1)

    return project_info

def analyze_gitlab_email(message):
    """
    Phân tích email từ Gitlab để trích xuất thông tin và phân tích lỗi pipeline.

    Args:
        message: Đối tượng tin nhắn từ Gmail API

    Returns:
        Dictionary chứa kết quả phân tích
    """
    # Kiểm tra xem có phải email Gitlab không
    if not is_gitlab_pipeline_email(message):
        return {
            "success": False,
            "error": "Email không phải từ Gitlab"
        }

    # Lấy thông tin cơ bản từ email
    from gmail_agent.gmail_operations import get_sender, get_email_subject
    sender = get_sender(message)
    subject = get_email_subject(message)

    # Trích xuất thông tin dự án
    project_info = extract_project_info_from_email(message) or {}
    project_name = project_info.get("project_name", "Unknown Project")
    commit_id = project_info.get("commit_id", "Unknown Commit")
    environment = project_info.get("environment", "Unknown Environment")

    # Trích xuất trực tiếp job URLs từ email (now returns a dict)
    job_url_map = extract_job_urls(message)
    job_urls = list(job_url_map.values())

    # Khởi tạo kết quả phân tích
    result = {
        "sender": sender,
        "subject": subject,
        "project_name": project_name,
        "commit_id": commit_id,
        "environment": environment,
        "is_failed_pipeline": is_failed_pipeline_email(message),
        "pipeline_url": extract_pipeline_url(message),  # Thêm pipeline_url
        "pipeline_url_accessible": False,  # Mặc định là False
        "accessibility_message": "Chưa kiểm tra khả năng truy cập",  # Thông báo mặc định
        "job_urls": job_url_map,  # Keep mapping for display
        "job_count": len(job_urls) if job_urls else 0,
        "job_logs": None  # Khởi tạo giá trị rỗng cho job_logs
    }

    # Nếu tìm thấy job URLs và đây là email thông báo pipeline thất bại
    if job_urls and result["is_failed_pipeline"]:
        logger.info(f"Đã trích xuất được {len(job_urls)} job URLs từ email")
        logger.info(f"Danh sách job URLs: {job_url_map}")

        from gmail_agent.gitlab_auth import find_and_get_failed_job_log
        job_result = find_and_get_failed_job_log(job_urls)

        if job_result.get('success'):
            job_log = job_result.get('job_log', '')
            job_info = job_result.get('job_info', {})

            log_lines = job_log.splitlines() if job_log else []
            error_lines = [line.strip() for line in log_lines if any(err_term in line.lower() for err_term in ['error', 'exception', 'failed', 'failure', 'lỗi'])]
            error_lines = error_lines[:20]

            job_logs = {
                "success": True,
                "job_links": job_urls,
                "error_lines": error_lines,
                "logs": job_log[:5000] if job_log else None
            }

            result["job_logs"] = job_logs
            result["job_info"] = job_info
            result["job_status"] = job_result.get('job_status', 'unknown')
            result["job_name"] = job_info.get('name', 'Unknown Job')

            # Phân tích lỗi bằng AI nếu có thể
            if job_log:
                try:
                    from gmail_agent.ai_models import AIModelService
                    ai_service = AIModelService()
                    prompt = ai_service._create_gitlab_analysis_prompt(job_log)
                    ai_result = ai_service.analyze_with_prompt(prompt)
                    if isinstance(ai_result, dict):
                        # Chỉ lấy các trường mới: tom_tat, nguyen_nhan, goi_y_chinh_sua
                        result["ai_error_analysis"] = {
                            "tom_tat": ai_result.get("tom_tat", ""),
                            "nguyen_nhan": ai_result.get("nguyen_nhan", ""),
                            "goi_y_chinh_sua": ai_result.get("goi_y_chinh_sua", "")
                        }
                    else:
                        logger.warning("AI analysis result is not a dictionary.")
                except Exception as e:
                    logger.error(f"Lỗi khi phân tích pipeline bằng AI: {str(e)}")
        else:
            logger.warning(f"Không thể lấy log từ job: {job_result.get('error', 'Unknown error')}")
            result["job_error"] = job_result.get('error', 'Unknown error')
            if MOCK_HANDLER_AVAILABLE:
                result = integrate_mock_pipeline_logs_to_gitlab_analysis(result)

    elif MOCK_HANDLER_AVAILABLE and result["is_failed_pipeline"]:
        logger.info("Không tìm thấy job URLs hoặc không lấy được log, sử dụng mock data")
        result = integrate_mock_pipeline_logs_to_gitlab_analysis(result)

    return result
