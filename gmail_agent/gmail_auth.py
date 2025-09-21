"""
Module xác thực và kết nối đến Gmail API.
Module này cung cấp các chức năng xác thực và tạo kết nối đến Gmail API.
"""
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Định nghĩa các phạm vi truy cập
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """
    Lấy và trả về phiên bản dịch vụ Gmail API đã được xác thực.

    Trả về:
        Đối tượng dịch vụ Gmail API đã xác thực
    """
    creds = None
    # Thư mục chứa token và credentials
    token_path = 'token.pickle'
    credentials_path = 'credentials.json'

    # Kiểm tra xem có file token lưu sẵn không
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # Nếu không có credentials hoặc credentials không hợp lệ, tạo mới
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                print("Không tìm thấy file credentials.json. Vui lòng tạo một dự án trong Google API Console "
                      "và tải file credentials.json về.")
                exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Lưu credentials cho lần sau
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    # Tạo dịch vụ Gmail API
    service = build('gmail', 'v1', credentials=creds)
    return service
