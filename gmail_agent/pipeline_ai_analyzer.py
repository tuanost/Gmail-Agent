"""
Module tích hợp AI model vào quá trình phân tích lỗi pipeline.
Sử dụng ai_connector để kết nối với các AI model khác nhau.
"""

import json
import os
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal

# Tải biến môi trường một cách rõ ràng ngay từ đầu
from dotenv import load_dotenv

# Đảm bảo load dotenv từ đường dẫn chính xác và ghi đè biến môi trường
env_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_file = os.path.join(env_path, '.env')
load_dotenv(dotenv_path=env_file, override=True)

# Import ai_connector để kết nối với các model AI
from gmail_agent.ai_connector import (
    generate_ai_response,
    setup_ai_model,
    list_available_ai_providers,
    list_ollama_models
)

# Thư mục lưu kết quả phân tích
ANALYSIS_DIR = "email_analysis_results"

def generate_ai_prompt_for_pipeline_error(
    error_type: str,
    logs: str,
    error_lines: List[str],
    project_info: Dict[str, str]
) -> str:
    """
    Tạo prompt cho AI để phân tích lỗi pipeline và đưa ra gợi ý.

    Args:
        error_type: Loại lỗi được xác định từ quá trình phân tích ban đầu
        logs: Log đầy đủ của pipeline
        error_lines: Các dòng lỗi đã trích xuất
        project_info: Thông tin về dự án (tên, commit, môi trường)

    Returns:
        str: Prompt đầy đủ cho AI
    """
    # Giới hạn logs để tránh quá dài
    if logs and len(logs) > 3000:
        logs = logs[:1500] + "\n...[log quá dài, đã được cắt bớt]...\n" + logs[-1500:]

    # Format các dòng lỗi
    formatted_error_lines = chr(10).join([f"- {line}" for line in error_lines[:10]])
    if len(error_lines) > 10:
        formatted_error_lines += f"\n... và {len(error_lines) - 10} dòng lỗi khác"

    # Lấy prompt từ biến môi trường
    template = os.getenv("PIPELINE_ERROR_PROMPT")

    # Thay thế các placeholder với giá trị thực tế
    prompt = template.format(
        project_name=project_info.get('project_name', 'Không xác định'),
        commit_id=project_info.get('commit_id', 'Không xác định'),
        environment=project_info.get('environment', 'Không xác định'),
        error_type=error_type,
        error_lines=formatted_error_lines,
        logs=logs
    )

    return prompt

def analyze_pipeline_error_with_ai(
    pipeline_logs: Dict[str, Any],
    project_info: Dict[str, str],
    temperature: float = 0.2,
    provider: str = "auto",
    model_name: str = None
) -> Optional[Dict[str, Any]]:
    """
    Sử dụng AI để phân tích log lỗi pipeline và đưa ra gợi ý cách sửa.
    Sử dụng ai_connector để kết nối với các AI model.

    Args:
        pipeline_logs: Dictionary chứa thông tin log lỗi pipeline
        project_info: Thông tin về dự án
        temperature: Độ sáng tạo của AI (0.0-1.0, thấp hơn = chính xác hơn)
        provider: Nhà cung cấp AI ("google", "openai", "ollama", hoặc "auto")
        model_name: Tên model cụ thể (nếu không chọn sẽ dùng mặc định của provider)

    Returns:
        Dict hoặc None: Kết quả phân tích của AI hoặc None nếu thất bại
    """
    # Kiểm tra dữ liệu đầu vào
    if not pipeline_logs or not pipeline_logs.get("success"):
        print("Không có dữ liệu log hợp lệ để phân tích")
        return None

    logs = pipeline_logs.get("logs", "")
    error_lines = pipeline_logs.get("error_lines", [])

    if not logs and not error_lines:
        print("Không tìm thấy dữ liệu lỗi để phân tích")
        return None

    # Xác định loại lỗi ban đầu (sử dụng từ phân tích trước nếu có)
    if "error_type" in project_info and project_info["error_type"] != "unknown":
        error_type = project_info["error_type"]
    else:
        # Xác định loại lỗi cơ bản từ log
        error_type = "unknown"
        if logs:
            if any(term in logs.lower() for term in ["build failed", "compilation error"]):
                error_type = "build_error"
            elif any(term in logs.lower() for term in ["test failed", "assertion"]):
                error_type = "test_failure"
            elif any(term in logs.lower() for term in ["dependency", "could not resolve"]):
                error_type = "dependency_error"
            elif any(term in logs.lower() for term in ["deploy", "kubernetes"]):
                error_type = "deployment_error"

    # Tạo prompt cho AI
    prompt = generate_ai_prompt_for_pipeline_error(error_type, logs, error_lines, project_info)

    # Sử dụng ai_connector để gọi API AI model
    print(f"\nĐang phân tích lỗi pipeline bằng AI ({provider})...")
    success, ai_response, result_info = generate_ai_response(prompt, provider, model_name, temperature)

    if not success or not ai_response:
        print(f"Không thể lấy phản hồi từ AI: {ai_response}")
        # Thử provider khác nếu đang dùng "auto"
        if provider == "auto":
            providers = list_available_ai_providers()
            current_provider = result_info.get("provider", "")

            if current_provider and current_provider in providers:
                providers.remove(current_provider)

            for next_provider in providers:
                print(f"Đang thử lại với {next_provider}...")
                result = analyze_pipeline_error_with_ai(
                    pipeline_logs, project_info, temperature, next_provider
                )
                if result:
                    return result

        return None

    # Tạo kết quả phân tích
    ai_analysis = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "error_type": error_type,
        "ai_analysis": ai_response,
        "project_info": project_info,
        "provider": result_info.get("provider", "unknown"),
        "model": result_info.get("model", "unknown")
    }

    # Lưu kết quả phân tích
    save_ai_analysis_result(ai_analysis)

    return ai_analysis

