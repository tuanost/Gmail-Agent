"""
Module quản lý các kết nối với các mô hình AI.
Hỗ trợ Google Gemini API, OpenAI API và Ollama.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tải biến môi trường
from dotenv import load_dotenv

# Đảm bảo load dotenv từ đường dẫn chính xác và ghi đè biến môi trường
env_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_file = os.path.join(env_path, '.env')
load_dotenv(dotenv_path=env_file, override=True)

# Kiểm tra các API key quan trọng
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    logger.info(f"Loaded Google API Key: {GOOGLE_API_KEY[:4]}...{GOOGLE_API_KEY[-4:]}")
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY  # Đảm bảo có sẵn cho các module khác
else:
    logger.warning("GOOGLE_API_KEY not found in environment")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    logger.info(f"Loaded OpenAI API Key: {OPENAI_API_KEY[:4]}...{OPENAI_API_KEY[-4:]}")
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY  # Đảm bảo có sẵn cho các module khác
else:
    logger.warning("OPENAI_API_KEY not found in environment")

# Thiết lập proxy dựa trên biến môi trường
proxy_enabled = os.getenv("GMAIL_PROXY_ENABLED", "False").lower() == "true"
http_proxy = os.getenv("PROXY_HTTP", "")
if proxy_enabled and http_proxy:
    # Sử dụng HTTP proxy cho tất cả kết nối (kể cả HTTPS)
    logger.info(f"Proxy enabled: {http_proxy}")

    # Thiết lập proxy cho tất cả kết nối HTTP
    os.environ["HTTP_PROXY"] = http_proxy
    os.environ["HTTPS_PROXY"] = http_proxy
    os.environ["http_proxy"] = http_proxy
    os.environ["https_proxy"] = http_proxy

# Thử import các module AI cần thiết
try:
    import google.generativeai as genai
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

def setup_ai_model(provider: str = "auto") -> Tuple[bool, str]:
    """
    Thiết lập và cấu hình AI model với cách tiếp cận đơn giản và trực tiếp.

    Args:
        provider: Nhà cung cấp AI ("google", "openai", "ollama", hoặc "auto" để tự động chọn)

    Returns:
        Tuple[bool, str]: (Thành công hay không, Tên provider đang sử dụng)
    """
    # Đảm bảo API keys đã được thiết lập
    google_api_key = os.getenv("GOOGLE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # Kiểm tra cấu hình proxy
    proxy_enabled = os.getenv("GMAIL_PROXY_ENABLED", "False").lower() == "true"
    http_proxy = os.getenv("PROXY_HTTP", "")

    # Thiết lập biến môi trường proxy nếu proxy được bật
    if proxy_enabled and http_proxy:
        # QUAN TRỌNG: Sử dụng proxy HTTP cho cả HTTP và HTTPS
        os.environ["HTTP_PROXY"] = http_proxy
        os.environ["HTTPS_PROXY"] = http_proxy
        os.environ["http_proxy"] = http_proxy
        os.environ["https_proxy"] = http_proxy
        logger.info(f"Đang sử dụng proxy cho kết nối API: {http_proxy}")

    # Xử lý theo provider được chỉ định hoặc tự động chọn
    if provider == "auto" or provider == "gemini":
        # Thử sử dụng Gemini
        if GENAI_AVAILABLE and google_api_key:
            try:
                # Cấu hình trực tiếp
                genai.configure(api_key=google_api_key)
                gemini_model_name = os.getenv("DEFAULT_GEMINI_MODEL", "models/gemini-pro-latest")
                model = genai.GenerativeModel(gemini_model_name)

                # Kiểm tra kết nối với một prompt đơn giản
                response = model.generate_content("Hello")
                if response.text:
                    logger.info(f"Đã thiết lập Google Gemini API thành công với mô hình {gemini_model_name}.")
                    return True, "google"
            except Exception as e:
                logger.error(f"Lỗi kết nối Gemini API: {str(e)}")
                if provider == "gemini":
                    return False, ""
                logger.info("Đang thử với OpenAI API...")

    if provider == "auto" or provider == "openai":
        # Thử sử dụng OpenAI
        if OPENAI_AVAILABLE and openai_api_key:
            try:
                # Kiểm tra phiên bản OpenAI API
                is_v1_api = False
                try:
                    from openai import OpenAI
                    is_v1_api = True
                except ImportError:
                    pass

                openai_model = os.getenv("DEFAULT_OPENAI_MODEL", "gpt-3.5-turbo")

                if is_v1_api:
                    # Sử dụng API v1.0+
                    client = OpenAI(api_key=openai_api_key)

                    # Thiết lập proxy nếu cần
                    if proxy_enabled and http_proxy:
                        import httpx
                        client = OpenAI(
                            api_key=openai_api_key,
                            http_client=httpx.Client(proxies={"http://": http_proxy, "https://": http_proxy})
                        )

                    response = client.chat.completions.create(
                        model=openai_model,
                        messages=[{"role": "user", "content": "Hello"}],
                        max_tokens=10
                    )
                    if response.choices[0].message.content:
                        logger.info(f"Đã thiết lập OpenAI API v1.0+ thành công với mô hình {openai_model}.")
                        return True, "openai"
                else:
                    # Sử dụng API phiên bản cũ
                    openai.api_key = openai_api_key

                    # Thiết lập proxy nếu cần
                    if proxy_enabled and http_proxy:
                        openai.proxy = http_proxy

                    response = openai.ChatCompletion.create(
                        model=openai_model,
                        messages=[{"role": "user", "content": "Hello"}],
                        max_tokens=10
                    )
                    if response.choices[0].message.content:
                        logger.info(f"Đã thiết lập OpenAI API thành công (phiên bản cũ) với mô hình {openai_model}.")
                        return True, "openai"
            except Exception as e:
                logger.error(f"Lỗi kết nối OpenAI API: {str(e)}")
                if provider == "openai":
                    return False, ""
                logger.info("Đang thử với Ollama...")

    if provider == "auto" or provider == "ollama":
        # Thử sử dụng Ollama
        if OLLAMA_AVAILABLE and REQUESTS_AVAILABLE:
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200 and response.json().get("models"):
                    logger.info("Đã thiết lập kết nối Ollama thành công.")
                    return True, "ollama"
            except Exception as e:
                logger.error(f"Lỗi kết nối Ollama: {str(e)}")
                return False, ""

    # Nếu không có provider nào thành công
    logger.error("\nKhông thể thiết lập bất kỳ AI model nào.")
    logger.error("Vui lòng thực hiện một trong các cách sau:")
    logger.error("\n1. Sử dụng Google Gemini API:")
    logger.error("   - pip install google-generativeai python-dotenv")
    logger.error("   - Tạo file .env với nội dung: GOOGLE_API_KEY=your_api_key")

    logger.error("\n2. Sử dụng OpenAI API:")
    logger.error("   - pip install openai python-dotenv")
    logger.error("   - Tạo file .env với nội dung: OPENAI_API_KEY=your_api_key")

    logger.error("\n3. Sử dụng Ollama (miễn phí, chạy local):")
    logger.error("   - Cài đặt Ollama từ: https://ollama.com/")
    logger.error("   - Chạy lệnh: ollama pull codellama")

    return False, ""

def generate_ai_response(prompt: str,
                        provider: str = "auto",
                        model_name: str = None,
                        temperature: float = 0.2) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Tạo phản hồi từ mô hình AI cho prompt đã cho.

    Args:
        prompt: Nội dung prompt cần gửi tới AI
        provider: Nhà cung cấp AI ("google", "openai", "ollama", hoặc "auto")
        model_name: Tên model cụ thể (nếu không chọn sẽ dùng mặc định của provider)
        temperature: Độ sáng tạo của AI (0.0-1.0, thấp hơn = chính xác hơn)

    Returns:
        Tuple[bool, str, Dict]: (Thành công hay không, Nội dung phản hồi, Thông tin chi tiết)
    """
    # Thiết lập AI model
    success, active_provider = setup_ai_model(provider)
    if not success:
        return False, "Không thể thiết lập AI model", {"error": True}

    # Chọn model mặc định nếu không được chỉ định
    if not model_name:
        if active_provider == "google":
            model_name = os.getenv("DEFAULT_GEMINI_MODEL", "models/gemini-pro-latest")
        elif active_provider == "openai":
            model_name = os.getenv("DEFAULT_OPENAI_MODEL", "gpt-3.5-turbo")
        elif active_provider == "ollama":
            model_name = "tinyllama"  # Model mặc định của Ollama

    logger.info(f"Đang sử dụng AI model: {active_provider}/{model_name}")
    result_info = {
        "provider": active_provider,
        "model": model_name,
        "success": False
    }

    try:
        ai_response = None
        # Kiểm tra cấu hình proxy
        proxy_enabled = os.getenv("GMAIL_PROXY_ENABLED", "False").lower() == "true"
        http_proxy = os.getenv("PROXY_HTTP", "")

        # Sử dụng Google Gemini API
        if active_provider == "google":
            # Thiết lập trực tiếp
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model = genai.GenerativeModel(model_name)

            # Thiết lập cấu hình generation
            generation_config = {
                "temperature": temperature,
                "top_p": 0.95,
                "top_k": 64
            }

            # Gọi API trực tiếp
            response = model.generate_content(prompt, generation_config=generation_config)
            ai_response = response.text

        # Sử dụng OpenAI API
        elif active_provider == "openai":
            # Kiểm tra phiên bản API
            try:
                # Thử với API mới (v1.0+)
                from openai import OpenAI

                # Khởi tạo client
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                # Thiết lập proxy nếu cần
                if proxy_enabled and http_proxy:
                    import httpx
                    client = OpenAI(
                        api_key=os.getenv("OPENAI_API_KEY"),
                        http_client=httpx.Client(proxies={"http://": http_proxy, "https://": http_proxy})
                    )

                # Gọi API
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature
                )
                ai_response = response.choices[0].message.content
            except (ImportError, AttributeError):
                # Dùng API phiên bản cũ
                openai.api_key = os.getenv("OPENAI_API_KEY")

                # Thiết lập proxy nếu cần
                if proxy_enabled and http_proxy:
                    openai.proxy = http_proxy

                # Gọi API
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

            # Gọi API trực tiếp
            response = requests.post("http://localhost:11434/api/generate", json=data)
            if response.status_code == 200:
                ai_response = response.json().get("response", "")
            else:
                logger.error(f"Lỗi khi gọi Ollama API: {response.status_code} - {response.text}")
                return False, "", result_info

        # Xử lý kết quả
        if not ai_response:
            logger.error("AI không trả về kết quả")
            return False, "", result_info

        result_info["success"] = True
        return True, ai_response, result_info

    except Exception as e:
        logger.error(f"Lỗi khi gọi AI API ({active_provider}/{model_name}): {str(e)}")
        return False, str(e), result_info

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
            # Cấu hình và kiểm tra
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            gemini_model = os.getenv("DEFAULT_GEMINI_MODEL", "models/gemini-pro-latest")
            logger.info(f"Kiểm tra kết nối Gemini API với model: {gemini_model}")

            # Thử gọi API với timeout ngắn
            model = genai.GenerativeModel(gemini_model)
            response = model.generate_content("Test", generation_config={"max_output_tokens": 10})

            if response.text:
                providers.append("google")
                logger.info("✓ Gemini API khả dụng")
            else:
                logger.warning("✗ Gemini API trả về phản hồi trống")
        except Exception as e:
            logger.error(f"✗ Không thể kết nối Gemini API: {str(e)}")
    elif not GENAI_AVAILABLE:
        logger.warning("✗ Module google.generativeai không có sẵn. Hãy cài đặt: pip install google-generativeai")
    elif not os.getenv("GOOGLE_API_KEY"):
        logger.warning("✗ Không tìm thấy GOOGLE_API_KEY trong biến môi trường")

    # Kiểm tra OpenAI API
    if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
        try:
            # Lấy tên model từ biến môi trường
            openai_model = os.getenv("DEFAULT_OPENAI_MODEL", "gpt-3.5-turbo")
            logger.info(f"Kiểm tra kết nối OpenAI API với model: {openai_model}")

            # Thiết lập và kiểm tra
            openai.api_key = os.getenv("OPENAI_API_KEY")
            response = openai.ChatCompletion.create(
                model=openai_model,
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.1,
                max_tokens=10
            )

            if response.choices and len(response.choices) > 0:
                providers.append("openai")
                logger.info("✓ OpenAI API khả dụng")
            else:
                logger.warning("✗ OpenAI API trả về phản hồi không hợp lệ")
        except Exception as e:
            logger.error(f"✗ Không thể kết nối OpenAI API: {str(e)}")
    elif not OPENAI_AVAILABLE:
        logger.warning("✗ Module openai không có sẵn. Hãy cài đặt: pip install openai")
    elif not os.getenv("OPENAI_API_KEY"):
        logger.warning("✗ Không tìm thấy OPENAI_API_KEY trong biến môi trường")

    # Kiểm tra Ollama
    if OLLAMA_AVAILABLE:
        try:
            # Kiểm tra kết nối
            response = requests.get("http://localhost:11434/api/tags", timeout=1)
            if response.status_code == 200:
                providers.append("ollama")
                logger.info("✓ Ollama khả dụng")
            else:
                logger.warning(f"✗ Ollama trả về mã lỗi: {response.status_code}")
        except Exception as e:
            logger.error(f"✗ Không thể kết nối Ollama: {str(e)}")
    elif not REQUESTS_AVAILABLE:
        logger.warning("✗ Module requests không có sẵn. Hãy cài đặt: pip install requests")
    else:
        logger.warning("✗ Ollama không chạy hoặc không thể kết nối")

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
