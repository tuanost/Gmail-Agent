"""
Module tích hợp mô hình AI Gemini, OpenAI và Ollama.
Module này cung cấp các hàm để gửi prompt đến API của các mô hình AI
và xử lý kết quả trả về.
"""
import os
import json
import logging
import re
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tải các biến môi trường từ file .env
load_dotenv()

# Import AI connector for model access
from gmail_agent.ai_connector import generate_ai_response

class AIModelService:
    """Lớp cung cấp dịch vụ phân tích bằng các mô hình AI."""

    def __init__(self):
        """
        Khởi tạo dịch vụ mô hình AI.
        Luôn lấy provider và model từ biến môi trường đã được chọn ở đầu chương trình.
        """
        self.model_provider = os.environ.get("CURRENT_AI_PROVIDER")
        self.model_name = os.environ.get("CURRENT_AI_MODEL")
        if not self.model_provider:
            raise ValueError("Chưa thiết lập CURRENT_AI_PROVIDER. Hãy chọn AI provider trước khi sử dụng.")
        if not self.model_name:
            raise ValueError("Chưa thiết lập CURRENT_AI_MODEL. Hãy chọn AI model trước khi sử dụng.")

    def analyze_with_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Phân tích nội dung bằng mô hình AI với prompt hoàn chỉnh.

        Args:
            prompt: Prompt hoàn chỉnh (đã được tạo từ _create_email_analysis_prompt hoặc _create_gitlab_analysis_prompt)

        Returns:
            Kết quả phân tích dạng dictionary
        """
        logger.info(f"Đang phân tích với prompt: {prompt}")
        success, response, details = generate_ai_response(
            prompt=prompt,
            provider=self.model_provider,
            model_name=self.model_name,
            temperature=0.3
        )
        if not success:
            logger.error(f"Lỗi khi gọi API {self.model_provider}: {response}")
            return {
                "error": True,
                "message": response,
                "phan_tich": "Không thể kết nối tới API AI để phân tích."
            }
        try:
            result = self._parse_ai_response(response)
            result["model_info"] = details
            return result
        except Exception as e:
            logger.exception(f"Lỗi khi xử lý phản hồi từ mô hình AI: {str(e)}")
            return {
                "error": True,
                "message": str(e),
                "phan_tich": "Có lỗi khi xử lý phản hồi từ mô hình AI."
            }

    def _create_email_analysis_prompt(self, email_content: str, user_prompt: str) -> str:
        """
        Tạo prompt phân tích đầy đủ cho email thông thường (tóm tắt email, gợi ý trả lời).

        Args:
            email_content: Nội dung email cần phân tích
            user_prompt: Prompt từ người dùng

        Returns:
            Prompt đầy đủ để gửi đến mô hình AI
        """
        # Xây dựng prompt đầy đủ
        full_prompt = f"""
{user_prompt}

---

EMAIL CẦN PHÂN TÍCH:
{email_content}

---

Vui lòng tóm tắt chi tiết email trên theo yêu cầu. Phản hồi dưới dạng JSON với các trường sau:
{{
  "phan_tich": "<phân tích chi tiết>",
  "chu_de_chinh": "<chủ đề chính>",
  "dien_bien": "<diễn biến>",
  "nguoi_tham_gia": "<danh sách người tham gia>",
  "cac_van_de": "<các vấn đề chính>",
  "goi_y_reply": [
    "<Gợi ý trả lời option 1>",
    "<Gợi ý trả lời option 2>",
    "<Gợi ý trả lời option 3>"
  ]
}}

Lưu ý: Chỉ trả về dữ liệu JSON, không có văn bản giới thiệu hoặc bao quanh.
"""
        return full_prompt

    def _create_gitlab_analysis_prompt(self, pipeline_logs: str, user_prompt: str = "") -> str:
        """
        Tạo prompt phân tích email Gitlab (tóm tắt lỗi pipeline, gợi ý chỉnh sửa).

        Args:
            pipeline_logs: Nội dung log pipeline cần phân tích
            user_prompt: Prompt bổ sung (nếu có)

        Returns:
            Prompt đầy đủ để gửi đến mô hình AI
        """
        full_prompt = f"""
{user_prompt}

---

LOG LỖI PIPELINE CẦN PHÂN TÍCH:
{pipeline_logs}

---

Vui lòng phân tích chi tiết lỗi pipeline trên, tóm tắt nguyên nhân, và đưa ra một đoạn gợi ý chỉnh sửa cho pipeline/email này. Phản hồi dưới dạng JSON với các trường sau:
{{
  "tom_tat": "<Tóm tắt lỗi pipeline>",
  "nguyen_nhan": "<Nguyên nhân>",
  "goi_y_chinh_sua": "<Gợi ý chỉnh sửa cho pipeline này>"
}}

Lưu ý: Chỉ trả về dữ liệu JSON, không có văn bản giới thiệu hoặc bao quanh.
"""
        return full_prompt

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """
        Phân tích phản hồi từ mô hình AI thành dạng cấu trúc.

        Args:
            response: Phản hồi từ mô hình AI

        Returns:
            Dictionary chứa dữ liệu đã phân tích
        """
        # Tìm phần JSON trong phản hồi
        json_match = re.search(r'({[\s\S]*})', response)

        if json_match:
            try:
                # Trích xuất và phân tích phần JSON
                json_text = json_match.group(1)
                result = json.loads(json_text)
                return result
            except json.JSONDecodeError:
                logger.warning("Không thể phân tích JSON từ phản hồi. Sử dụng phản hồi thô.")
                pass

        # Trường hợp không tìm thấy JSON, trả về dạng cấu trúc đơn giản
        return {
            "phan_tich": response
        }

    def get_provider_name(self) -> str:
        """
        Lấy tên nhà cung cấp mô hình hiện tại.

        Returns:
            Tên nhà cung cấp mô hình
        """
        return self.model_provider

    def get_model_name(self) -> str:
        """
        Lấy tên mô hình hiện tại.

        Returns:
            Tên mô hình
        """
        return self.model_name
