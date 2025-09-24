"""
Module tích hợp AI model vào quá trình phân tích lỗi pipeline.
Hỗ trợ Google Gemini API, OpenAI API và Ollama.
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal

# Thư mục lưu kết quả phân tích
ANALYSIS_DIR = "email_analysis_results"

# Thử import các module AI cần thiết
try:
    import google.generativeai as genai
    from dotenv import load_dotenv
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# Thử import OpenAI API
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Thử import các module AI mã nguồn mở
OLLAMA_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
    # Kiểm tra xem Ollama có khả dụng không
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=1)
        if response.status_code == 200:
            OLLAMA_AVAILABLE = True
    except:
        OLLAMA_AVAILABLE = False
except ImportError:
    REQUESTS_AVAILABLE = False

def setup_ai_model(provider: str = "auto") -> tuple[bool, str]:
    """
    Thiết lập và cấu hình AI model.

    Args:
        provider: Nhà cung cấp AI ("google", "openai", "ollama", hoặc "auto" để tự động chọn)

    Returns:
        tuple: (True/False, provider_name) - Trạng thái thiết lập và nhà cung cấp đang dùng
    """
    # Tải biến môi trường
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    if provider == "auto":
        # Thử thiết lập Google Gemini trước
        if GENAI_AVAILABLE:
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                try:
                    genai.configure(api_key=api_key)
                    # Thử gọi API nhỏ để kiểm tra quota
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content("Hello")
                    if response.text:
                        print("Đã thiết lập Google Gemini API thành công.")
                        return True, "google"
                except Exception as e:
                    print(f"Không thể sử dụng Google Gemini API: {str(e)}")
                    print("Đang thử các model khác...")

        # Thử thiết lập OpenAI nếu Gemini không khả dụng
        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                try:
                    openai.api_key = api_key
                    print("Đã thiết lập OpenAI API thành công.")
                    return True, "openai"
                except Exception as e:
                    print(f"Không thể sử dụng OpenAI API: {str(e)}")
                    print("Đang thử các model khác...")

        # Thử thiết lập Ollama nếu cả Gemini và OpenAI không khả dụng
        if OLLAMA_AVAILABLE:
            try:
                # Kiểm tra các model có sẵn trong Ollama
                response = requests.get("http://localhost:11434/api/tags")
                if response.status_code == 200 and response.json().get("models"):
                    print("Đã thiết lập Ollama thành công.")
                    return True, "ollama"
            except Exception as e:
                print(f"Không thể sử dụng Ollama: {str(e)}")

    elif provider == "google" and GENAI_AVAILABLE:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("Không tìm thấy GOOGLE_API_KEY trong biến môi trường.")
            return False, ""
        
        try:
            genai.configure(api_key=api_key)
            print("Đã thiết lập Google Gemini API thành công.")
            return True, "google"
        except Exception as e:
            print(f"Không thể sử dụng Google Gemini API: {str(e)}")

    elif provider == "openai" and OPENAI_AVAILABLE:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Không tìm thấy OPENAI_API_KEY trong biến môi trường.")
            return False, ""

        try:
            openai.api_key = api_key
            print("Đã thiết lập OpenAI API thành công.")
            return True, "openai"
        except Exception as e:
            print(f"Không thể sử dụng OpenAI API: {str(e)}")

    elif provider == "ollama" and OLLAMA_AVAILABLE:
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                print("Đã thiết lập Ollama thành công.")
                return True, "ollama"
            else:
                print("Không thể kết nối đến Ollama server.")
        except Exception as e:
            print(f"Không thể sử dụng Ollama: {str(e)}")

    # Thông báo lỗi nếu không thể thiết lập
    print("\nKhông thể thiết lập bất kỳ AI model nào.")
    print("Vui lòng thực hiện một trong các cách sau:")
    print("\n1. Sử dụng Google Gemini API:")
    print("   - pip install google-generativeai python-dotenv")
    print("   - Tạo file .env với nội dung: GOOGLE_API_KEY=your_api_key")
    
    print("\n2. Sử dụng OpenAI API:")
    print("   - pip install openai python-dotenv")
    print("   - Tạo file .env với nội dung: OPENAI_API_KEY=your_api_key")

    print("\n3. Sử dụng Ollama (miễn phí, chạy local):")
    print("   - Cài đặt Ollama từ: https://ollama.com/")
    print("   - Chạy lệnh: ollama pull codellama")

    return False, ""

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

    # Tải biến môi trường nếu chưa được tải
    load_dotenv()

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

    Args:
        pipeline_logs: Dictionary chứa thông tin log lỗi pipeline
        project_info: Thông tin về dự án
        temperature: Độ sáng tạo của AI (0.0-1.0, thấp hơn = chính xác hơn)
        provider: Nhà cung cấp AI ("google", "openai", "ollama", hoặc "auto")
        model_name: Tên model cụ thể (nếu không chọn sẽ dùng mặc định của provider)

    Returns:
        Dict hoặc None: Kết quả phân tích của AI hoặc None nếu thất bại
    """
    # Kiểm tra và thiết lập AI model
    success, active_provider = setup_ai_model(provider)
    if not success:
        print("Không thể thiết lập AI model. Vui lòng kiểm tra cấu hình.")
        return None

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

    # Chọn model mặc định nếu không được chỉ định
    if not model_name:
        if active_provider == "google":
            model_name = "gemini-1.5-flash"
        elif active_provider == "openai":
            model_name = "gpt-3.5-turbo" # Hoặc model khác của OpenAI
        elif active_provider == "ollama":
            model_name = "tinyllama" # Sử dụng model mặc định của Ollama

    print(f"\nĐang phân tích lỗi pipeline bằng AI ({active_provider}/{model_name})...")
    
    try:
        ai_response = None
        
        # Sử dụng Google Gemini API
        if active_provider == "google":
            model = genai.GenerativeModel(model_name)
            
            # Thiết lập generation_config
            generation_config = {
                "temperature": temperature,
                "top_p": 0.95,
                "top_k": 64
            }
            
            response = model.generate_content(prompt, generation_config=generation_config)
            ai_response = response.text
            
        # Sử dụng OpenAI API
        elif active_provider == "openai":
            response = openai.ChatCompletion.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            ai_response = response.choices[0].message.content.strip() if response.choices else ""

        # Sử dụng Ollama API
        elif active_provider == "ollama":
            data = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }

            response = requests.post("http://localhost:11434/api/generate", json=data)
            if response.status_code == 200:
                ai_response = response.json().get("response", "")
            else:
                print(f"Lỗi khi gọi Ollama API: {response.status_code} - {response.text}")
                return None

        # Xử lý kết quả
        if not ai_response:
            print("AI không trả về kết quả")
            return None

        # Tạo kết quả phân tích
        ai_analysis = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error_type": error_type,
            "ai_analysis": ai_response,
            "project_info": project_info,
            "provider": active_provider,
            "model": model_name
        }

        # Lưu kết quả phân tích
        save_ai_analysis_result(ai_analysis)

        return ai_analysis

    except Exception as e:
        print(f"Lỗi khi phân tích với AI ({active_provider}/{model_name}): {str(e)}")
        
        # Nếu một provider gặp lỗi và đang dùng auto, thử provider còn lại
        if provider == "auto" and active_provider in ["google", "openai", "ollama"]:
            providers = ["google", "openai", "ollama"]
            providers.remove(active_provider)
            
            for next_provider in providers:
                print(f"Đang thử lại với {next_provider}...")
                result = analyze_pipeline_error_with_ai(
                    pipeline_logs, project_info, temperature, next_provider
                )
                if result:
                    return result
            
        return None

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

