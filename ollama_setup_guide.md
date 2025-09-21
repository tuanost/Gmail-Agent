# Hướng dẫn thiết lập và sử dụng Ollama với Gmail-Agent

## 1. Cài đặt Ollama

Nếu bạn đã cài đặt Ollama.exe, bạn đã hoàn thành bước đầu tiên. Tuy nhiên, việc cài đặt Ollama.exe chỉ là phần đầu tiên của quá trình. Bạn cần cài đặt các model để Ollama có thể chạy được.

## 2. Khởi động Ollama

Trước tiên, hãy đảm bảo rằng Ollama đang chạy trên máy tính của bạn:
- Khởi động Ollama.exe nếu chưa chạy
- Một icon Ollama sẽ xuất hiện ở khay hệ thống (system tray) của Windows

## 3. Cài đặt model cho Ollama

Mở Command Prompt (cmd.exe) và thực hiện các lệnh sau:

```
# Tải model CodeLlama (được đề xuất cho phân tích code)
ollama pull codellama

# HOẶC tải model Llama 2 cho phân tích văn bản tổng quát
ollama pull llama2

# HOẶC tải các model khác bạn muốn sử dụng
# ollama pull mistral
```

Lưu ý: Quá trình tải model có thể mất từ vài phút đến vài giờ tùy thuộc vào kết nối internet và kích thước model.

## 4. Kiểm tra các model đã cài đặt

Để kiểm tra các model đã được cài đặt:

```
ollama list
```

## 5. Cấu hình Gmail-Agent để sử dụng model cụ thể

Khi chọn phân tích với Ollama, Gmail-Agent sẽ liệt kê các model có sẵn để bạn chọn.

## 6. Khắc phục sự cố

Nếu bạn vẫn gặp lỗi khi sử dụng Ollama API:

1. **Kiểm tra Ollama có đang chạy không?** Đảm bảo Ollama đang chạy và biểu tượng của nó xuất hiện trong khay hệ thống.

2. **Kiểm tra model đã được cài đặt chưa?** Chạy lệnh `ollama list` để xác nhận.

3. **Kiểm tra API trực tiếp** bằng cách mở trình duyệt và truy cập:
   http://localhost:11434/api/tags
   
   Bạn sẽ thấy danh sách các model đã cài đặt dạng JSON.

4. **Thử gọi API với curl**:
   ```
   curl -X POST http://localhost:11434/api/generate -d "{\"model\": \"codellama\", \"prompt\": \"Hello\", \"stream\": false}"
   ```

5. **Khởi động lại Ollama** nếu cần.

## 7. Tối ưu hiệu suất

- Ollama sẽ sử dụng GPU nếu có, nếu không nó sẽ sử dụng CPU
- Đảm bảo máy tính của bạn có đủ RAM (tối thiểu 8GB, đề xuất 16GB trở lên)
- Model nhỏ hơn như Phi-2, Tinyllama chạy nhanh hơn nhưng ít chính xác hơn
- Model lớn hơn như Llama-3-70B, CodeLlama chính xác hơn nhưng chậm hơn

## Lưu ý quan trọng

Gmail-Agent đã được cập nhật với khả năng xử lý lỗi tốt hơn khi gọi Ollama API. Nếu vẫn gặp vấn đề, hãy kiểm tra thông báo lỗi chi tiết được hiển thị trong ứng dụng.
