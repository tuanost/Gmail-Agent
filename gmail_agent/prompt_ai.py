"""
Module xử lý prompt cho phân tích email bằng AI.
Module này cung cấp các chức năng để xử lý email dựa trên các prompt từ người dùng.
"""

import re
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Import lớp AIModelService để sử dụng các API mô hình AI
from gmail_agent.ai_models import AIModelService

# Import các hàm cần thiết từ email_ai - chỉ giữ lại những hàm thực sự cần
from gmail_agent.email_ai import extract_entities, summarize_text, extract_action_items, extract_email_body

# Tải các biến môi trường
load_dotenv()

# Cấu hình mô hình AI mặc định từ biến môi trường hoặc sử dụng Gemini nếu không được cấu hình
DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER", "gemini")

def analyze_email_with_prompt(email_body, prompt):
    """
    Phân tích email dựa trên prompt từ người dùng sử dụng mô hình AI thực tế.

    Tham số:
        email_body: Nội dung email cần phân tích
        prompt: Câu lệnh từ người dùng mô tả cách phân tích

    Trả về:
        Kết quả phân tích dựa trên prompt
    """
    try:
        # Tạo đối tượng AIModelService với nhà cung cấp mô hình từ cấu hình
        ai_service = AIModelService(model_provider=DEFAULT_AI_PROVIDER)

        # Gửi nội dung email và prompt đến mô hình AI để phân tích
        result = ai_service.analyze_email(email_body, prompt)

        # Kiểm tra lỗi
        if result.get("error", False):
            print(f"Lỗi khi sử dụng API AI: {result.get('message', 'Lỗi không xác định')}")
            # Fallback: Sử dụng phương thức phân tích cục bộ nếu gọi API thất bại
            return _legacy_analyze_email(email_body, prompt)

        return result

    except Exception as e:
        print(f"Lỗi khi phân tích email với AI: {str(e)}")
        # Fallback: Sử dụng phương thức phân tích cục bộ
        return _legacy_analyze_email(email_body, prompt)

# Các hàm legacy để sử dụng khi API AI không khả dụng
def _legacy_analyze_email(email_body, prompt):
    """Phiên bản cũ của hàm phân tích email để sử dụng khi API AI gặp lỗi."""
    if re.search(r'tóm tắt|tổng kết|summary', prompt.lower()):
        # Thực hiện tóm tắt nội dung
        summary = summarize_text(email_body, num_sentences=5)

        # Trích xuất các từ khóa quan trọng
        entities = extract_entities(email_body)
        keywords = []
        for name in entities['potential_names']:
            keywords.append(name)

        # Trích xuất các mục hành động
        action_items = extract_action_items(email_body)

        # Định dạng kết quả
        result = {
            "summary": summary,
            "important_keywords": keywords[:10],  # Giới hạn 10 từ khóa
            "action_items": action_items
        }

        return result
    else:
        # Mặc định xử lý chung
        summary = summarize_text(email_body)
        return {"summary": summary}

def format_analysis_result(result):
    """
    Định dạng kết quả phân tích để hiển thị cho người dùng.

    Tham số:
        result: Kết quả phân tích từ hàm analyze_email_with_prompt

    Trả về:
        Chuỗi đã định dạng để hiển thị
    """
    output = "===== KẾT QUẢ PHÂN TÍCH EMAIL =====\n\n"

    # Hiển thị thông tin về chuỗi hội thoại nếu có
    if "subject" in result:
        output += f"📧 CHỦ ĐỀ: {result['subject']}\n"

    if "message_count" in result:
        output += f"📊 SỐ TIN NHẮN: {result['message_count']}\n\n"

    if "summary" in result:
        output += "📝 TÓM TẮT:\n"
        output += result["summary"]
        output += "\n\n"

    if "tom_tat" in result:
        output += "📝 TÓM TẮT:\n"
        output += result["tom_tat"]
        output += "\n\n"

    if "important_keywords" in result and result["important_keywords"]:
        output += "🔑 TỪ KHÓA QUAN TRỌNG:\n"
        for keyword in result["important_keywords"]:
            output += f"  • {keyword}\n"
        output += "\n"

    if "tu_khoa_quan_trong" in result and result["tu_khoa_quan_trong"]:
        output += "🔑 TỪ KHÓA QUAN TRỌNG:\n"
        for keyword in result["tu_khoa_quan_trong"]:
            output += f"  • {keyword}\n"
        output += "\n"

    if "action_items" in result and result["action_items"]:
        output += "✅ HÀNH ĐỘNG CẦN THỰC HIỆN:\n"
        for action in result["action_items"]:
            output += f"  • {action}\n"
        output += "\n"

    if "hanh_dong" in result and result["hanh_dong"]:
        output += "✅ HÀNH ĐỘNG CẦN THỰC HIỆN:\n"
        for action in result["hanh_dong"]:
            output += f"  • {action}\n"
        output += "\n"

    if "phan_tich_them" in result and result["phan_tich_them"]:
        output += "📌 PHÂN TÍCH THÊM:\n"
        if isinstance(result["phan_tich_them"], str):
            output += result["phan_tich_them"] + "\n\n"
        elif isinstance(result["phan_tich_them"], list):
            for item in result["phan_tich_them"]:
                output += f"  • {item}\n"
            output += "\n"
        elif isinstance(result["phan_tich_them"], dict):
            for key, value in result["phan_tich_them"].items():
                output += f"  • {key}: {value}\n"
            output += "\n"

    return output

def save_analysis_result(result, file_name):
    """
    Lưu kết quả phân tích vào một file JSON.

    Tham số:
        result: Kết quả phân tích
        file_name: Tên file để lưu kết quả
    """
    # Đảm bảo thư mục tồn tại
    os.makedirs("email_analysis_results", exist_ok=True)

    file_path = os.path.join("email_analysis_results", file_name)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return file_path

def highlight_keywords_in_text(text, keywords):
    """
    Làm nổi bật từ khóa trong văn bản.

    Tham số:
        text: Văn bản cần làm nổi bật
        keywords: Danh sách các từ khóa cần làm nổi bật

    Trả về:
        Văn bản với các từ khóa được làm nổi bật
    """
    highlighted_text = text

    for keyword in keywords:
        if len(keyword.strip()) > 2:  # Bỏ qua các từ khóa quá ngắn
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            highlighted_text = pattern.sub(f"\033[1m\033[93m{keyword}\033[0m", highlighted_text)

    return highlighted_text
