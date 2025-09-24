"""
Module xử lý các thao tác với Gitlab từ email.
Module này cung cấp các chức năng xử lý email từ Gitlab, phân tích và trích xuất thông tin.
"""

import re
import requests
import json
from bs4 import BeautifulSoup
import base64
import html
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
    from gmail_agent.open_ai_analyzer import (
        analyze_pipeline_error_with_ai,
        list_available_ai_providers,
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
    subject = get_email_subject(message)

    return "failed" in subject.lower()

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
    Trích xuất trực tiếp các URL job từ email Gitlab.

    Args:
        message: Đối tượng tin nhắn từ Gmail API

    Returns:
        List[str]: Danh sách các URL job hoặc danh sách trống nếu không tìm thấy
    """
    # Lấy nội dung HTML
    html_content = extract_raw_html_content(message)

    if not html_content:
        return []

    # Sử dụng BeautifulSoup để phân tích HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # Tìm các liên kết chứa từ khóa "job" hoặc "build"
    job_links = []
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and ('job' in href.lower() or 'build' in href.lower()):
            job_links.append(href)

    return job_links

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

def analyze_pipeline_errors(pipeline_logs):
    """
    Phân tích log lỗi và đưa ra gợi ý cách sửa.

    Args:
        pipeline_logs: Dictionary chứa thông tin log lỗi từ hàm extract_pipeline_logs

    Returns:
        Dictionary chứa phân tích và gợi ý cách sửa
    """
    if not pipeline_logs or not pipeline_logs["success"]:
        return {
            "analysis": "Không thể phân tích do không có dữ liệu log",
            "error_type": "unknown",
            "suggestions": ["Kiểm tra quyền truy cập vào pipeline URL"]
        }

    # Khởi tạo kết quả
    analysis = {
        "analysis": "",
        "error_type": "unknown",
        "suggestions": []
    }

    # Logs để phân tích
    logs = pipeline_logs.get("logs", "")
    error_lines = pipeline_logs.get("error_lines", [])

    # Nếu không có dữ liệu log
    if not logs and not error_lines:
        analysis["analysis"] = "Không tìm thấy log lỗi cụ thể để phân tích"
        analysis["suggestions"].append("Kiểm tra trực tiếp trên giao diện Gitlab để xem chi tiết lỗi")
        return analysis

    # Phân tích các lỗi phổ biến

    # 1. Lỗi xây dựng (Build errors)
    if logs and any(term in logs.lower() for term in ["build failed", "compilation error", "compiler error"]):
        analysis["error_type"] = "build_error"
        analysis["analysis"] = "Phát hiện lỗi trong quá trình xây dựng (build)"

        # Phân tích chi tiết hơn về lỗi xây dựng
        if "cannot find symbol" in logs.lower():
            analysis["analysis"] += ": Không tìm thấy ký hiệu/class/method được tham chiếu"
            analysis["suggestions"] = [
                "Kiểm tra tên biến, class hoặc method có đúng không",
                "Kiểm tra xem bạn đã import các package cần thiết chưa",
                "Xác nhận rằng các dependencies đã được cài đặt đầy đủ"
            ]
        elif "syntax error" in logs.lower():
            analysis["analysis"] += ": Lỗi cú pháp trong code"
            analysis["suggestions"] = [
                "Kiểm tra cú pháp: dấu chấm phẩy, ngoặc đơn, ngoặc nhọn",
                "Tìm và sửa lỗi cú pháp tại các vị trí được chỉ ra trong log"
            ]
        else:
            analysis["suggestions"] = [
                "Kiểm tra log lỗi để xác định file và dòng cụ thể có lỗi",
                "Xác nhận rằng code được commit đã được xây dựng và kiểm thử trên môi trường local",
                "Kiểm tra các dependencies và phiên bản có tương thích không"
            ]

    # 2. Lỗi kiểm thử (Test failures)
    elif logs and any(term in logs.lower() for term in ["test failed", "assertion error", "expected", "actual", "junit"]):
        analysis["error_type"] = "test_failure"
        analysis["analysis"] = "Phát hiện lỗi trong quá trình kiểm thử (test)"
        analysis["suggestions"] = [
            "Kiểm tra các test case không thành công",
            "Xác nhận rằng thay đổi mới không làm hỏng chức năng hiện có",
            "Cập nhật các test case nếu logic nghiệp vụ đã thay đổi"
        ]

    # 3. Lỗi cấu hình (Configuration errors)
    elif logs and any(term in logs.lower() for term in ["configuration", "config", "yml", "yaml", ".xml", "pom.xml", "gradle"]):
        analysis["error_type"] = "config_error"
        analysis["analysis"] = "Phát hiện lỗi trong cấu hình pipeline hoặc cấu hình dự án"
        analysis["suggestions"] = [
            "Kiểm tra file .gitlab-ci.yml hoặc các file cấu hình khác",
            "Xác nhận rằng tất cả các biến môi trường cần thiết đã được định nghĩa",
            "Kiểm tra cú pháp trong các file cấu hình"
        ]

    # 4. Lỗi dependency
    elif logs and any(term in logs.lower() for term in ["dependency", "could not resolve", "not found in repository", "failed to download", "npm", "yarn", "maven"]):
        analysis["error_type"] = "dependency_error"
        analysis["analysis"] = "Phát hiện lỗi liên quan đến dependencies"
        analysis["suggestions"] = [
            "Kiểm tra kết nối đến repository",
            "Xác nhận rằng tất cả các dependencies đều có phiên bản hợp lệ",
            "Kiểm tra xem có dependencies bị conflict không",
            "Thử xóa cache của dependencies và tải lại"
        ]

    # 5. Lỗi triển khai (Deployment errors)
    elif logs and any(term in logs.lower() for term in ["deploy", "deployment", "kubernetes", "docker", "container", "k8s"]):
        analysis["error_type"] = "deployment_error"
        analysis["analysis"] = "Phát hiện lỗi trong quá trình triển khai (deployment)"
        analysis["suggestions"] = [
            "Kiểm tra cấu hình triển khai và môi trường",
            "Xác nhận quyền truy cập đến môi trường triển khai",
            "Kiểm tra logs của container/kubernetes để biết thêm chi tiết"
        ]

    # 6. Xử lý trường hợp không xác định được lỗi cụ thể
    else:
        # Lấy các dòng lỗi cụ thể từ error_lines
        specific_errors = []
        for line in error_lines:
            specific_errors.append(line)

        if specific_errors:
            analysis["analysis"] = f"Phát hiện các lỗi sau: {'; '.join(specific_errors[:3])}"
            if len(specific_errors) > 3:
                analysis["analysis"] += f" và {len(specific_errors) - 3} lỗi khác"

            analysis["suggestions"] = [
                "Kiểm tra các lỗi cụ thể được liệt kê ở trên",
                "Xác nhận rằng code đã được kiểm thử trên môi trường local",
                "Tham khảo tài liệu hoặc tìm kiếm online về lỗi cụ thể"
            ]
        else:
            analysis["analysis"] = "Không thể xác định lỗi cụ thể từ log"
            analysis["suggestions"] = [
                "Kiểm tra trực tiếp trên giao diện Gitlab để xem chi tiết lỗi",
                "Thử chạy pipeline lại nếu có thể"
            ]

    return analysis

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
    project_info = extract_project_info_from_email(message)

    # Trích xuất trực tiếp job URLs từ email
    job_urls = extract_job_urls(message)

    # Khởi tạo kết quả phân tích
    result = {
        "sender": sender,
        "subject": subject,
        "project_name": project_info["project_name"],
        "commit_id": project_info["commit_id"],
        "environment": project_info["environment"],
        "is_failed_pipeline": is_failed_pipeline_email(message),
        "job_urls": job_urls,
        "job_count": len(job_urls)
    }

    # Nếu tìm thấy job URLs và đây là email thông báo pipeline thất bại
    if job_urls and result["is_failed_pipeline"]:
        logger.info(f"Đã trích xuất được {len(job_urls)} job URLs từ email")

        # Import hàm từ gitlab_auth để lấy log từ job thất bại
        from gmail_agent.gitlab_auth import find_and_get_failed_job_log

        # Tìm và lấy log của job thất bại đầu tiên
        job_result = find_and_get_failed_job_log(job_urls)

        if job_result.get('success'):
            # Tạo dữ liệu log cho phân tích
            job_log = job_result.get('job_log', '')
            job_info = job_result.get('job_info', {})

            # Tách log thành các dòng và tìm các dòng lỗi
            log_lines = job_log.splitlines()
            error_lines = []
            for line in log_lines:
                if any(err_term in line.lower() for err_term in ['error', 'exception', 'failed', 'failure', 'lỗi']):
                    error_lines.append(line.strip())

            # Giới hạn số dòng lỗi
            error_lines = error_lines[:20]

            # Tạo dữ liệu pipeline logs cho phân tích
            pipeline_logs = {
                "success": True,
                "job_links": job_urls,
                "error_lines": error_lines,
                "logs": job_log[:5000] if job_log else None  # Giới hạn độ dài để tránh quá tải
            }

            result["pipeline_logs"] = pipeline_logs
            result["job_info"] = job_info
            result["job_status"] = job_result.get('job_status', 'unknown')
            result["job_name"] = job_info.get('name', 'Unknown Job')

            # Phân tích lỗi dựa trên log
            error_analysis = analyze_pipeline_errors(pipeline_logs)
            result["error_analysis"] = error_analysis

            # Phân tích lỗi bằng AI nếu có thể
            if OPEN_AI_ANALYZER_AVAILABLE:
                try:
                    # Sử dụng mô hình AI để phân tích lỗi
                    project_info_for_ai = {
                        "project_name": project_info["project_name"],
                        "commit_id": project_info["commit_id"],
                        "environment": project_info["environment"],
                        "error_type": error_analysis.get("error_type", "unknown")
                    }

                    # Phân tích với AI
                    from gmail_agent.open_ai_analyzer import analyze_pipeline_error_with_ai
                    ai_result = analyze_pipeline_error_with_ai(pipeline_logs, project_info_for_ai)
                    if ai_result:
                        result["ai_error_analysis"] = ai_result
                except Exception as e:
                    logger.error(f"Lỗi khi phân tích pipeline bằng AI: {str(e)}")

        else:
            # Không thể lấy được log của job
            logger.warning(f"Không thể lấy log từ job: {job_result.get('error', 'Unknown error')}")
            result["job_error"] = job_result.get('error', 'Unknown error')

            # Chuẩn bị dữ liệu giả lập cho phân tích
            if MOCK_HANDLER_AVAILABLE:
                result = integrate_mock_pipeline_logs_to_gitlab_analysis(result)

    # Nếu không tìm thấy job URLs hoặc không lấy được log
    elif MOCK_HANDLER_AVAILABLE and result["is_failed_pipeline"]:
        # Sử dụng mock data nếu không tìm thấy job URLs
        logger.info("Không tìm thấy job URLs hoặc không lấy được log, sử dụng mock data")
        result = integrate_mock_pipeline_logs_to_gitlab_analysis(result)

    return result
