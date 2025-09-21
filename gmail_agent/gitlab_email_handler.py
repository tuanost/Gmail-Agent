"""
Module xử lý email từ Gitlab.
Module này cung cấp các chức năng để xử lý email từ Gitlab, đặc biệt là các thông báo
về pipeline thành công hoặc thất bại.
"""

import re
import requests
from bs4 import BeautifulSoup
import base64
import html
from urllib.parse import urlparse

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
        "environment": ""
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

    return result
