"""
Module xử lý email từ Gitlab.
Module này cung cấp các chức năng để xử lý email từ Gitlab, đặc biệt là các thông báo
về pipeline thành công hoặc thất bại.
"""

import re
import requests
import json
from bs4 import BeautifulSoup
import base64
import html
import logging
from urllib.parse import urlparse

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import tùy chọn cho mock data (nếu URL pipeline không thể truy cập)
try:
    from gmail_agent.pipeline_mock_handler import integrate_mock_pipeline_logs_to_gitlab_analysis
    MOCK_HANDLER_AVAILABLE = True
except ImportError:
    MOCK_HANDLER_AVAILABLE = False

# Import module phân tích AI mới
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

    Tham số:
        message: Đối tượng tin nhắn từ Gmail API

    Trả về:
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

    Tham số:
        message: Đối tượng tin nhắn từ Gmail API
        sender_filter: Địa chỉ email của hệ thống Gitlab (mặc định là git_nhs@bidv.com.vn)

    Trả về:
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

    Tham số:
        message: Đối tượng tin nhắn từ Gmail API

    Trả về:
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

    Tham số:
        message: Đối tượng tin nhắn từ Gmail API

    Trả về:
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

def check_pipeline_url_accessibility(url, timeout=5):
    """
    Kiểm tra xem URL của pipeline có thể truy cập được không.

    Tham số:
        url: URL cần kiểm tra
        timeout: Thời gian chờ tối đa (giây)

    Trả về:
        Tuple (bool, str): (Có thể truy cập không, Thông báo)
    """
    if not url:
        return False, "Không tìm thấy URL pipeline trong email."

    try:
        # Phân tích URL để kiểm tra tính hợp lệ
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return False, f"URL pipeline không hợp lệ: {url}"

        # Thử truy cập URL
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        if response.status_code < 400:
            return True, f"URL pipeline có thể truy cập được: {url}"
        else:
            return False, f"URL pipeline không thể truy cập. Mã trạng thái: {response.status_code}"

    except requests.exceptions.Timeout:
        return False, f"Kết nối đến URL pipeline bị time out: {url}"

    except requests.exceptions.ConnectionError:
        return False, f"Không thể kết nối đến URL pipeline: {url}"

    except Exception as e:
        return False, f"Lỗi khi kiểm tra URL pipeline: {str(e)}"

def extract_pipeline_logs(pipeline_url):
    """
    Truy cập URL pipeline để lấy log lỗi.

    Tham số:
        pipeline_url: URL của pipeline cần truy cập

    Trả về:
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

    Tham số:
        pipeline_logs: Dictionary chứa thông tin log lỗi từ hàm extract_pipeline_logs

    Trả về:
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
            analysis["analysis"] = "Không thể xác định chính xác loại lỗi từ log"
            analysis["suggestions"] = [
                "Kiểm tra trực tiếp trên giao diện Gitlab để xem chi tiết lỗi",
                "Thử chạy pipeline lại nếu có thể",
                "Kiểm tra các thay đổi gần đây trong code có thể gây ra lỗi"
            ]

    return analysis

def analyze_gitlab_email(message):
    """
    Phân tích email từ Gitlab và trả về thông tin chi tiết.

    Tham số:
        message: Đối tượng tin nhắn từ Gmail API

    Trả về:
        Dictionary chứa thông tin phân tích
    """
    from gmail_agent.gmail_operations import get_email_subject, get_sender

    result = {
        "is_gitlab_email": is_gitlab_pipeline_email(message),
        "is_failed_pipeline": False,
        "subject": get_email_subject(message),
        "sender": get_sender(message),
        "pipeline_url": None,
        "pipeline_url_accessible": False,
        "accessibility_message": "",
        "project_name": "",
        "commit_id": "",
        "environment": "",
        "pipeline_logs": None,
        "error_analysis": None,
        "using_mock_data": False
    }

    if not result["is_gitlab_email"]:
        return result

    # Kiểm tra xem có phải email thông báo thất bại không
    result["is_failed_pipeline"] = is_failed_pipeline_email(message)

    # Trích xuất URL pipeline
    pipeline_url = extract_pipeline_url(message)
    result["pipeline_url"] = pipeline_url

    # Kiểm tra khả năng truy cập URL
    if pipeline_url:
        accessible, message = check_pipeline_url_accessibility(pipeline_url)
        result["pipeline_url_accessible"] = accessible
        result["accessibility_message"] = message

        # Nếu URL có thể truy cập và là email báo lỗi, trích xuất và phân tích logs
        if accessible and result["is_failed_pipeline"]:
            # Trích xuất logs từ pipeline URL
            pipeline_logs = extract_pipeline_logs(pipeline_url)
            result["pipeline_logs"] = pipeline_logs

            # Phân tích lỗi và đưa ra gợi ý
            if pipeline_logs:
                error_analysis = analyze_pipeline_errors(pipeline_logs)
                result["error_analysis"] = error_analysis

        # Nếu URL KHÔNG thể truy cập và mock handler có sẵn, sử dụng mock data
        elif not accessible and result["is_failed_pipeline"] and MOCK_HANDLER_AVAILABLE:
            # Sử dụng mock data nếu người dùng lựa chọn
            result = integrate_mock_pipeline_logs_to_gitlab_analysis(result)

    # Trích xuất thông tin từ tiêu đề
    subject = result["subject"]

    # Trích xuất tên dự án
    project_match = re.search(r'^([a-zA-Z0-9\-_]+)', subject)
    if project_match:
        result["project_name"] = project_match.group(1)

    # Trích xuất commit ID (thường là chuỗi hex ở cuối)
    commit_match = re.search(r'([a-f0-9]{6,40})$', subject)
    if commit_match:
        result["commit_id"] = commit_match.group(1)

    # Trích xuất môi trường (sit, uat, prod)
    env_match = re.search(r'(sit|uat|prod)-[0-9]+', subject, re.IGNORECASE)
    if env_match:
        result["environment"] = env_match.group(0)

    # Nếu có module phân tích AI, sử dụng để phân tích lỗi
    if OPEN_AI_ANALYZER_AVAILABLE and result["pipeline_logs"] and result["is_failed_pipeline"]:
        ai_analysis = analyze_pipeline_error_with_ai(result["pipeline_logs"])
        result["ai_error_analysis"] = ai_analysis

    return result
