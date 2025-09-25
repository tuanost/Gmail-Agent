# Gmail Agent

Một dự án Python để tìm kiếm và phân tích email trong tài khoản Gmail của bạn với các tính năng AI nâng cao.

## Cập Nhật Mới (25 Tháng 9, 2025)

- **Tối Ưu Hiển Thị Email**: Cải thiện cách hiển thị số lượng email và định dạng danh sách email
- **Tối Ưu Hóa Mã Nguồn**: Cải thiện cấu trúc code, thêm type hints và logging để dễ dàng bảo trì hơn
- **Cải Tiến Xử Lý Lỗi**: Nâng cao khả năng xử lý lỗi khi gọi API và xử lý dữ liệu
- **Loại Bỏ Trường Thừa**: Đã loại bỏ các trường summary, important_keywords, action_items trong kết quả phân tích
- **Xử Lý Email Gitlab**: Tính năng phân tích các email pipeline từ Gitlab
- **Kiểm Tra URL Pipeline**: Khả năng kiểm tra trạng thái truy cập của các URL pipeline trong email thông báo thất bại
- **Hiển Thị Prompt Phân Tích**: Hiển thị prompt đã sử dụng trong kết quả phân tích và đặt ở đầu file JSON kết quả
- **Tối Ưu Hóa Dependencies**: Loại bỏ các thư viện không sử dụng để giảm kích thước cài đặt

## Cấu Trúc Dự Án

Dự án được tổ chức thành các module riêng biệt để dễ bảo trì:

- `gmail_auth.py` - Chứa các chức năng xác thực cho Gmail API
- `gmail_operations.py` - Chứa chức năng tìm kiếm và truy xuất email
- `email_ai.py` - Chức năng AI cơ bản cho phân tích email
- `ai_interface.py` - Giao diện chức năng phân tích email bằng AI
- `ai_models.py` - Tích hợp với các API mô hình AI bên ngoài (Gemini, OpenAI)
- `prompt_ai.py` - Xử lý prompt và định dạng kết quả phân tích
- `gitlab_auth.py` - Xác thực với Gitlab API
- `gitlab_operations.py` - Xử lý chuyên biệt cho email từ Gitlab
- `open_ai_analyzer.py` - Tích hợp phân tích với OpenAI
- `pipeline_mock_data.py` - Dữ liệu mô phỏng cho phân tích lỗi pipeline
- `pipeline_mock_handler.py` - Xử lý dữ liệu mô phỏng cho pipeline
- `main.py` - Chương trình chính tích hợp các module khác

## Cài Đặt Ban Đầu

1. Tạo một dự án trong [Google Cloud Console](https://console.cloud.google.com/)
2. Kích hoạt Gmail API
3. Tạo thông tin xác thực OAuth (OAuth client ID) cho ứng dụng desktop
4. Tải thông tin xác thực và lưu thành `credentials.json` trong thư mục dự án
5. Tạo file `.env` chứa các biến môi trường cần thiết (xem phần Cấu Hình Môi Trường)

## Cài Đặt

```bash
pip install -r requirements.txt
```

Hoặc cài đặt trực tiếp từ mã nguồn:

```bash
pip install -e .
```

## Đóng Gói và Phân Phối

Để đóng gói dự án và cài đặt trên máy tính khác:

```bash
# Tạo bản phân phối
python -m build

# Sao chép file .whl từ thư mục dist sang máy tính khác
# Trên máy đích, cài đặt bằng lệnh:
pip install gmail_agent-0.3.0-py3-none-any.whl
```

## Sử Dụng

Chạy script:

```bash
python -m gmail_agent.main
```

Hoặc nếu đã cài đặt qua setup.py:

```bash
gmail-agent
```

Lần đầu tiên chạy script, nó sẽ mở cửa sổ trình duyệt để xác thực với tài khoản Google của bạn.
Sau khi xác thực, bạn có thể sử dụng các chức năng tìm kiếm và phân tích email.

## Tính Năng

- **Xác thực với Gmail API** sử dụng OAuth2
- **Tìm kiếm email** theo từ khóa hoặc nhãn (label)
- **Phân tích email bằng AI** với prompt tùy chỉnh
- **Xử lý email Gitlab**:
    - Tìm email thông báo pipeline Gitlab
    - Phân tích email thông báo pipeline thất bại
    - Kiểm tra khả năng truy cập URL pipeline
- **Phân tích nội dung email**:
    - Phân tích chi tiết dựa trên prompt người dùng
    - Định dạng kết quả phân tích dễ đọc
    - Lưu kết quả phân tích vào file JSON
- **Logging đầy đủ**: Theo dõi và ghi lại quá trình xử lý để dễ dàng gỡ lỗi

## Cấu Hình Môi Trường

Dự án sử dụng file `.env` để cấu hình các thông số quan trọng. Một số cấu hình chính:

```
# API Keys cho các mô hình AI
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key

# Cấu hình mô hình
DEFAULT_AI_PROVIDER=gemini  # "gemini" hoặc "openai"

# Cấu hình tên mô hình
DEFAULT_OPENAI_MODEL=gpt-3.5-turbo-0125
DEFAULT_GEMINI_MODEL=gemini-1.5-flash

# Default prompt cho phân tích email
DEFAULT_EMAIL_PROMPT="Prompt mặc định cho phân tích email..."

# Prompt cho phân tích lỗi pipeline
PIPELINE_ERROR_PROMPT="Prompt cho phân tích lỗi pipeline..."
```

## Yêu Cầu

- Python 3.8+
- Google API Python Client
- OAuth2 Client
- Google Gemini API hoặc OpenAI API
- Các thư viện khác được liệt kê trong file requirements.txt

## Tích Hợp Ollama (Tùy chọn)

Gmail Agent hỗ trợ tích hợp với Ollama để chạy các mô hình LLM cục bộ. Xem hướng dẫn chi tiết trong file `ollama_setup_guide.md`.

## Đóng Góp

Mọi đóng góp đều được hoan nghênh. Vui lòng gửi Pull Request hoặc mở Issue để thảo luận về các tính năng hoặc báo cáo lỗi.

## Giấy Phép

[MIT License](LICENSE)

