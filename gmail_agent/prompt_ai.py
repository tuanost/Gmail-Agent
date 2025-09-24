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

# Import các hàm cần thiết từ email_ai
from gmail_agent.email_ai import extract_email_body

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tải các biến môi trường
load_dotenv()

# Cấu hình mô hình AI mặc định từ biến môi trường
DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER")

def analyze_email_with_prompt(email_body: str, prompt: str) -> Dict[str, Any]:
    """
    Phân tích email dựa trên prompt từ người dùng sử dụng mô hình AI.

    Args:
        email_body: Nội dung email cần phân tích
        prompt: Câu lệnh từ người dùng mô tả cách phân tích

    Returns:
        Kết quả phân tích dựa trên prompt
    """
    logger.info(f"Đang phân tích email với prompt: {prompt[:50]}...")

    try:
        # Tạo đối tượng AIModelService với nhà cung cấp mô hình từ cấu hình
        ai_service = AIModelService(model_provider=DEFAULT_AI_PROVIDER)

        # Gửi nội dung email và prompt đến mô hình AI để phân tích
        result = ai_service.analyze_email(email_body, prompt)

        # Lưu prompt đã sử dụng vào kết quả để tham khảo sau này
        result["prompt_su_dung"] = prompt

        # Kiểm tra lỗi
        if result.get("error", False):
            logger.error(f"Lỗi khi sử dụng API AI: {result.get('message', 'Lỗi không xác định')}")
            # Fallback: Sử dụng phương thức phân tích cục bộ nếu gọi API thất bại
            return _legacy_analyze_email(email_body, prompt)

        logger.info("Đã phân tích email thành công")
        return result

    except Exception as e:
        logger.exception(f"Lỗi khi phân tích email với AI: {str(e)}")
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

    # Mặc định xử lý chung
    result = {
        "prompt_su_dung": prompt,
        "phan_tich": "Không thể kết nối tới API AI. Đây là phân tích cục bộ đơn giản."
    }

    return result

def format_analysis_result(result: Dict[str, Any]) -> str:
    """
    Định dạng kết quả phân tích để hiển thị cho người dùng.

    Args:
        result: Kết quả phân tích từ hàm analyze_email_with_prompt

    Returns:
        Chuỗi đã định dạng để hiển thị
    """
    output = "===== KẾT QUẢ PHÂN TÍCH EMAIL =====\n\n"

    # Hiển thị prompt được sử dụng cho phân tích ở đầu kết quả
    if "prompt_su_dung" in result:
        output += "🔍 PROMPT ĐÃ SỬ DỤNG:\n"
        output += f"{result['prompt_su_dung']}\n\n"

    # Hiển thị thông tin về chuỗi hội thoại nếu có
    if "subject" in result:
        output += f"📧 CHỦ ĐỀ: {result['subject']}\n"

    if "message_count" in result:
        output += f"📊 SỐ TIN NHẮN: {result['message_count']}\n\n"

    # Phân tích
    if "phan_tich" in result and result["phan_tich"]:
        output += "📌 PHÂN TÍCH:\n"
        output += _format_analysis_content(result["phan_tich"])

    # Thêm các trường phân tích hội thoại nếu có
    _append_conversation_analysis(result, output)

    return output

def _format_analysis_content(content: Union[str, List[str], Dict[str, Any]]) -> str:
    """
    Định dạng nội dung phân tích dựa trên loại dữ liệu.

    Args:
        content: Nội dung phân tích (chuỗi, danh sách hoặc dictionary)

    Returns:
        Chuỗi đã định dạng
    """
    formatted_output = ""

    if isinstance(content, str):
        formatted_output = content + "\n\n"
    elif isinstance(content, list):
        for item in content:
            formatted_output += f"  • {item}\n"
        formatted_output += "\n"
    elif isinstance(content, dict):
        for key, value in content.items():
            formatted_output += f"  • {key}: {value}\n"
        formatted_output += "\n"

    return formatted_output

def _append_conversation_analysis(result: Dict[str, Any], output: str) -> None:
    """
    Thêm các trường phân tích hội thoại vào output nếu có.

    Args:
        result: Kết quả phân tích
        output: Chuỗi output để thêm vào
    """
    conversation_fields = {
        "chu_de_chinh": "CHỦ ĐỀ CHÍNH",
        "dien_bien": "DIỄN BIẾN HỘI THOẠI",
        "nguoi_tham_gia": "NGƯỜI THAM GIA",
        "cac_van_de": "CÁC VẤN ĐỀ",
        "ket_luan": "KẾT LUẬN"
    }

    for field, title in conversation_fields.items():
        if field in result and result[field]:
            output += f"📝 {title}:\n"
            output += _format_analysis_content(result[field])

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
