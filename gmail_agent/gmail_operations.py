"""
Module chứa các thao tác với Gmail API.
Module này cung cấp các chức năng để tìm kiếm, lấy và xử lý email từ Gmail API.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from googleapiclient.errors import HttpError

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Danh sách các nhãn Gmail hệ thống phổ biến
GMAIL_SYSTEM_LABELS = {
    'INBOX': 'Hộp thư đến',
    'SENT': 'Đã gửi',
    'DRAFT': 'Bản nháp',
    'TRASH': 'Thùng rác',
    'SPAM': 'Spam',
    'UNREAD': 'Chưa đọc',
    'STARRED': 'Đã gắn sao',
    'IMPORTANT': 'Quan trọng',
    'CATEGORY_PERSONAL': 'Cá nhân',
    'CATEGORY_SOCIAL': 'Mạng xã hội',
    'CATEGORY_PROMOTIONS': 'Quảng cáo',
    'CATEGORY_UPDATES': 'Cập nhật',
    'CATEGORY_FORUMS': 'Diễn đàn'
}

def search_emails(service: Any, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Tìm kiếm email theo truy vấn với Gmail API.

    Args:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        query: Chuỗi truy vấn tìm kiếm (Gmail search syntax)
        max_results: Số lượng kết quả tối đa cần trả về

    Returns:
        Danh sách các đối tượng tin nhắn
    """
    try:
        logger.info(f"Tìm kiếm email với truy vấn: {query}")
        result = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = []
        if 'messages' in result:
            messages.extend(result['messages'])

        # Phân trang kết quả nếu cần thiết
        while 'nextPageToken' in result and len(messages) < max_results:
            page_token = result['nextPageToken']
            result = service.users().messages().list(
                userId='me', q=query, pageToken=page_token, maxResults=max_results - len(messages)
            ).execute()
            if 'messages' in result:
                messages.extend(result['messages'])

        email_count = len(messages)
        logger.info(f"[Kết quả tìm kiếm] Tìm thấy {email_count} email khớp với truy vấn: {query}")
        return messages
    except HttpError as e:
        logger.error(f"Lỗi HTTP khi tìm kiếm email: {str(e)}")
        return []
    except Exception as e:
        logger.exception(f"Lỗi khi tìm kiếm email: {str(e)}")
        return []

