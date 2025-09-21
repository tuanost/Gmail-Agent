# Gmail Agent

Một dự án Python để tìm kiếm và phân tích email trong tài khoản Gmail của bạn với các tính năng AI nâng cao.

## Cập Nhật Mới (Tháng 9, 2025)

- **Xử Lý Email Gitlab**: Tính năng mới để phân tích các email pipeline từ Gitlab
- **Kiểm Tra URL Pipeline**: Khả năng kiểm tra trạng thái truy cập của các URL pipeline trong email thông báo thất bại
- **Hiển Thị Prompt Phân Tích**: Hiển thị prompt đã sử dụng trong kết quả phân tích và đặt ở đầu file JSON kết quả
- **Tối Ưu Hóa Dependencies**: Loại bỏ các thư viện không sử dụng để giảm kích thước cài đặt

## Cấu Trúc Dự Án

Dự án được tổ chức thành các module riêng biệt để dễ bảo trì:

- `gmail_auth.py` - Chứa các chức năng xác thực cho Gmail API
- `gmail_operations.py` - Chứa chức năng tìm kiếm và truy xuất email
- `email_ai.py` - Chức năng AI cơ bản cho phân tích email
- `ai_interface.py` - Giao diện chức năng phân tích email bằng AI
- `ai_models.py` - Tích hợp với các API mô hình AI bên ngoài
- `prompt_ai.py` - Xử lý prompt và định dạng kết quả phân tích
- `gitlab_email_handler.py` - Xử lý chuyên biệt cho email từ Gitlab
- `main.py` - Chương trình chính tích hợp các module khác

## Cài Đặt Ban Đầu

1. Tạo một dự án trong [Google Cloud Console](https://console.cloud.google.com/)
2. Kích hoạt Gmail API
3. Tạo thông tin xác thực OAuth (OAuth client ID) cho ứng dụng desktop
4. Tải thông tin xác thực và lưu thành `credentials.json` trong thư mục dự án

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
pip install gmail_agent-0.2.0-py3-none-any.whl
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
  - Tóm tắt nội dung
  - Trích xuất từ khóa quan trọng
  - Xác định hành động cần thực hiện
  - Phân tích thêm chi tiết về email
- **Lưu kết quả phân tích** vào file JSON với prompt ở đầu file

## Môi Trường

Dự án yêu cầu Python 3.8 trở lên và sử dụng API của Google Gemini (có thể cấu hình trong file .env).

## Yêu Cầu

Xem requirements.txt để biết các thư viện phụ thuộc:
- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib
- nltk
- scikit-learn
- numpy
- google-generativeai
- python-dotenv
- requests
- beautifulsoup4
