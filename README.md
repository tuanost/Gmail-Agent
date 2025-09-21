# Công Cụ Tìm Kiếm Gmail

Một dự án Python để tìm kiếm email trong tài khoản Gmail của bạn với các tính năng tìm kiếm và phân tích nâng cao.

## Cấu Trúc Dự Án

Dự án được tổ chức thành các module riêng biệt để dễ bảo trì:

- `gmail_auth.py` - Chứa các chức năng xác thực cho Gmail API
- `gmail_operations.py` - Chứa chức năng tìm kiếm và truy xuất email
- `ai_interface.py` - Chứa các chức năng phân tích email bằng AI
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

## Sử Dụng

Chạy script:

```bash
python main.py
```

Lần đầu tiên chạy script, nó sẽ mở cửa sổ trình duyệt để xác thực với tài khoản Google của bạn.
Sau khi xác thực, bạn có thể sử dụng các chức năng tìm kiếm và phân tích email.

## Tính Năng

- Xác thực với Gmail API sử dụng OAuth2
- Tìm kiếm email theo người gửi
- Tìm kiếm email theo từ khóa
- Phân tích email bằng AI
- Hiển thị chi tiết email bao gồm tiêu đề, ngày tháng và tóm tắt
- Xử lý phân trang cho các bộ sưu tập email lớn

## Yêu Cầu

Xem requirements.txt để biết các thư viện phụ thuộc:
- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib
- nltk
- scikit-learn
- numpy
