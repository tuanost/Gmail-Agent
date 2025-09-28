"""
Giao diện xử lý email AI cho Gmail Agent.
Module này cung cấp chức năng phân tích email theo prompt tùy chỉnh.
"""

from gmail_agent.gmail_auth import get_gmail_service
from gmail_agent.prompt_ai import analyze_email_with_prompt, save_analysis_result
import json
import os
from datetime import datetime

def save_ai_results(result, filename=None):
    """
    Lưu kết quả xử lý AI vào một tệp JSON.

    Args:
        result: AI processing results
        filename: Optional filename, defaults to timestamp

    Returns:
        Path to the saved file
    """
    if not result:
        return None

    output_dir = "email_analysis_results"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"email_analysis_{timestamp}.json"

    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nKết quả phân tích đã được lưu vào: {filepath}")
    return filepath

def select_email_from_list(service, emails_to_display):
    if not emails_to_display:
        return None
    from gmail_agent.gmail_operations import get_email_details, get_email_subject

    for i, msg in enumerate(emails_to_display, 1):
        # msg luôn là dict email có key 'id'
        message_detail = get_email_details(service, msg['id'])
        subject = get_email_subject(message_detail)
        print(f"{i}. {subject}")

    print("0. Quay lại tìm kiếm email")
    selection = input("\nNhập số thứ tự email để phân tích hoặc nhập 0 để quay lại: ")
    if selection == "0":
        return None
    try:
        selection = int(selection)
        if selection < 1 or selection > len(emails_to_display):
            print("Lựa chọn không hợp lệ.")
            return None
        # Trả về chi tiết email đã chọn
        return get_email_details(service, emails_to_display[selection-1]['id'])
    except ValueError:
        print("Đầu vào không hợp lệ. Vui lòng nhập một số.")
        return None

def analyze_and_display_email(selected_message):
    from gmail_agent.gitlab_operations import is_gitlab_pipeline_email
    from gmail_agent.ai_models import AIModelService
    ai_service = AIModelService()
    if is_gitlab_pipeline_email(selected_message):
        from gmail_agent.gitlab_operations import extract_job_urls, extract_pipeline_logs
        job_urls = list(extract_job_urls(selected_message).values())
        all_logs = []
        for url in job_urls:
            log = extract_pipeline_logs(url)
            if log:
                all_logs.append(log)
        combined_log = '\n\n'.join(all_logs)
        prompt = ai_service._create_gitlab_analysis_prompt(combined_log)
    else:
        from gmail_agent.email_extractor import extract_email_body
        email_body = extract_email_body(selected_message)
        prompt = ai_service._create_email_analysis_prompt(email_body, "Tóm tắt email và đưa ra gợi ý trả lời.")
    result = ai_service.analyze_with_prompt(prompt)
    print("\n===== KẾT QUẢ PHÂN TÍCH EMAIL =====")
    if result.get("error"):
        print(f"Lỗi: {result.get('message')}")
        print(f"Phân tích: {result.get('phan_tich')}")
    else:
        for key, value in result.items():
            if key != "model_info":
                print(f"{key}: {value}")
        if result.get("model_info"):
            print("\n[Thông tin model AI]")
            print(result["model_info"])
    # Save result to file
    save_dir = os.path.join(os.path.dirname(__file__), '../email_analysis_results')
    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"prompt_analysis_{timestamp}.json"
    filepath = os.path.join(save_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n[Đã lưu kết quả phân tích vào file: {filepath}]")

def analyze_email_with_custom_prompt(service):
    from gmail_agent.gmail_operations import search_by_keyword, search_by_label, get_email_labels
    from gmail_agent.gitlab_operations import is_failed_pipeline_email
    while True:
        print("\n===== TÌM KIẾM EMAIL =====")
        print("1. Tìm theo từ khóa")
        print("2. Tìm theo nhãn (label)")
        print("3. Xử lý email Gitlab failed")
        print("0. Thoát")
        choice = input("\nNhập lựa chọn của bạn (0-3): ")
        emails_to_display = []
        if choice == '1':
            keyword = input("Nhập từ khóa để tìm kiếm email: ")
            emails_to_display = search_by_keyword(service, keyword)[:10]
        elif choice == '2':
            labels = get_email_labels(service)
            if not labels:
                print("Không tìm thấy nhãn nào trong tài khoản Gmail của bạn.")
                continue
            print("\nDanh sách các nhãn có sẵn:")
            for i, label in enumerate(labels, 1):
                print(f"{i}. {label['name']}")
            label_choice = input("\nNhập số thứ tự nhãn để tìm kiếm hoặc nhập 0 để quay lại: ")
            if label_choice == "0":
                continue
            try:
                label_index = int(label_choice) - 1
                if 0 <= label_index < len(labels):
                    selected_label = labels[label_index]
                    emails_to_display = search_by_label(service, selected_label['id'], selected_label['name'])[:10]
                else:
                    print("Lựa chọn không hợp lệ.")
                    continue
            except ValueError:
                print("Đầu vào không hợp lệ. Vui lòng nhập một số.")
                continue
        elif choice == '3':
            labels = get_email_labels(service)
            gitlab_label_id = None
            for label in labels:
                if label['name'].lower() == 'gitlab':
                    gitlab_label_id = label['id']
                    break
            if not gitlab_label_id:
                print("Không tìm thấy nhãn 'Gitlab' trong tài khoản Gmail của bạn.")
                continue
            print("\nĐang tìm kiếm email Gitlab pipeline failed...")
            messages = search_by_label(service, gitlab_label_id, "Gitlab")
            failed_messages = []
            from gmail_agent.gmail_operations import get_email_details
            for msg in messages:
                message = get_email_details(service, msg['id'])
                if message and is_failed_pipeline_email(message):
                    failed_messages.append(msg)
            failed_messages.sort(key=lambda m: int(get_email_details(service, m['id']).get('internalDate', '0')), reverse=True)
            emails_to_display = failed_messages[:10]
        elif choice == '0':
            break
        else:
            print("Lựa chọn không hợp lệ.")
            continue
        selected_message = select_email_from_list(service, emails_to_display)
        if selected_message:
            analyze_and_display_email(selected_message)