def list_available_ai_providers() -> List[str]:
    """
    Liệt kê các nhà cung cấp AI có sẵn trên hệ thống.
    
    Returns:
        List[str]: Danh sách các nhà cung cấp AI khả dụng
    """
    providers = []
    
    # Kiểm tra Google Gemini API
    if GENAI_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
        try:
            # Lấy tên model từ biến môi trường
            gemini_model = os.getenv("DEFAULT_GEMINI_MODEL")
            print(f"Kiểm tra kết nối Gemini API với model: {gemini_model}")

            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model = genai.GenerativeModel(gemini_model)

            # Thử gọi API với timeout ngắn để tránh treo
            response = model.generate_content("Test", generation_config={"max_output_tokens": 10})

            if response.text:
                providers.append("google")
                print("✓ Gemini API khả dụng")
            else:
                print("✗ Gemini API trả về phản hồi trống")
        except Exception as e:
            print(f"✗ Không thể kết nối Gemini API: {str(e)}")
    elif not GENAI_AVAILABLE:
        print("✗ Module google.generativeai không có sẵn. Hãy cài đặt: pip install google-generativeai")
    elif not os.getenv("GOOGLE_API_KEY"):
        print("✗ Không tìm thấy GOOGLE_API_KEY trong biến môi trường")

    # Kiểm tra OpenAI API
    if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
        try:
            # Lấy tên model từ biến môi trường
            openai_model = os.getenv("DEFAULT_OPENAI_MODEL")
            print(f"Kiểm tra kết nối OpenAI API với model: {openai_model}")

            openai.api_key = os.getenv("OPENAI_API_KEY")
            response = openai.ChatCompletion.create(
                model=openai_model,
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.1
            )

            if response.choices and len(response.choices) > 0:
                providers.append("openai")
                print("✓ OpenAI API khả dụng")
            else:
                print("✗ OpenAI API trả về phản hồi không hợp lệ")
        except Exception as e:
            print(f"✗ Không thể kết nối OpenAI API: {str(e)}")
    elif not OPENAI_AVAILABLE:
        print("✗ Module openai không có sẵn. Hãy cài đặt: pip install openai")
    elif not os.getenv("OPENAI_API_KEY"):
        print("✗ Không tìm thấy OPENAI_API_KEY trong biến môi trường")

    # Kiểm tra Ollama
    if OLLAMA_AVAILABLE:
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=1)
            if response.status_code == 200:
                providers.append("ollama")
                print("✓ Ollama khả dụng")
            else:
                print(f"✗ Ollama trả về mã lỗi: {response.status_code}")
        except Exception as e:
            print(f"✗ Không thể kết nối Ollama: {str(e)}")
    elif not REQUESTS_AVAILABLE:
        print("✗ Module requests không có sẵn. Hãy cài đặt: pip install requests")
    else:
        print("✗ Ollama không chạy hoặc không thể kết nối")

    return providers

