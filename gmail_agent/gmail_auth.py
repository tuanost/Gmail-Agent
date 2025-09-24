"""
Module xác thực và kết nối đến Gmail API.
Module này cung cấp các chức năng xác thực và tạo kết nối đến Gmail API.
"""
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import httplib2
from dotenv import load_dotenv
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tải biến môi trường
load_dotenv()

# Định nghĩa các phạm vi truy cập
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_proxy_info():
    """
    Lấy thông tin cấu hình proxy từ biến môi trường.

    Returns:
        dict: Thông tin cấu hình proxy hoặc None nếu không có cấu hình
    """
    proxy_enabled = os.getenv("PROXY_ENABLED", "False").lower() == "true"

    if not proxy_enabled:
        return None

    proxy_info = {
        'proxy_info': httplib2.ProxyInfo(
            httplib2.socks.PROXY_TYPE_HTTP,
            os.getenv("PROXY_HTTP", "").split('://')[1].split(':')[0],
            int(os.getenv("PROXY_HTTP", "").split('://')[1].split(':')[1]),
        )
    }

    # Thiết lập các biến môi trường cho thư viện requests
    os.environ["HTTP_PROXY"] = os.getenv("PROXY_HTTP", "")
    os.environ["HTTPS_PROXY"] = os.getenv("PROXY_HTTPS", "")

    return proxy_info

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

            # Kiểm tra cấu hình proxy
            proxy_enabled = os.getenv("PROXY_ENABLED", "False").lower() == "true"
            if proxy_enabled:
                logger.info("Đang sử dụng proxy cho quá trình xác thực: %s", os.getenv("PROXY_HTTP", ""))
                # Cấu hình proxy cho quá trình xác thực OAuth
                import socket
                import socks

                # Lấy host và port từ cấu hình proxy
                proxy_parts = os.getenv("PROXY_HTTP", "").split('://')
                if len(proxy_parts) > 1:
                    host_port = proxy_parts[1].split(':')
                    if len(host_port) > 1:
                        socks.set_default_proxy(socks.PROXY_TYPE_HTTP, host_port[0], int(host_port[1]))
                        socket.socket = socks.socksocket

            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Lưu credentials cho lần sau
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    # Kiểm tra thông tin proxy
    proxy_info = get_proxy_info()

    # Tạo HTTP object với cấu hình proxy nếu được bật
    if proxy_info:
        logger.info("Đang kết nối Gmail API qua proxy: %s", os.getenv("PROXY_HTTP", ""))
        http = httplib2.Http(proxy_info=proxy_info['proxy_info'])
        # Tạo dịch vụ Gmail API với HTTP object đã cấu hình proxy
        service = build('gmail', 'v1', credentials=creds, http=http)
    else:
        # Tạo dịch vụ Gmail API mà không có proxy
        service = build('gmail', 'v1', credentials=creds)

    logger.info("Đã tạo kết nối thành công với Gmail API")
    return service
