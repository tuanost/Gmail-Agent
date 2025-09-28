"""
Các thao tác để trích xuất nội dung email.
Module này cung cấp chức năng cơ bản để trích xuất nội dung email từ Gmail API.
"""

import re
import logging
import base64
import html
from typing import Dict, Any

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def decode_email_body(email_data: str) -> str:
    """
    Giải mã nội dung email từ base64 và xử lý HTML.

    Args:
        email_data: Chuỗi dữ liệu email đã được mã hóa base64

    Returns:
        Nội dung email đã được giải mã và làm sạch HTML
    """
    if not email_data:
        return ""

    try:
        # Giải mã base64
        decoded_bytes = base64.urlsafe_b64decode(email_data)
        text = decoded_bytes.decode('utf-8')

        # Làm sạch HTML
        text = clean_html_content(text)
        return text
    except Exception as e:
        logger.error(f"Lỗi khi giải mã nội dung email: {str(e)}")
        return ""

def clean_html_content(html_content: str) -> str:
    """
    Loại bỏ các thẻ HTML và giải mã các thực thể HTML.

    Args:
        html_content: Chuỗi HTML cần làm sạch

    Returns:
        Chuỗi văn bản đã làm sạch
    """
    # Loại bỏ thẻ HTML
    text = re.sub('<[^<]+?>', '', html_content)

    # Giải mã các thực thể HTML
    text = html.unescape(text)

    # Loại bỏ khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def extract_email_body(message: Dict[str, Any]) -> str:
    """
    Trích xuất và giải mã nội dung email từ một tin nhắn API Gmail.

    Args:
        message: Đối tượng tin nhắn từ Gmail API

    Returns:
        Nội dung email đã được giải mã
    """
    parts = []

    # Hàm để đệ quy trích xuất các phần
    def get_parts(payload: Dict[str, Any]) -> None:
        """Đệ quy qua các phần của email để trích xuất nội dung."""
        if 'parts' in payload:
            for part in payload['parts']:
                get_parts(part)
        elif 'body' in payload and 'data' in payload['body']:
            mime_type = payload.get('mimeType', '')
            if mime_type == 'text/plain' or mime_type.startswith('text/'):
                parts.append(payload['body']['data'])

    # Bắt đầu đệ quy từ payload gốc
    if 'payload' in message:
        get_parts(message['payload'])

    # Xử lý các phần đã trích xuất
    if parts:
        combined_content = ''.join(parts)
        return decode_email_body(combined_content)

    # Fallback: nếu không có phần nào, thử lấy snippet
    if 'snippet' in message:
        return message['snippet']

    return ""
