"""
Module xác thực và kết nối đến Gitlab API.
Module này cung cấp các chức năng xác thực và tạo kết nối đến Gitlab API.
"""
import os
import requests
from dotenv import load_dotenv
import logging
from urllib.parse import urlparse
import json
import re
import urllib.parse

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tải biến môi trường
load_dotenv()

def get_gitlab_auth_headers():
    """
    Lấy headers xác thực cho Gitlab API.

    Returns:
        Dict: Headers chứa token xác thực hoặc None nếu không có token
    """
    # Lấy token từ biến môi trường
    gitlab_token = os.getenv('GITLAB_API_TOKEN')

    if not gitlab_token:
        logger.warning("Không tìm thấy GITLAB_API_TOKEN trong biến môi trường.")
        return None

    return {
        'PRIVATE-TOKEN': gitlab_token
    }

def get_gitlab_service():
    """
    Kiểm tra kết nối đến Gitlab API và trả về thông tin cơ bản.

    Returns:
        Dict: Thông tin về kết nối Gitlab hoặc lỗi
    """
    # Lấy thông tin Gitlab URL từ môi trường
    gitlab_url = os.getenv('GITLAB_API_URL')

    if not gitlab_url:
        logger.warning("Không tìm thấy GITLAB_API_URL trong biến môi trường.")
        return {
            'success': False,
            'error': "GITLAB_API_URL không được cấu hình",
            'message': "Thiết lập GITLAB_API_URL trong file .env"
        }

    # Lấy headers xác thực
    headers = get_gitlab_auth_headers()

    if not headers:
        return {
            'success': False,
            'error': "Không có token xác thực Gitlab",
            'message': "Thiết lập GITLAB_API_TOKEN trong file .env"
        }

    try:
        # Gọi API kiểm tra kết nối
        response = requests.get(f"{gitlab_url}/version", headers=headers, timeout=10)

        if response.status_code == 200:
            # Kết nối thành công
            version_info = response.json()
            logger.info(f"Kết nối thành công đến Gitlab API: {version_info.get('version', 'Unknown version')}")
            return {
                'success': True,
                'version': version_info,
                'message': "Kết nối Gitlab thành công"
            }
        elif response.status_code == 401:
            # Lỗi xác thực
            logger.error("Lỗi xác thực Gitlab API: Token không hợp lệ")
            return {
                'success': False,
                'error': "Token không hợp lệ hoặc đã hết hạn",
                'status_code': response.status_code
            }
        else:
            # Lỗi khác
            logger.error(f"Lỗi kết nối Gitlab API: Mã trạng thái {response.status_code}")
            return {
                'success': False,
                'error': f"Không thể kết nối đến Gitlab API. Mã trạng thái: {response.status_code}",
                'status_code': response.status_code
            }
    except requests.exceptions.Timeout:
        logger.error("Kết nối đến Gitlab API bị timeout")
        return {
            'success': False,
            'error': "Kết nối đến Gitlab API bị timeout"
        }
    except requests.exceptions.ConnectionError:
        logger.error("Không thể kết nối đến Gitlab API")
        return {
            'success': False,
            'error': "Không thể kết nối đến Gitlab API"
        }
    except Exception as e:
        logger.exception(f"Lỗi không xác định khi kết nối Gitlab API: {str(e)}")
        return {
            'success': False,
            'error': f"Lỗi không xác định: {str(e)}"
        }

def get_pipeline_details(pipeline_id, project_id=None, pipeline_url=None):
    """
    Lấy thông tin chi tiết về một pipeline từ Gitlab API.

    Args:
        pipeline_id: ID của pipeline
        project_id: ID của project (nếu biết)
        pipeline_url: URL của pipeline (dùng để trích xuất project_id nếu không có)

    Returns:
        Dict: Thông tin về pipeline hoặc lỗi
    """
    # Nếu không có project_id, thử trích xuất từ URL
    if not project_id and pipeline_url:
        # Phân tích URL để lấy project_id
        try:
            url_parts = pipeline_url.split('/')
            # URL format: https://gitlab-domain.com/path/to/project/-/pipelines/123
            # Tìm vị trí của '-/pipelines'
            for i, part in enumerate(url_parts):
                if part == '-' and i+1 < len(url_parts) and url_parts[i+1] == 'pipelines':
                    # Ghép các phần trước đó để tạo đường dẫn project
                    project_path = '/'.join(url_parts[url_parts.index('/-/pipelines')-1])
                    break
        except Exception as e:
            logger.error(f"Không thể trích xuất project_id từ URL: {str(e)}")
            return {
                'success': False,
                'error': "Không thể xác định project_id từ URL",
                'message': "Vui lòng cung cấp project_id"
            }

    # Nếu vẫn không có project_id, trả về lỗi
    if not project_id:
        return {
            'success': False,
            'error': "Không có project_id",
            'message': "Vui lòng cung cấp project_id"
        }

    # Lấy thông tin Gitlab API từ môi trường
    gitlab_url = os.getenv('GITLAB_API_URL')
    headers = get_gitlab_auth_headers()

    if not gitlab_url or not headers:
        return {
            'success': False,
            'error': "Thiếu cấu hình Gitlab API",
            'message': "Thiết lập GITLAB_API_URL và GITLAB_API_TOKEN trong file .env"
        }

    try:
        # Gọi API lấy thông tin pipeline
        api_url = f"{gitlab_url}/projects/{project_id}/pipelines/{pipeline_id}"
        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 200:
            # Kết nối thành công
            pipeline_info = response.json()
            return {
                'success': True,
                'pipeline_info': pipeline_info
            }
        else:
            # Xử lý lỗi
            return {
                'success': False,
                'error': f"Không thể lấy thông tin pipeline. Mã trạng thái: {response.status_code}",
                'status_code': response.status_code
            }
    except Exception as e:
        logger.exception(f"Lỗi khi lấy thông tin pipeline: {str(e)}")
        return {
            'success': False,
            'error': f"Lỗi: {str(e)}"
        }

