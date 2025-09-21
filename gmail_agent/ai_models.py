"""
Module tích hợp mô hình AI Gemini.
Module này cung cấp các hàm để gửi prompt đến API của mô hình AI
và xử lý kết quả trả về.
"""
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

# Tải các biến môi trường từ file .env
load_dotenv()

# Cấu hình API keys từ biến môi trường
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Cấu hình mặc định cho mô hình từ biến môi trường
DEFAULT_GEMINI_MODEL = os.getenv("DEFAULT_GEMINI_MODEL", "gemini-1.5-flash")


class AIModelService:
    """Lớp cung cấp dịch vụ phân tích bằng mô hình AI Gemini."""

    def __init__(self, model_provider="gemini"):
        """
        Khởi tạo dịch vụ mô hình AI.

        Tham số:
            model_provider: nhà cung cấp mô hình (mặc định là "gemini")
        """
        if not GOOGLE_API_KEY:
            raise ValueError("Không tìm thấy Google API key. Hãy thiết lập biến môi trường GOOGLE_API_KEY")

        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(DEFAULT_GEMINI_MODEL)

    def analyze_email(self, email_content, prompt):
        """
        Phân tích email bằng mô hình AI.

        Tham số:
            email_content: Nội dung email cần phân tích
            prompt: Yêu cầu hướng dẫn mô hình phân tích email

        Trả về:
            Kết quả phân tích từ mô hình AI
        """
        # Kết hợp prompt và nội dung email
        full_prompt = f"""
Dưới đây là nội dung email cần phân tích:

EMAIL_CONTENT:
{email_content}

YÊU CẦU:
{prompt}

Vui lòng trả lời dưới dạng JSON với các trường: 
- "tom_tat": tóm tắt ngắn gọn nội dung email
- "tu_khoa_quan_trong": danh sách các từ khóa quan trọng
- "hanh_dong": danh sách các hành động cần thực hiện (nếu có)
- "phan_tich_them": các phân tích bổ sung khác theo yêu cầu
"""

        # Gọi API của mô hình Gemini
        return self._call_gemini_api(full_prompt)

    def _call_gemini_api(self, prompt):
        """
        Gọi API của Gemini để phân tích.

        Tham số:
            prompt: Prompt đầy đủ bao gồm nội dung email và yêu cầu

        Trả về:
            Kết quả phân tích dạng JSON
        """
        try:
            response = self.model.generate_content(prompt)

            # Trích xuất nội dung JSON từ phản hồi
            response_text = response.text

            # Tìm và trích xuất JSON từ phản hồi
            json_content = self._extract_json_from_text(response_text)

            # Nếu không thể parse JSON, trả về phản hồi nguyên bản
            if not json_content:
                return {"error": False, "raw_response": response_text}

            return {"error": False, **json_content}

        except Exception as e:
            error_message = str(e)
            return {"error": True, "message": error_message}

    def _extract_json_from_text(self, text):
        """
        Trích xuất nội dung JSON từ text.

        Tham số:
            text: Văn bản chứa JSON

        Trả về:
            Đối tượng JSON hoặc None nếu không thể trích xuất
        """
        try:
            # Tìm kiếm chuỗi JSON trong text
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)

            if json_match:
                # Nếu JSON được bọc trong khối mã markdown
                json_str = json_match.group(1)
            else:
                # Nếu toàn bộ văn bản là JSON
                json_str = text

            # Parse JSON
            return json.loads(json_str)

        except Exception as e:
            print(f"Lỗi khi trích xuất JSON: {str(e)}")
            return None

    def analyze_conversation(self, conversation_messages, prompt):
        """
        Phân tích chuỗi hội thoại email.

        Tham số:
            conversation_messages: Danh sách các tin nhắn trong chuỗi hội thoại
            prompt: Yêu cầu hướng dẫn mô hình phân tích chuỗi hội thoại

        Trả về:
            Kết quả phân tích từ mô hình AI
        """
        # Tổng hợp nội dung chuỗi hội thoại
        conversation_content = ""

        for i, message in enumerate(conversation_messages):
            # Trích xuất thông tin cần thiết từ mỗi tin nhắn
            subject = message.get('subject', 'Không có chủ đề')
            sender = message.get('sender', 'Không xác định')
            body = message.get('body', '') or message.get('snippet', '')

            conversation_content += f"--- EMAIL {i+1} ---\n"
            conversation_content += f"Từ: {sender}\n"
            conversation_content += f"Chủ đề: {subject}\n"
            conversation_content += f"Nội dung: {body}\n\n"

        # Kết hợp prompt và nội dung chuỗi hội thoại
        full_prompt = f"""
Dưới đây là nội dung chuỗi hội thoại email cần phân tích:

CONVERSATION_CONTENT:
{conversation_content}

YÊU CẦU:
{prompt}

Vui lòng trả lời dưới dạng JSON với các trường: 
- "tom_tat": tóm tắt ngắn gọn cuộc hội thoại
- "chu_de_chinh": chủ đề chính của cuộc trao đổi
- "dien_bien": diễn biến của cuộc hội thoại theo thời gian
- "nguoi_tham_gia": danh sách và vai trò của những người tham gia
- "cac_van_de": các vấn đề được đề cập hoặc cần giải quyết
- "ket_luan": kết luận hoặc kết quả cuối cùng của cuộc trao đổi (nếu có)
"""

        return self._call_gemini_api(full_prompt)