def search_by_keyword(service: Any, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Tìm kiếm email chứa từ khóa cụ thể.

    Args:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        keyword: Từ khóa cần tìm kiếm
        max_results: Số lượng kết quả tối đa

    Returns:
        Danh sách các email khớp với từ khóa
    """
    # Đảm bảo từ khóa được bọc trong dấu ngoặc kép để tìm chính xác
    query = f"\"{keyword}\""
    logger.info(f"Tìm kiếm email theo từ khóa: {keyword}")
    return search_emails(service, query, max_results)

def search_by_label(service: Any, label_id: str, label_name: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Tìm kiếm email theo nhãn (label).

    Args:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        label_id: ID của nhãn cần tìm
        label_name: Tên của nhãn để hiển thị thông báo
        max_results: Số lượng email gần nhất cần lấy

    Returns:
        Danh sách các email gần nhất có nhãn đã chọn
    """
    try:
        logger.info(f"Tìm kiếm email với nhãn: {label_name} (ID: {label_id})")

        # Đếm tổng số email thực tế có nhãn này
        total_count = count_total_emails(service, label_ids=[label_id])
        
        # Sử dụng labelIds trực tiếp để tìm email với nhãn
        result = service.users().messages().list(
            userId='me',
            labelIds=[label_id],
            maxResults=max_results
        ).execute()

        messages = []
        if 'messages' in result:
            messages.extend(result['messages'])

        # Log tổng số email thực sự có trong hệ thống
        logger.info(f"[Kết quả tìm kiếm] Đã tìm thấy {total_count} email với nhãn: {label_name}")

        return messages, total_count
    except HttpError as e:
        logger.error(f"Lỗi HTTP khi tìm kiếm email theo nhãn: {str(e)}")
        return [], 0
    except Exception as e:
        logger.exception(f"Lỗi khi tìm kiếm email theo nhãn: {str(e)}")
        return [], 0

def get_email_details(service: Any, msg_id: str) -> Optional[Dict[str, Any]]:
    """
    Lấy thông tin chi tiết của một email.

    Args:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        msg_id: ID của tin nhắn cần lấy chi tiết

    Returns:
        Đối tượng tin nhắn với đầy đủ thông tin hoặc None nếu có lỗi
    """
    try:
        message = service.users().messages().get(userId='me', id=msg_id).execute()
        return message
    except HttpError as e:
        logger.error(f"Lỗi HTTP khi lấy chi tiết email: {str(e)}")
        return None
    except Exception as e:
        logger.exception(f"Lỗi khi lấy chi tiết email: {str(e)}")
        return None

def extract_header_value(message: Dict[str, Any], header_name: str, default_value: str = 'Không xác định') -> str:
    """
    Trích xuất giá trị của một header từ tin nhắn.

    Args:
        message: Đối tượng tin nhắn từ Gmail API
        header_name: Tên header cần trích xuất
        default_value: Giá trị mặc định nếu không tìm thấy header

    Returns:
        Giá trị của header hoặc giá trị mặc định
    """
    try:
        headers = message['payload']['headers']
        for header in headers:
            if header['name'] == header_name:
                return header['value']
        return default_value
    except Exception:
        logger.warning(f"Không thể trích xuất header {header_name}")
        return default_value

def get_email_subject(message: Dict[str, Any]) -> str:
    """
    Trích xuất tiêu đề từ một tin nhắn email.

    Args:
        message: Đối tượng tin nhắn từ Gmail API

    Returns:
        Tiêu đề email hoặc 'Không có tiêu đề' nếu không tìm thấy
    """
    return extract_header_value(message, 'Subject', 'Không có tiêu đề')

def get_sender(message: Dict[str, Any]) -> str:
    """
    Trích xuất địa chỉ email người gửi từ một tin nhắn.

    Args:
        message: Đối tượng tin nhắn từ Gmail API

    Returns:
        Địa chỉ người gửi hoặc 'Không xác định' nếu không tìm thấy
    """
    return extract_header_value(message, 'From', 'Không xác định')

def get_recipients(message: Dict[str, Any]) -> str:
    """
    Trích xuất địa chỉ email người nhận từ một tin nhắn.

    Args:
        message: Đối tượng tin nhắn từ Gmail API

    Returns:
        Danh sách người nhận hoặc 'Không xác định' nếu không tìm thấy
    """
    # Thử lấy từ trường To
    to_recipients = extract_header_value(message, 'To', '')

    # Thử lấy từ trường Cc
    cc_recipients = extract_header_value(message, 'Cc', '')

    # Kết hợp các địa chỉ nhận
    all_recipients = []
    if to_recipients:
        all_recipients.append(f"Đến: {to_recipients}")
    if cc_recipients:
        all_recipients.append(f"Cc: {cc_recipients}")

    if all_recipients:
        return "; ".join(all_recipients)
    else:
        return "Không xác định"

def get_email_list(service: Any, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Lấy danh sách email mới nhất.

    Args:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        max_results: Số lượng email tối đa cần lấy

    Returns:
        Danh sách các đối tượng tin nhắn
    """
    try:
        logger.info(f"Lấy {max_results} email mới nhất")
        results = service.users().messages().list(userId='me', maxResults=max_results).execute()
        messages = results.get('messages', [])
        email_count = len(messages)
        logger.info(f"[Kết quả tìm kiếm] Đã tìm thấy {email_count} email mới nhất")
        return messages
    except HttpError as e:
        logger.error(f"Lỗi HTTP khi lấy danh sách email: {str(e)}")
        return []
    except Exception as e:
        logger.exception(f"Lỗi khi lấy danh sách email: {str(e)}")
        return []

def modify_message_labels(service: Any, msg_id: str, add_labels: List[str] = None,
                         remove_labels: List[str] = None) -> bool:
    """
    Chung cho các thao tác thêm/xóa nhãn trên email.

    Args:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        msg_id: ID của tin nhắn cần sửa đổi
        add_labels: Danh sách các nhãn cần thêm
        remove_labels: Danh sách các nhãn cần xóa

    Returns:
        True nếu thành công, False nếu có lỗi
    """
    add_labels = add_labels or []
    remove_labels = remove_labels or []

    try:
        logger.info(f"Sửa đổi nhãn cho email {msg_id}: Thêm {add_labels}, Xóa {remove_labels}")
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={
                'addLabelIds': add_labels,
                'removeLabelIds': remove_labels
            }
        ).execute()
        return True
    except HttpError as e:
        logger.error(f"Lỗi HTTP khi sửa đổi nhãn email: {str(e)}")
        return False
    except Exception as e:
        logger.exception(f"Lỗi khi sửa đổi nhãn email: {str(e)}")
        return False

def mark_as_read(service: Any, msg_id: str) -> bool:
    """
    Đánh dấu một email là đã đọc.

    Args:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        msg_id: ID của tin nhắn cần đánh dấu

    Returns:
        True nếu thành công, False nếu có lỗi
    """
    return modify_message_labels(service, msg_id, remove_labels=['UNREAD'])

def mark_as_unread(service: Any, msg_id: str) -> bool:
    """
    Đánh dấu một email là chưa đọc.

    Args:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        msg_id: ID của tin nhắn cần đánh dấu

    Returns:
        True nếu thành công, False nếu có lỗi
    """
    return modify_message_labels(service, msg_id, add_labels=['UNREAD'])

def archive_email(service: Any, msg_id: str) -> bool:
    """
    Lưu trữ một email (chuyển vào kho lưu trữ).

    Args:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        msg_id: ID của tin nhắn cần lưu trữ

    Returns:
        True nếu thành công, False nếu có lỗi
    """
    return modify_message_labels(service, msg_id, remove_labels=['INBOX'])

def delete_email(service: Any, msg_id: str) -> bool:
    """
    Xóa vĩnh viễn một email.

    Args:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        msg_id: ID của tin nhắn cần xóa

    Returns:
        True nếu xóa thành công, False nếu có lỗi
    """
    try:
        logger.info(f"Xóa email có ID: {msg_id}")
        service.users().messages().delete(userId='me', id=msg_id).execute()
        return True
    except HttpError as e:
        logger.error(f"Lỗi HTTP khi xóa email: {str(e)}")
        return False
    except Exception as e:
        logger.exception(f"Lỗi khi xóa email: {str(e)}")
        return False

def trash_email(service: Any, msg_id: str) -> bool:
    """
    Chuyển email vào thùng rác.

    Args:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        msg_id: ID của tin nhắn cần chuyển vào thùng rác

    Returns:
        True nếu chuyển thành công, False nếu có lỗi
    """
    try:
        logger.info(f"Chuyển email có ID {msg_id} vào thùng rác")
        service.users().messages().trash(userId='me', id=msg_id).execute()
        return True
    except HttpError as e:
        logger.error(f"Lỗi HTTP khi chuyển email vào thùng rác: {str(e)}")
        return False
    except Exception as e:
        logger.exception(f"Lỗi khi chuyển email vào thùng rác: {str(e)}")
        return False

def get_email_labels(service: Any) -> List[Dict[str, str]]:
    """
    Lấy danh sách tất cả các nhãn trong tài khoản Gmail.

    Args:
        service: Phiên bản dịch vụ Gmail API đã được xác thực

    Returns:
        Danh sách các nhãn với id và name
    """
    try:
        logger.info("Lấy danh sách các nhãn Gmail")
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        # Sắp xếp nhãn hệ thống lên đầu và các nhãn khác theo alphabet
        system_labels = []
        user_labels = []

        for label in labels:
            if label['type'] == 'system':
                system_labels.append(label)
            else:
                user_labels.append(label)

        # Sắp xếp các nhãn người dùng theo tên
        user_labels.sort(key=lambda x: x['name'].lower())

        # Kết hợp hai danh sách
        sorted_labels = system_labels + user_labels

        logger.info(f"Đã tìm thấy {len(sorted_labels)} nhãn")
        return sorted_labels
    except HttpError as e:
        logger.error(f"Lỗi HTTP khi lấy danh sách nhãn: {str(e)}")
        return []
    except Exception as e:
        logger.exception(f"Lỗi khi lấy danh sách nhãn: {str(e)}")
        return []

def get_email_thread(service: Any, thread_id: str) -> List[Dict[str, Any]]:
    """
    Lấy chuỗi hội thoại email từ thread ID.

    Args:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        thread_id: ID của chuỗi hội thoại cần lấy

    Returns:
        Danh sách các tin nhắn trong chuỗi hội thoại
    """
    try:
        logger.info(f"Lấy chuỗi hội thoại có ID: {thread_id}")
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        messages = thread.get('messages', [])
        logger.info(f"Đã tìm thấy {len(messages)} tin nhắn trong chuỗi hội thoại")
        return messages
    except HttpError as e:
        logger.error(f"Lỗi HTTP khi lấy chuỗi hội thoại: {str(e)}")
        return []
    except Exception as e:
        logger.exception(f"Lỗi khi lấy chuỗi hội thoại: {str(e)}")
        return []

def count_total_emails(service: Any, query: str = None, label_ids: List[str] = None) -> int:
    """
    Đếm tổng số email khớp với truy vấn hoặc nhãn mà không giới hạn kết quả.
    
    Args:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        query: Chuỗi truy vấn tìm kiếm (Gmail search syntax)
        label_ids: Danh sách ID nhãn cần tìm
        
    Returns:
        Tổng số email khớp với điều kiện
    """
    try:
        params = {'userId': 'me'}
        if query:
            params['q'] = query
        if label_ids:
            params['labelIds'] = label_ids
            
        result = service.users().messages().list(**params).execute()
        total_messages = 0
        
        # Gmail API sẽ trả về resultSizeEstimate nếu có nhiều kết quả
        if 'resultSizeEstimate' in result:
            return result['resultSizeEstimate']
            
        # Nếu không có resultSizeEstimate, đếm bằng cách lặp qua tất cả trang
        if 'messages' in result:
            total_messages += len(result['messages'])
            
        # Xử lý phân trang để đếm tất cả kết quả
        while 'nextPageToken' in result:
            page_token = result['nextPageToken']
            params['pageToken'] = page_token
            result = service.users().messages().list(**params).execute()
            if 'messages' in result:
                total_messages += len(result['messages'])
                
        return total_messages
    except HttpError as e:
        logger.error(f"Lỗi HTTP khi đếm email: {str(e)}")
        return 0
    except Exception as e:
        logger.exception(f"Lỗi khi đếm email: {str(e)}")
        return 0
