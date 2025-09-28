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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL")

# Thiết lập proxy dựa trên biến môi trường
proxy_enabled = os.getenv("GMAIL_PROXY_ENABLED", "False").lower() == "true"
http_proxy = os.getenv("PROXY_HTTP", "")
if proxy_enabled and http_proxy:
    # Sử dụng HTTP proxy cho tất cả kết nối (kể cả HTTPS)
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
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1)
        if response.status_code == 200:
            OLLAMA_AVAILABLE = True
    except:
        OLLAMA_AVAILABLE = False
except ImportError:
    REQUESTS_AVAILABLE = False

# Biến lưu trạng thái kết nối AI model
_ai_connection_state = {
    "provider": None,
    "connected": False
}

def setup_ai_model(provider: str = "auto") -> Tuple[bool, str]:
    """
    Thiết lập và cấu hình AI model với cách tiếp cận đơn giản và trực tiếp.

    Args:
        provider: Nhà cung cấp AI ("google", "openai", "ollama", hoặc "auto" để tự động chọn)

    Returns:
        Tuple[bool, str]: (Thành công hay không, Tên provider đang sử dụng)
    """
    global _ai_connection_state
    google_api_key = os.getenv("GOOGLE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    proxy_enabled = os.getenv("GMAIL_PROXY_ENABLED", "False").lower() == "true"
    http_proxy = os.getenv("PROXY_HTTP", "")
    if proxy_enabled and http_proxy:
        os.environ["HTTP_PROXY"] = http_proxy
        os.environ["HTTPS_PROXY"] = http_proxy
        os.environ["http_proxy"] = http_proxy
        os.environ["https_proxy"] = http_proxy
    # Chỉ kết nối đúng provider
    if provider == "google":
        if GENAI_AVAILABLE and google_api_key:
            try:
                genai.configure(api_key=google_api_key)
                model_name = os.getenv("DEFAULT_GEMINI_MODEL", "models/gemini-pro-latest")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Hello")
                if response.text:
                    _ai_connection_state["provider"] = provider
                    _ai_connection_state["connected"] = True
                    return True, provider
            except Exception as e:
                logger.error(f"Lỗi kết nối Gemini API: {str(e)}")
        _ai_connection_state["connected"] = False
        return False, ""
    elif provider == "openai":
        if OPENAI_AVAILABLE and openai_api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_api_key)
                if proxy_enabled and http_proxy:
                    import httpx
                    client = OpenAI(
                        api_key=openai_api_key,
                        http_client=httpx.Client(proxies={"http://": http_proxy, "https://": http_proxy})
                    )
                model_name = os.getenv("DEFAULT_OPENAI_MODEL", "gpt-3.5-turbo")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=10
                )
                if response.choices[0].message.content:
                    _ai_connection_state["provider"] = provider
                    _ai_connection_state["connected"] = True
                    return True, provider
            except Exception as e:
                logger.error(f"Lỗi kết nối OpenAI API: {str(e)}")
        _ai_connection_state["connected"] = False
        return False, ""
    elif provider == "ollama":
        if OLLAMA_AVAILABLE and REQUESTS_AVAILABLE:
            try:
                if not OLLAMA_URL:
                    logger.error("Biến môi trường OLLAMA_URL chưa được thiết lập. Vui lòng thêm vào .env hoặc môi trường hệ thống.")
                    return False, ""
                response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
                if response.status_code == 200 and response.json().get("models"):
                    _ai_connection_state["provider"] = provider
                    _ai_connection_state["connected"] = True
                    return True, provider
            except Exception as e:
                logger.error(f"Lỗi kết nối Ollama: {str(e)}")
        _ai_connection_state["connected"] = False
        return False, ""
    elif provider == "auto":
        # Tự động chọn provider khả dụng
        for auto_provider in ["google", "openai", "ollama"]:
            success, prov = setup_ai_model(auto_provider)
            if success:
                return True, prov
        _ai_connection_state["connected"] = False
        return False, ""
    else:
        logger.error(f"Provider không hợp lệ: {provider}")
        _ai_connection_state["connected"] = False
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
    # Chỉ gọi setup_ai_model nếu chưa kết nối hoặc provider thay đổi
    global _ai_connection_state
    if not _ai_connection_state["connected"] or _ai_connection_state["provider"] != provider:
        success, active_provider = setup_ai_model(provider)
        if not success:
            return False, "Không thể thiết lập AI model", {"error": True}
    else:
        active_provider = _ai_connection_state["provider"]

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
            except Exception as e:
                logger.error(f"Lỗi khi gọi API openai: {str(e)}")
                return False, str(e), result_info

        # Sử dụng Ollama API
        elif active_provider == "ollama":
            # Truyền nguyên tên model (bao gồm cả phần sau dấu hai chấm) cho Ollama
            data = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }

            # Gọi API trực tiếp
            response = requests.post(f"{OLLAMA_URL}/api/generate", json=data, timeout=60)
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

def list_ollama_models() -> List[str]:
    """
    Liệt kê các model có sẵn trong Ollama.

    Returns:
        List[str]: Danh sách các model
    """
    models = []

    if OLLAMA_AVAILABLE:
        try:
            response = requests.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200 and response.json().get("models"):
                for model in response.json().get("models", []):
                    models.append(model.get("name"))
        except:
            pass

    return models

