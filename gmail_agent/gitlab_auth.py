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

def get_gitlab_proxy_info():
    """
    Lấy thông tin cấu hình proxy cho GitLab từ biến môi trường.

    Returns:
        dict: Thông tin cấu hình proxy hoặc một dict trống nếu không có cấu hình
    """
    proxy_enabled = os.getenv("GITLAB_PROXY_ENABLED", "False").lower() == "true"

    if not proxy_enabled:
        # Khi proxy bị tắt, trả về dict rỗng để requests biết là không dùng proxy
        # và xóa các biến môi trường proxy để đảm bảo không có proxy nào được sử dụng
        if "HTTP_PROXY" in os.environ:
            del os.environ["HTTP_PROXY"]
        if "HTTPS_PROXY" in os.environ:
            del os.environ["HTTPS_PROXY"]
        if "http_proxy" in os.environ:
            del os.environ["http_proxy"]
        if "https_proxy" in os.environ:
            del os.environ["https_proxy"]

        return {'http': None, 'https': None}

    # Thiết lập thông tin proxy
    proxies = {
        'http': os.getenv("GITLAB_PROXY_HTTP", ""),
        'https': os.getenv("GITLAB_PROXY_HTTPS", "")
    }

    return proxies

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

    # Lấy cấu hình proxy
    proxies = get_gitlab_proxy_info()
    if proxies:
        logger.info("Đang sử dụng proxy cho kết nối GitLab: %s", proxies['http'])

    try:
        # Gọi API kiểm tra kết nối với proxy nếu được cấu hình
        response = requests.get(
            f"{gitlab_url}/version",
            headers=headers,
            proxies=proxies,
            timeout=10
        )

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
    except requests.exceptions.RequestException as e:
        logger.error(f"Lỗi kết nối Gitlab API: {str(e)}")
        return {
            'success': False,
            'error': f"Lỗi kết nối: {str(e)}"
        }

def check_pipeline_url_accessibility(pipeline_url):
    """
    Kiểm tra khả năng truy cập URL pipeline.

    Args:
        pipeline_url (str): URL pipeline cần kiểm tra

    Returns:
        bool: True nếu URL có thể truy cập, False nếu không
    """
    try:
        # Lấy cấu hình proxy
        proxies = get_gitlab_proxy_info()

        # Gửi request kiểm tra với proxy nếu được cấu hình
        response = requests.head(
            pipeline_url,
            proxies=proxies,
            timeout=5,
            allow_redirects=True
        )

        # Kiểm tra trạng thái response
        return response.status_code < 400
    except Exception as e:
        logger.warning(f"Không thể truy cập pipeline URL {pipeline_url}: {str(e)}")
        return False

