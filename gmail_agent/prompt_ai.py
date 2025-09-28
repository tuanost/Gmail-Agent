"""
Module xử lý prompt cho phân tích email bằng AI.
Module này cung cấp các chức năng để xử lý email dựa trên các prompt từ người dùng.
"""

import re
import json
import os
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dotenv import load_dotenv

# Import lớp AIModelService để sử dụng các API mô hình AI
from gmail_agent.ai_models import AIModelService

# Import các hàm cần thiết từ email_extractor
from gmail_agent.email_extractor import extract_email_body

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tải các biến môi trường
load_dotenv()

# Cấu hình mô hình AI mặc định từ biến môi trường
DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER")

def analyze_email_with_prompt(email_body: str, prompt: str) -> Dict[str, Any]:
    """
    Phân tích email với prompt tùy chỉnh.

    Args:
        email_body: Nội dung email cần phân tích
        prompt: Prompt hoàn chỉnh hoặc chỉ dẫn ngắn

    Returns:
        Kết quả phân tích dạng dictionary
    """
    ai_service = AIModelService()
    # Nếu prompt chưa phải prompt hoàn chỉnh, tạo bằng _create_email_analysis_prompt
    if not any(key in prompt for key in ["phan_tich", "goi_y_reply", "goi_y_chinh_sua", "tom_tat", "nguyen_nhan"]):
        prompt = ai_service._create_email_analysis_prompt(email_body, prompt)
    result = ai_service.analyze_with_prompt(prompt)
    return result

def analyze_email_with_prompt(email_body: str, prompt: str) -> Dict[str, Any]:
    """
    Phân tích email dựa trên prompt từ người dùng sử dụng mô hình AI.

    Args:
        email_body: Nội dung email cần phân tích
        prompt: Câu lệnh từ người dùng mô tả cách phân tích

    Returns:
        Kết quả phân tích dựa trên prompt
    """
    try:
        # Sử dụng AI provider và model đã được chọn bởi người dùng
        selected_provider = os.environ.get("CURRENT_AI_PROVIDER", DEFAULT_AI_PROVIDER)
        selected_model = os.environ.get("CURRENT_AI_MODEL", None)

        # Tạo đối tượng AIModelService với nhà cung cấp và model được chọn
        ai_service = AIModelService(
            model_provider=selected_provider,
            model_name=selected_model
        )

        # Gửi nội dung email và prompt đến mô hình AI để phân tích
        result = ai_service.analyze_email(email_body, prompt)

        # Lưu prompt đã sử dụng và thông tin model vào kết quả để tham khảo sau này
        result["prompt_su_dung"] = prompt
        result["ai_provider"] = selected_provider
        result["ai_model"] = selected_model

        # Kiểm tra lỗi
        if result.get("error", False):
            logger.error(f"Lỗi khi sử dụng API AI: {result.get('message', 'Lỗi không xác định')}")
            # Fallback: Sử dụng phương thức phân tích cục bộ nếu gọi API thất bại
            return _legacy_analyze_email(email_body, prompt)

        return result

    except Exception as e:
        logger.error(f"Lỗi khi phân tích email với AI: {str(e)}")
        # Fallback: Sử dụng phương thức phân tích cục bộ
        return _legacy_analyze_email(email_body, prompt)

def _legacy_analyze_email(email_body: str, prompt: str) -> Dict[str, Any]:
    """
    Phiên bản cũ của hàm phân tích email để sử dụng khi API AI gặp lỗi.

    Args:
        email_body: Nội dung email cần phân tích
        prompt: Prompt người dùng yêu cầu

    Returns:
        Kết quả phân tích đơn giản
    """
    logger.warning("Sử dụng phân tích legacy vì không thể kết nối đến API AI")

    ai_service = AIModelService()
    if not any(key in prompt for key in ["phan_tich", "goi_y_reply", "goi_y_chinh_sua", "tom_tat", "nguyen_nhan"]):
        prompt = ai_service._create_email_analysis_prompt(email_body, prompt)
    return ai_service.analyze_with_prompt(prompt)

def save_analysis_result(result: Dict[str, Any], file_name: str) -> str:
    """
    Lưu kết quả phân tích vào một file JSON.

    Args:
        result: Kết quả phân tích
        file_name: Tên file để lưu kết quả

    Returns:
        Đường dẫn đến file đã lưu
    """
    # Đảm bảo thư mục tồn tại
    output_dir = "email_analysis_results"
    os.makedirs(output_dir, exist_ok=True)

    file_path = os.path.join(output_dir, file_name)

    try:
        # Sắp xếp để đảm bảo prompt_su_dung nằm ở đầu file JSON
        from collections import OrderedDict
        ordered_result = OrderedDict()

        # Đặt prompt_su_dung lên đầu nếu có
        if "prompt_su_dung" in result:
            ordered_result["prompt_su_dung"] = result["prompt_su_dung"]

        # Thêm các trường khác vào OrderedDict
        for key, value in result.items():
            if key != "prompt_su_dung":  # Bỏ qua vì đã thêm ở trên
                ordered_result[key] = value

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(ordered_result, f, ensure_ascii=False, indent=2)

        logger.info(f"Đã lưu kết quả phân tích vào: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Lỗi khi lưu kết quả phân tích: {str(e)}")
        return ""

def generate_analysis_filename(prefix: str = "email_analysis") -> str:
    """
    Tạo tên file có dấu thời gian cho phân tích email.

    Args:
        prefix: Tiền tố cho tên file

    Returns:
        Tên file có dấu thời gian
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.json"

def highlight_keywords_in_text(text: str, keywords: List[str]) -> str:
    """
    Làm nổi bật từ khóa trong văn bản.

    Args:
        text: Văn bản cần làm nổi bật
        keywords: Danh sách các từ khóa cần làm nổi bật

    Returns:
        Văn bản với các từ khóa được làm nổi bật
    """
    if not text or not keywords:
        return text

    highlighted_text = text

    for keyword in keywords:
        if len(keyword.strip()) > 2:  # Bỏ qua các từ khóa quá ngắn
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            highlighted_text = pattern.sub(f"\033[1m\033[93m{keyword}\033[0m", highlighted_text)

    return highlighted_text