def discover_available_models(provider: str) -> List[str]:
    """
    Khám phá các model có sẵn từ nhà cung cấp AI sử dụng API chính thức.

    Args:
        provider: Nhà cung cấp AI ("google", "openai", "ollama")
        
    Returns:
        List[str]: Danh sách các model có thể sử dụng, hoặc danh sách trống nếu không tìm thấy
    """
    available_models = []
    
    # Google Gemini
    if provider == "google":
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            
            # Sử dụng API của Google để lấy danh sách models
            try:
                # Gọi API để lấy danh sách model
                models = genai.list_models()
                gemini_models = []

                # Lọc các model Gemini khả dụng
                for model in models:
                    if "gemini" in model.name.lower():
                        model_name = model.name.split("/")[-1]
                        # Chỉ thêm model có hỗ trợ text generation
                        if "generateContent" in model.supported_generation_methods:
                            gemini_models.append(model_name)

                available_models = gemini_models
            except Exception as e:
                logger.warning(f"Không thể lấy danh sách model từ Gemini API: {str(e)}")

        except Exception as e:
            logger.error(f"Lỗi khi khám phá model Gemini: {str(e)}")
    
    # OpenAI
    elif provider == "openai":
        try:
            # Thử với API mới (v1+)
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                # Thiết lập proxy nếu cần
                proxy_enabled = os.getenv("GMAIL_PROXY_ENABLED", "False").lower() == "true"
                http_proxy = os.getenv("PROXY_HTTP", "")
                if proxy_enabled and http_proxy:
                    import httpx
                    client = OpenAI(
                        api_key=os.getenv("OPENAI_API_KEY"),
                        http_client=httpx.Client(proxies={"http://": http_proxy, "https://": http_proxy})
                    )

                # Lấy danh sách model từ API
                models_data = client.models.list()
                gpt_models = []

                for model in models_data.data:
                    model_id = model.id
                    # Chỉ lấy các model GPT cho chat completion
                    if any(name in model_id.lower() for name in ["gpt-4", "gpt-3.5"]):
                        gpt_models.append(model_id)
            except Exception as e:
                logger.warning(f"Không thể sử dụng OpenAI API mới: {str(e)}")
                # Thử với API cũ
                try:
                    import openai as openai_old
                    openai_old.api_key = os.getenv("OPENAI_API_KEY")
                    
                    # Thiết lập proxy nếu cần
                    proxy_enabled = os.getenv("GMAIL_PROXY_ENABLED", "False").lower() == "true"
                    http_proxy = os.getenv("PROXY_HTTP", "")
                    if proxy_enabled and http_proxy:
                        openai_old.proxy = http_proxy
                    
                    # Lấy danh sách model từ API
                    models = openai_old.Model.list()
                    gpt_models = []

                    if "data" in models:
                        for model in models["data"]:
                            model_id = model["id"]
                            # Chỉ lấy các model GPT cho chat completion
                            if any(name in model_id.lower() for name in ["gpt-4", "gpt-3.5"]):
                                gpt_models.append(model_id)
                except Exception as e:
                    logger.warning(f"Không thể lấy danh sách model từ OpenAI API: {str(e)}")

            available_models = gpt_models
        except Exception as e:
            logger.error(f"Lỗi khi khám phá model OpenAI: {str(e)}")

    # Ollama
    elif provider == "ollama":
        try:
            # Ollama đã có API trả về danh sách model
            if OLLAMA_AVAILABLE and REQUESTS_AVAILABLE:
                try:
                    response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)

                    if response.status_code == 200 and response.json().get("models"):
                        for model in response.json().get("models", []):
                            model_name = model.get("name")
                            if model_name:
                                available_models.append(model_name)
                except Exception as e:
                    logger.warning(f"Không thể kết nối đến Ollama API: {str(e)}")
            else:
                logger.warning("Ollama không khả dụng hoặc module requests không được cài đặt")

        except Exception as e:
            logger.error(f"Lỗi khi khám phá model Ollama: {str(e)}")

    # Sắp xếp danh sách các model để nhóm các model cùng loại
    if available_models:
        available_models = sorted(list(set(available_models)))

    # Khi danh sách trống, ghi log cảnh báo
    if not available_models:
        logger.warning(f"Không tìm thấy model nào khả dụng cho nhà cung cấp: {provider}")

    return available_models

def check_model_connectivity(provider: str, model_name: str) -> bool:
    """
    Kiểm tra kết nối đến một model AI cụ thể của provider.
    Returns True nếu kết nối thành công, False nếu không.
    """
    try:
        if provider == "google":
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Test", generation_config={"max_output_tokens": 5})
                return hasattr(response, 'text') and bool(response.text)
            except Exception as e:
                logger.warning(f"Không thể kết nối model Gemini: {model_name} - {str(e)}")
                return False
        elif provider == "openai":
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                proxy_enabled = os.getenv("GMAIL_PROXY_ENABLED", "False").lower() == "true"
                http_proxy = os.getenv("PROXY_HTTP", "")
                if proxy_enabled and http_proxy:
                    import httpx
                    client = OpenAI(
                        api_key=os.getenv("OPENAI_API_KEY"),
                        http_client=httpx.Client(proxies={"http://": http_proxy, "https://": http_proxy})
                    )
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": "Test"}],
                    max_tokens=5
                )
                return response and response.choices and bool(response.choices[0].message.content)
            except Exception as e:
                logger.warning(f"Không thể kết nối model OpenAI: {model_name} - {str(e)}")
                return False
        elif provider == "ollama":
            try:
                import requests
                data = {
                    "model": model_name,
                    "prompt": "Test",
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 5}
                }
                response = requests.post(f"{OLLAMA_URL}/api/generate", json=data, timeout=60)
                return response.status_code == 200 and response.json().get("response")
            except Exception as e:
                logger.warning(f"Không thể kết nối model Ollama: {model_name} - {str(e)}")
                return False
    except Exception as e:
        logger.error(f"Lỗi kiểm tra kết nối model {provider}/{model_name}: {str(e)}")
        return False
