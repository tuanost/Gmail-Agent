"""
Module tích hợp mô hình AI Gemini.
Module này cung cấp các hàm để gửi prompt đến API của mô hình AI
và xử lý kết quả trả về.
"""
import os
import json
import logging
import re
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv
import google.generativeai as genai

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tải các biến môi trường từ file .env
load_dotenv()

# Cấu hình API keys từ biến môi trường
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Cấu hình mặc định cho mô hình từ biến môi trường
DEFAULT_GEMINI_MODEL = os.getenv("DEFAULT_GEMINI_MODEL", "gemini-1.5-flash")


class AIModelService:
    """Lớp cung cấp dịch vụ phân tích bằng mô hình AI Gemini."""

    def __init__(self, model_provider: str = "gemini"):
        """
        Khởi tạo dịch vụ mô hình AI.

        Args:
            model_provider: Nhà cung cấp mô hình (mặc định là "gemini")

        Raises:
            ValueError: Nếu không tìm thấy API key
        """
        if not GOOGLE_API_KEY:
            logger.error("Không tìm thấy Google API key")
            raise ValueError("Không tìm thấy Google API key. Hãy thiết lập biến môi trường GOOGLE_API_KEY")

        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(DEFAULT_GEMINI_MODEL)
        logger.info(f"Đã khởi tạo AI Model Service với mô hình {DEFAULT_GEMINI_MODEL}")

    def analyze_email(self, email_content: str, prompt: str) -> Dict[str, Any]:
        """
        Phân tích email bằng mô hình AI.

        Args:
            email_content: Nội dung email cần phân tích
            prompt: Yêu cầu hướng dẫn mô hình phân tích email

        Returns:
            Kết quả phân tích từ mô hình AI
        """
        logger.info("Đang phân tích email với prompt tùy chỉnh")

        # Kết hợp prompt và nội dung email
        full_prompt = self._create_email_analysis_prompt(email_content, prompt)

        # Gọi API của mô hình Gemini
        return self._call_gemini_api(full_prompt)

    def _create_email_analysis_prompt(self, email_content: str, prompt: str) -> str:
        """
        Tạo prompt đầy đủ cho việc phân tích email.

        Args:
            email_content: Nội dung email cần phân tích
            prompt: Prompt của người dùng

        Returns:
            Prompt đầy đủ đã được định dạng
        """
        return f"""
Dưới đây là nội dung email cần phân tích:

EMAIL_CONTENT:
{email_content}

YÊU CẦU:
{prompt}

Vui lòng trả lời dưới dạng JSON với trường: 
- "phan_tich_them": các phân tích bổ sung theo yêu cầu
"""

    def _call_gemini_api(self, prompt: str) -> Dict[str, Any]:
        """
        Gọi API của Gemini để phân tích.

        Args:
            prompt: Prompt đầy đủ bao gồm nội dung email và yêu cầu

        Returns:
            Kết quả phân tích dạng JSON
        """
        try:
            logger.debug(f"Gửi prompt đến API Gemini: {prompt[:100]}...")
            response = self.model.generate_content(prompt)
            response_text = response.text

            # Tìm và trích xuất JSON từ phản hồi
            json_content = self._extract_json_from_text(response_text)

            # Nếu không thể parse JSON, trả về phản hồi nguyên bản
            if not json_content:
                logger.warning("Không thể phân tích JSON từ phản hồi. Trả về văn bản gốc.")
                return {"error": False, "raw_response": response_text}

            logger.info("Đã nhận phản hồi JSON hợp lệ từ API Gemini")
            return {"error": False, **json_content}

        except Exception as e:
            error_message = str(e)
            logger.error(f"Lỗi khi gọi API Gemini: {error_message}")
            return {"error": True, "message": error_message}

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Trích xuất nội dung JSON từ text.

        Args:
            text: Văn bản chứa JSON

        Returns:
            Đối tượng JSON hoặc None nếu không thể trích xuất
        """
        try:
            # Tìm kiếm chuỗi JSON trong text - hỗ trợ nhiều định dạng
            json_patterns = [
                r'```json\s*([\s\S]*?)\s*```',  # Markdown code block
                r'```\s*([\s\S]*?)\s*```',      # Generic code block
                r'\{[\s\S]*\}'                  # Plain JSON
            ]

            for pattern in json_patterns:
                json_match = re.search(pattern, text)
                if json_match:
                    if pattern.endswith('}'):  # Nếu là pattern JSON thuần
                        json_str = json_match.group(0)
                    else:
                        json_str = json_match.group(1)

                    return json.loads(json_str)

            # Nếu không tìm thấy theo pattern, thử parse toàn bộ văn bản
            return json.loads(text)

        except Exception as e:
            logger.warning(f"Lỗi khi trích xuất JSON: {str(e)}")
            return None

    def analyze_conversation(self, conversation_messages: List[Dict[str, str]], prompt: str) -> Dict[str, Any]:
        """
        Phân tích chuỗi hội thoại email.

        Args:
            conversation_messages: Danh sách các tin nhắn trong chuỗi hội thoại
            prompt: Yêu cầu hướng dẫn mô hình phân tích chuỗi hội thoại

        Returns:
            Kết quả phân tích từ mô hình AI
        """
        logger.info(f"Đang phân tích chuỗi hội thoại với {len(conversation_messages)} tin nhắn")

        # Tổng hợp nội dung chuỗi hội thoại
        conversation_content = self._format_conversation_content(conversation_messages)

        # Kết hợp prompt và nội dung chuỗi hội thoại
        full_prompt = self._create_conversation_analysis_prompt(conversation_content, prompt)

        return self._call_gemini_api(full_prompt)

    def _format_conversation_content(self, conversation_messages: List[Dict[str, str]]) -> str:
        """
        Định dạng nội dung cuộc hội thoại để phân tích.

        Args:
            conversation_messages: Danh sách các tin nhắn trong hội thoại

        Returns:
            Chuỗi định dạng của nội dung hội thoại
        """
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

        return conversation_content

    def _create_conversation_analysis_prompt(self, conversation_content: str, prompt: str) -> str:
        """
        Tạo prompt đầy đủ cho việc phân tích cuộc hội thoại.

        Args:
            conversation_content: Nội dung cuộc hội thoại đã định dạng
            prompt: Prompt của người dùng

        Returns:
            Prompt đầy đủ đã được định dạng
        """
        return f"""
Dưới đây là nội dung chuỗi hội thoại email cần phân tích:

CONVERSATION_CONTENT:
{conversation_content}

YÊU CẦU:
{prompt}

Vui lòng trả lời dưới dạng JSON với các trường: 
- "chu_de_chinh": chủ đề chính của cuộc trao đổi
- "dien_bien": diễn biến của cuộc hội thoại theo thời gian
- "nguoi_tham_gia": danh sách và vai trò của những người tham gia
- "cac_van_de": các vấn đề được đề cập hoặc cần giải quyết
- "ket_luan": kết luận hoặc kết quả cuối cùng của cuộc trao đổi (nếu có)
"""