def list_ollama_models() -> List[str]:
    """
    Liệt kê các model có sẵn trong Ollama.

    Returns:
        List[str]: Danh sách các model
    """
    models = []

    if OLLAMA_AVAILABLE:
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200 and response.json().get("models"):
                for model in response.json().get("models", []):
                    models.append(model.get("name"))
        except:
            pass

    return models

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

# Demo sử dụng
if __name__ == "__main__":
    print("\n===== PHÂN TÍCH LỖI PIPELINE VỚI AI =====")
    
    # Liệt kê các provider có sẵn
    providers = list_available_ai_providers()
    if not providers:
        print("Không tìm thấy AI provider nào khả dụng!")
        print("Vui lòng cài đặt và cấu hình một trong các provider sau:")
        print("1. Google Gemini API")
        print("2. OpenAI API")
        print("3. Ollama")
        print("Chi tiết cài đặt vui lòng xem README hoặc mã nguồn.")
        exit(1)
    
    print(f"Các AI provider khả dụng: {', '.join(providers)}")
    
    # Hiển thị menu chọn provider
    print("\nChọn AI provider để phân tích:")
    for i, provider in enumerate(providers, 1):
        print(f"{i}. {provider.title()}")
    print(f"{len(providers) + 1}. Auto (tự động chọn)")
    
    choice = input("\nNhập lựa chọn của bạn: ")
    
    # Xác định provider được chọn
    selected_provider = "auto"
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(providers):
            selected_provider = providers[idx]
        elif idx == len(providers):
            selected_provider = "auto"
    except:
        pass

    # Nếu chọn Ollama, hiển thị danh sách các model
    model_name = None
    if selected_provider == "ollama":
        ollama_models = list_ollama_models()
        if ollama_models:
            print(f"\nCác model Ollama có sẵn: {', '.join(ollama_models)}")
            print("Chọn model để sử dụng:")
            for i, model in enumerate(ollama_models, 1):
                print(f"{i}. {model}")

            model_choice = input("\nNhập lựa chọn của bạn (Enter để dùng mặc định): ")
            try:
                model_idx = int(model_choice) - 1
                if 0 <= model_idx < len(ollama_models):
                    model_name = ollama_models[model_idx]
            except:
                pass

    # Hiển thị menu chọn loại lỗi
    print("\nChọn loại lỗi pipeline để phân tích:")
    print("1. Build Error - Lỗi biên dịch")
    print("2. Test Failure - Lỗi kiểm thử")
    print("3. Config Error - Lỗi cấu hình")
    print("4. Dependency Error - Lỗi phụ thuộc")
    print("5. Deployment Error - Lỗi triển khai")
    print("6. Database Error - Lỗi cơ sở dữ liệu")
    print("7. Complex Error - Lỗi phức tạp")
    
    error_choice = input("\nNhập lựa chọn của bạn (1-7): ")
    
    error_types = ["build_error", "test_failure", "config_error", 
                  "dependency_error", "deployment_error", "database_error", "complex_error"]
    
    if error_choice.isdigit() and 1 <= int(error_choice) <= len(error_types):
        selected_error = error_types[int(error_choice)-1]
        print(f"\nĐang phân tích lỗi: {selected_error} với {selected_provider}{' - ' + model_name if model_name else ''}")
        
        result = analyze_mockup_pipeline_with_ai(
            selected_error,
            provider=selected_provider,
            model_name=model_name
        )
        
        if result:
            formatted = format_ai_analysis_for_display(result)
            print(formatted)
        else:
            print("Không thể phân tích lỗi pipeline. Vui lòng kiểm tra cấu hình AI model.")
    else:
        print("Lựa chọn không hợp lệ!")
