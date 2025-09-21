"""
Module chứa các thao tác với Gmail API.
Module này cung cấp các chức năng để tìm kiếm, lấy và xử lý email từ Gmail API.
"""

def search_emails(service, query, max_results=20):
    """
    Tìm kiếm email theo truy vấn với Gmail API.

    Tham số:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        query: Chuỗi truy vấn tìm kiếm (Gmail search syntax)
        max_results: Số lượng kết quả tối đa cần trả về

    Trả về:
        Danh sách các đối tượng tin nhắn
    """
    try:
        result = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = []
        if 'messages' in result:
            messages.extend(result['messages'])

        # Chỉ tiếp tục lấy thêm kết quả nếu còn nextPageToken và chưa đủ max_results
        while 'nextPageToken' in result and len(messages) < max_results:
            page_token = result['nextPageToken']
            result = service.users().messages().list(
                userId='me', q=query, pageToken=page_token, maxResults=max_results - len(messages)
            ).execute()
            if 'messages' in result:
                messages.extend(result['messages'])

        print(f"Đã tìm thấy {len(messages)} email khớp với truy vấn: {query}")
        return messages
    except Exception as e:
        print(f"Lỗi khi tìm kiếm email: {str(e)}")
        return []

def search_by_keyword(service, keyword, max_results=20):
    """
    Tìm kiếm email chứa từ khóa cụ thể.

    Tham số:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        keyword: Từ khóa cần tìm kiếm
        max_results: Số lượng kết quả tối đa

    Trả về:
        Danh sách các email khớp với từ khóa
    """
    # Đảm bảo từ khóa được bọc trong dấu ngoặc kép để tìm chính xác
    query = f"\"{keyword}\""
    return search_emails(service, query, max_results)

def search_by_label(service, label_id, label_name, max_results=20):
    """
    Tìm kiếm email theo nhãn (label).

    Tham số:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        label_id: ID của nhãn cần tìm
        max_results: Số lượng kết quả tối đa

    Trả về:
        Danh sách các email có nhãn đã chọn
    """
    try:
        # Sử dụng labelIds trực tiếp thay vì query để tìm email theo nhãn
        result = service.users().messages().list(
            userId='me',
            labelIds=[label_id],
            maxResults=max_results
        ).execute()

        messages = []
        if 'messages' in result:
            messages.extend(result['messages'])

        # Xử lý phân trang nếu có nhiều kết quả
        while 'nextPageToken' in result and len(messages) < max_results:
            page_token = result['nextPageToken']
            result = service.users().messages().list(
                userId='me',
                labelIds=[label_id],
                pageToken=page_token,
                maxResults=max_results - len(messages)
            ).execute()
            if 'messages' in result:
                messages.extend(result['messages'])

        print(f"Đã tìm thấy {len(messages)} email với nhãn: {label_name}")
        return messages
    except Exception as e:
        print(f"Lỗi khi tìm kiếm email theo nhãn: {str(e)}")
        return []

def get_email_details(service, msg_id):
    """
    Lấy thông tin chi tiết của một email.

    Tham số:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        msg_id: ID của tin nhắn cần lấy chi tiết

    Trả về:
        Đối tượng tin nhắn với đầy đủ thông tin
    """
    try:
        message = service.users().messages().get(userId='me', id=msg_id).execute()
        return message
    except Exception as e:
        print(f"Lỗi khi lấy chi tiết email: {str(e)}")
        return None

def get_email_subject(message):
    """Trích xuất tiêu đề từ một tin nhắn email."""
    headers = message['payload']['headers']
    for header in headers:
        if header['name'] == 'Subject':
            return header['value']
    return 'Không có tiêu đề'

def get_sender(message):
    """Trích xuất địa chỉ email người gửi từ một tin nhắn."""
    headers = message['payload']['headers']
    for header in headers:
        if header['name'] == 'From':
            return header['value']
    return 'Không xác định'

def get_email_list(service, max_results=10):
    """
    Lấy danh sách email mới nhất.

    Tham số:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        max_results: Số lượng email tối đa cần lấy

    Trả về:
        Danh sách các đối tượng tin nhắn
    """
    try:
        results = service.users().messages().list(userId='me', maxResults=max_results).execute()
        return results.get('messages', [])
    except Exception as e:
        print(f"Lỗi khi lấy danh sách email: {str(e)}")
        return []

def mark_as_read(service, msg_id):
    """Đánh dấu một email là đã đọc."""
    try:
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        return True
    except Exception as e:
        print(f"Lỗi khi đánh dấu email đã đọc: {str(e)}")
        return False

def mark_as_unread(service, msg_id):
    """Đánh dấu một email là chưa đọc."""
    try:
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={'addLabelIds': ['UNREAD']}
        ).execute()
        return True
    except Exception as e:
        print(f"Lỗi khi đánh dấu email chưa đọc: {str(e)}")
        return False

def archive_email(service, msg_id):
    """Lưu trữ một email (chuyển vào kho lưu trữ)."""
    try:
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        return True
    except Exception as e:
        print(f"Lỗi khi lưu trữ email: {str(e)}")
        return False

def delete_email(service, msg_id):
    """
    Xóa vĩnh viễn một email.

    Tham số:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
        msg_id: ID của tin nhắn cần xóa

    Trả về:
        True nếu xóa thành công, False nếu có lỗi
    """
    try:
        service.users().messages().delete(userId='me', id=msg_id).execute()
        return True
    except Exception as e:
        print(f"Lỗi khi xóa email: {str(e)}")
        return False

def get_email_labels(service):
    """
    Lấy danh sách tất cả các nhãn (labels) trong Gmail của người dùng.

    Tham số:
        service: Phiên bản dịch vụ Gmail API đã được xác thực

    Trả về:
        Danh sách các nhãn Gmail
    """
    try:
        results = service.users().labels().list(userId='me').execute()
        return results.get('labels', [])
    except Exception as e:
        print(f"Lỗi khi lấy danh sách nhãn: {str(e)}")
        return []

def get_recipients(message):
    """Trích xuất thông tin người nhận từ một tin nhắn email."""
    headers = message['payload']['headers']
    recipients = []

    # Check different recipient header fields
    for header in headers:
        if header['name'] in ['To', 'Cc', 'Bcc']:
            recipients.append(f"{header['name']}: {header['value']}")

    if recipients:
        return "; ".join(recipients)
    return 'Không xác định'