def save_ai_analysis_result(analysis: Dict[str, Any]) -> str:
    """
    Lưu kết quả phân tích của AI vào file JSON.

    Args:
        analysis: Kết quả phân tích của AI

    Returns:
        str: Đường dẫn đến file đã lưu
    """
    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists(ANALYSIS_DIR):
        os.makedirs(ANALYSIS_DIR)

    # Tạo tên file dựa trên thời gian
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_name = analysis.get("project_info", {}).get("project_name", "unknown")
    provider = analysis.get("provider", "ai")
    filename = f"ai_analysis_{provider}_{project_name}_{timestamp}.json"
    filepath = os.path.join(ANALYSIS_DIR, filename)

    # Lưu vào file JSON
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    print(f"\nĐã lưu kết quả phân tích AI vào: {filepath}")
    return filepath

def format_ai_analysis_for_display(ai_analysis: Dict[str, Any]) -> str:
    """
    Định dạng kết quả phân tích của AI để hiển thị cho người dùng.

    Args:
        ai_analysis: Kết quả phân tích của AI

    Returns:
        str: Kết quả phân tích đã được định dạng
    """
    if not ai_analysis or "ai_analysis" not in ai_analysis:
        return "Không có kết quả phân tích AI"

    # Lấy kết quả phân tích
    analysis_text = ai_analysis["ai_analysis"]

    # Tạo header
    formatted_result = "=" * 80 + "\n"
    formatted_result += "PHÂN TÍCH LỖI PIPELINE BẰNG AI".center(80) + "\n"
    formatted_result += "=" * 80 + "\n\n"

    # Thêm thông tin dự án
    project_info = ai_analysis.get("project_info", {})
    formatted_result += f"Dự án: {project_info.get('project_name', 'Không xác định')}\n"
    formatted_result += f"Commit ID: {project_info.get('commit_id', 'Không xác định')}\n"
    formatted_result += f"Môi trường: {project_info.get('environment', 'Không xác định')}\n"
    formatted_result += f"Loại lỗi: {ai_analysis.get('error_type', 'Không xác định')}\n"
    formatted_result += f"AI Model: {ai_analysis.get('provider', 'unknown')}/{ai_analysis.get('model', 'unknown')}\n\n"

    # Thêm kết quả phân tích của AI
    formatted_result += analysis_text

    # Thêm footer
    formatted_result += "\n\n" + "=" * 80 + "\n"
    formatted_result += f"Phân tích được tạo vào: {ai_analysis.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}\n"

    return formatted_result

def analyze_mockup_pipeline_with_ai(
    error_type: str,
    provider: str = "auto",
    model_name: str = None
) -> Optional[Dict[str, Any]]:
    """
    Phân tích mockup data với AI model.

    Args:
        error_type: Loại lỗi mockup muốn phân tích
        provider: Nhà cung cấp AI ("google", "openai", "ollama", hoặc "auto")
        model_name: Tên model cụ thể (tùy chọn)

    Returns:
        Dict hoặc None: Kết quả phân tích của AI hoặc None nếu thất bại
    """
    try:
        # Import các module cần thiết
        from gmail_agent.pipeline_mock_data import get_mock_pipeline_logs, get_all_mock_error_types

        # Kiểm tra loại lỗi có hợp lệ không
        available_types = get_all_mock_error_types()
        if error_type not in available_types:
            print(f"Loại lỗi không hợp lệ. Các loại có sẵn: {', '.join(available_types)}")
            return None

        # Lấy mockup data
        mock_logs = get_mock_pipeline_logs(error_type)
        if not mock_logs:
            print(f"Không tìm thấy mockup data cho loại lỗi: {error_type}")
            return None

        # Tạo thông tin dự án giả lập
        project_info = {
            "project_name": f"mockup-{error_type}-project",
            "commit_id": "a1b2c3d4e5f6g7h8i9j0",
            "environment": "test-environment",
            "error_type": error_type
        }

        # Phân tích với AI
        ai_result = analyze_pipeline_error_with_ai(
            mock_logs, project_info, provider=provider, model_name=model_name
        )
        return ai_result

    except ImportError:
        print("Không thể import module pipeline_mock_data. Vui lòng kiểm tra cài đặt.")
        return None
    except Exception as e:
        print(f"Lỗi khi phân tích mockup data: {str(e)}")
        return None