def find_and_get_failed_job_log(job_urls):
    """
    Tìm và lấy log từ các job pipeline thất bại trong GitLab.

    Args:
        job_urls (list): Danh sách các URL của các job cần kiểm tra

    Returns:
        dict: Kết quả truy vấn bao gồm log của job thất bại đầu tiên và thông tin job
    """
    import requests
    import os
    from urllib.parse import urlparse

    if not job_urls:
        logger.warning("Không có URL job nào để kiểm tra")
        return {'success': False, 'error': "Không có URL job nào để kiểm tra"}

    # Lấy thông tin proxy
    proxies = get_gitlab_proxy_info()

    # Lấy headers xác thực
    headers = get_gitlab_auth_headers()

    if not headers:
        return {'success': False, 'error': "Không có token xác thực GitLab API"}

    # Base URL của GitLab API
    gitlab_api_url = os.getenv('GITLAB_API_URL')

    if not gitlab_api_url:
        return {'success': False, 'error': "GITLAB_API_URL không được cấu hình"}

    # Vô hiệu hóa cảnh báo về SSL
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    for job_url in job_urls:
        try:
            # Phân tích URL để lấy project ID và job ID
            parsed_url = urlparse(job_url)
            path_parts = parsed_url.path.strip('/').split('/')

            if len(path_parts) < 4:
                logger.warning(f"URL job không hợp lệ: {job_url}")
                continue

            # Định dạng của URL job là: /<namespace>/<project>/-/jobs/<job_id>
            # hoặc /<group>/<namespace>/<project>/-/jobs/<job_id>
            job_id = path_parts[-1]  # ID job là phần tử cuối cùng

            # Tìm vị trí của '-/jobs' trong đường dẫn
            try:
                jobs_index = path_parts.index('-')
                if jobs_index > 0 and path_parts[jobs_index + 1] == 'jobs':
                    project_path = '/'.join(path_parts[:jobs_index])
                else:
                    logger.warning(f"URL job không đúng định dạng: {job_url}")
                    continue
            except ValueError:
                logger.warning(f"URL job không đúng định dạng: {job_url}")
                continue

            # URL encode project path
            project_path_encoded = urllib.parse.quote_plus(project_path)

            # API endpoint để lấy thông tin job
            job_info_url = f"{gitlab_api_url}/projects/{project_path_encoded}/jobs/{job_id}"

            # Gọi API để lấy thông tin job với verify=False để bỏ qua xác thực SSL
            job_response = requests.get(
                job_info_url,
                headers=headers,
                proxies=proxies,
                timeout=10,
                verify=False  # Bỏ qua xác thực SSL cho self-signed certificate
            )

            if job_response.status_code != 200:
                logger.warning(f"Không thể lấy thông tin job {job_id}: HTTP {job_response.status_code}")
                continue

            job_info = job_response.json()

            # Kiểm tra trạng thái job
            if job_info.get('status') != 'failed':
                logger.info(f"Job {job_id} không ở trạng thái thất bại (status={job_info.get('status')})")
                continue

            # API endpoint để lấy trace (log) của job
            job_trace_url = f"{job_info_url}/trace"

            # Gọi API để lấy log của job với verify=False để bỏ qua xác thực SSL
            trace_response = requests.get(
                job_trace_url,
                headers=headers,
                proxies=proxies,
                timeout=15,
                verify=False  # Bỏ qua xác thực SSL cho self-signed certificate
            )

            if trace_response.status_code != 200:
                logger.warning(f"Không thể lấy log của job {job_id}: HTTP {trace_response.status_code}")
                continue

            # Lấy nội dung log
            job_log = trace_response.text

            logger.info(f"Đã lấy được log của job thất bại {job_id}")
            logger.info(f"Danh sách các job URLs: {job_urls}")

            # Tạo thư mục logs nếu chưa tồn tại
            log_dir = os.path.join(os.getcwd(), "gitlab_job_logs")
            os.makedirs(log_dir, exist_ok=True)

            # Tạo tên file log với timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"job_{job_id}_{project_path.replace('/', '_')}_{timestamp}.log"
            log_filepath = os.path.join(log_dir, log_filename)

            # Ghi log ra file
            try:
                with open(log_filepath, 'w', encoding='utf-8') as log_file:
                    log_file.write(f"Job ID: {job_id}\n")
                    log_file.write(f"Project: {project_path}\n")
                    log_file.write(f"Status: {job_info.get('status')}\n")
                    log_file.write(f"Created at: {job_info.get('created_at')}\n")
                    log_file.write(f"Started at: {job_info.get('started_at')}\n")
                    log_file.write(f"Finished at: {job_info.get('finished_at')}\n")
                    log_file.write("\n--- JOB LOG ---\n\n")
                    log_file.write(job_log)
                logger.info(f"Đã lưu log vào file: {log_filepath}")
            except Exception as e:
                logger.error(f"Không thể ghi log ra file: {str(e)}")

            # Phân tích log với AI
            try:
                # Kiểm tra xem module phân tích AI có khả dụng không
                from gmail_agent.open_ai_analyzer import analyze_pipeline_error_with_ai, list_available_ai_providers

                # Tạo dữ liệu pipeline logs cho phân tích AI
                # Tách log thành các dòng và tìm các dòng lỗi
                log_lines = job_log.splitlines()
                error_lines = []
                for line in log_lines:
                    if any(err_term in line.lower() for err_term in ['error', 'exception', 'failed', 'failure', 'lỗi']):
                        error_lines.append(line.strip())

                # Giới hạn số dòng lỗi
                error_lines = error_lines[:20]

                # Chuẩn bị dữ liệu cho phân tích AI
                pipeline_logs = {
                    "success": True,
                    "job_links": job_urls,
                    "error_lines": error_lines,
                    "logs": job_log[:5000] if job_log else None  # Giới hạn độ dài để tránh quá tải
                }

                # Tạo thông tin dự án
                project_info = {
                    "project_name": project_path,
                    "commit_id": job_info.get('commit_ref_name', job_info.get('ref', 'unknown')),
                    "environment": job_info.get('stage', 'unknown'),
                    "error_type": "build_error"  # Giả định ban đầu, sẽ được phân tích chính xác hơn trong hàm phân tích
                }

                # Phân tích lỗi với AI
                logger.info(f"Đang phân tích log với AI...")
                ai_result = analyze_pipeline_error_with_ai(pipeline_logs, project_info)

                if ai_result:
                    logger.info(f"Phân tích AI hoàn tất: {ai_result.get('provider')} - {ai_result.get('model')}")

                    # Lưu kết quả phân tích AI vào file JSON
                    ai_result_dir = os.path.join(os.getcwd(), "email_analysis_results")
                    os.makedirs(ai_result_dir, exist_ok=True)
                    ai_result_filename = f"ai_analysis_{project_path.replace('/', '_')}_{job_id}_{timestamp}.json"
                    ai_result_filepath = os.path.join(ai_result_dir, ai_result_filename)

                    with open(ai_result_filepath, 'w', encoding='utf-8') as ai_file:
                        json.dump(ai_result, ai_file, ensure_ascii=False, indent=2)
                    logger.info(f"Kết quả phân tích AI đã được lưu vào: {ai_result_filepath}")

                    # Thêm kết quả AI vào kết quả trả về
                    return {
                        'success': True,
                        'job_info': job_info,
                        'job_log': job_log,
                        'log_filepath': log_filepath if 'log_filepath' in locals() else None,
                        'ai_analysis': ai_result,
                        'ai_result_filepath': ai_result_filepath
                    }

            except ImportError:
                logger.warning("Không thể import module phân tích AI. Bỏ qua phân tích AI.")
            except Exception as e:
                logger.error(f"Lỗi khi phân tích log với AI: {str(e)}")

            return {
                'success': True,
                'job_info': job_info,
                'job_log': job_log,
                'log_filepath': log_filepath if 'log_filepath' in locals() else None
            }

        except Exception as e:
            logger.error(f"Lỗi khi xử lý job URL {job_url}: {str(e)}")

    # Nếu không tìm thấy job thất bại nào
    return {
        'success': False,
        'error': "Không tìm thấy job thất bại nào hoặc không thể lấy log"
    }