def check_pipeline_url_accessibility(url, timeout=5):
    """
    Kiểm tra xem URL của pipeline có thể truy cập được không.

    Args:
        url: URL cần kiểm tra
        timeout: Thời gian chờ tối đa (giây)

    Returns:
        Tuple (bool, str): (Có thể truy cập không, Thông báo)
    """
    if not url:
        return False, "Không tìm thấy URL pipeline trong email."

    try:
        # Phân tích URL để kiểm tra tính hợp lệ
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return False, f"URL pipeline không hợp lệ: {url}"

        # Thử truy cập URL
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        if response.status_code < 400:
            return True, f"URL pipeline có thể truy cập được: {url}"
        else:
            return False, f"URL pipeline không thể truy cập. Mã trạng thái: {response.status_code}"

    except requests.exceptions.Timeout:
        return False, f"Kết nối đến URL pipeline bị time out: {url}"

    except requests.exceptions.ConnectionError:
        return False, f"Không thể kết nối đến URL pipeline: {url}"

    except Exception as e:
        return False, f"Lỗi khi kiểm tra URL pipeline: {str(e)}"

def extract_job_id_from_url(job_url):
    """
    Trích xuất job ID từ URL của job.

    Args:
        job_url: URL của job Gitlab

    Returns:
        Tuple (project_id, job_id) hoặc (None, None) nếu không thể trích xuất
    """
    # Pattern URL Gitlab job: https://gitlab-domain.com/group/project/-/jobs/123456

    # Tìm project path và job ID từ URL
    match = re.search(r'https?://[^/]+/(.+?)/-/jobs/(\d+)', job_url)
    if not match:
        logger.warning(f"Không thể trích xuất job ID từ URL: {job_url}")
        return None, None

    project_path = match.group(1)
    job_id = match.group(2)

    # Mã hóa project path cho API
    encoded_project_path = urllib.parse.quote_plus(project_path)

    return encoded_project_path, job_id

def get_job_log(job_url):
    """
    Lấy log của job từ Gitlab API.

    Args:
        job_url: URL của job cần lấy log

    Returns:
        Dict: Thông tin về job và log hoặc lỗi
    """
    # Lấy gitlab API URL và headers
    gitlab_url = os.getenv('GITLAB_API_URL')
    headers = get_gitlab_auth_headers()

    if not gitlab_url or not headers:
        logger.error("Thiếu cấu hình Gitlab API URL hoặc token")
        return {
            'success': False,
            'error': "Thiếu cấu hình Gitlab API"
        }

    # Trích xuất project ID và job ID từ URL
    project_path, job_id = extract_job_id_from_url(job_url)
    if not project_path or not job_id:
        return {
            'success': False,
            'error': f"Không thể trích xuất thông tin từ job URL: {job_url}"
        }

    try:
        # Lấy thông tin chi tiết về job
        job_url = f"{gitlab_url}/projects/{project_path}/jobs/{job_id}"
        response = requests.get(job_url, headers=headers, timeout=15)

        if response.status_code != 200:
            logger.error(f"Lỗi khi lấy thông tin job: HTTP {response.status_code}")
            return {
                'success': False,
                'error': f"Không thể lấy thông tin job. HTTP {response.status_code}"
            }

        job_info = response.json()

        # Lấy trace log của job
        trace_url = f"{gitlab_url}/projects/{project_path}/jobs/{job_id}/trace"
        trace_response = requests.get(trace_url, headers=headers, timeout=15)

        if trace_response.status_code != 200:
            logger.error(f"Lỗi khi lấy log job: HTTP {trace_response.status_code}")
            return {
                'success': False,
                'job_info': job_info,
                'error': f"Không thể lấy log job. HTTP {trace_response.status_code}"
            }

        # Trả về thông tin job và log
        return {
            'success': True,
            'job_info': job_info,
            'job_log': trace_response.text,
            'job_status': job_info.get('status', 'unknown')
        }

    except Exception as e:
        logger.exception(f"Lỗi khi truy cập Gitlab API: {str(e)}")
        return {
            'success': False,
            'error': f"Lỗi khi truy cập Gitlab API: {str(e)}"
        }

def find_and_get_failed_job_log(job_urls):
    """
    Tìm và lấy log của job thất bại đầu tiên từ danh sách job URLs.

    Args:
        job_urls: Danh sách các URL job

    Returns:
        Dict: Log và thông tin của job thất bại đầu tiên hoặc lỗi
    """
    if not job_urls:
        return {
            'success': False,
            'error': "Không có job URL nào được cung cấp"
        }

    # Kiểm tra từng job URL
    for job_url in job_urls:
        result = get_job_log(job_url)

        # Nếu lấy thông tin job thành công
        if result.get('success'):
            # Kiểm tra xem job có thất bại không (failed hoặc error)
            status = result.get('job_status', '').lower()
            if status in ['failed', 'error', 'canceled']:
                logger.info(f"Đã tìm thấy job thất bại: {job_url} (status: {status})")
                return result

    # Nếu không tìm thấy job thất bại, trả về job đầu tiên
    logger.info("Không tìm thấy job thất bại, lấy job đầu tiên")
    return get_job_log(job_urls[0])
