"""
Giao diện xử lý email AI cho Gmail Agent.
Module này cung cấp chức năng phân tích email theo prompt tùy chỉnh.
"""

from gmail_agent.gmail_auth import get_gmail_service
from gmail_agent.prompt_ai import analyze_email_with_prompt, format_analysis_result, save_analysis_result
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

def analyze_email_with_custom_prompt(service):
    """
    Cho phép người dùng phân tích email bằng prompt tùy chỉnh.

    Tham số:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
    """
    # Hiển thị các tùy chọn tìm kiếm email
    print("\n===== TÌM KIẾM EMAIL =====")
    print("1. Tìm theo từ khóa")
    print("2. Tìm theo nhãn (label)")
    print("3. Xử lý email Gitlab")
    print("4. Quay lại menu chính")

    choice = input("\nNhập lựa chọn của bạn (1-4): ")

    messages = []
    if choice == '1':
        keyword = input("Nhập từ khóa để tìm kiếm email: ")
        from gmail_agent.gmail_operations import search_by_keyword
        messages = search_by_keyword(service, keyword)
    elif choice == '2':
        from gmail_agent.gmail_operations import get_email_labels, search_by_label

        # Lấy danh sách các nhãn (labels) và hiển thị cho người dùng
        labels = get_email_labels(service)

        if not labels:
            print("Không tìm thấy nhãn nào trong tài khoản Gmail của bạn.")
            return

        print("\nDanh sách các nhãn có sẵn:")
        for i, label in enumerate(labels, 1):
            print(f"{i}. {label['name']}")

        print(f"{len(labels) + 1}. Quay lại tìm kiếm email")

        label_choice = input("\nNhập số thứ tự nhãn để tìm kiếm hoặc chọn quay lại: ")
        try:
            label_index = int(label_choice) - 1

            # Option to return to email search menu
            if label_index == len(labels):
                # Return to email search options
                analyze_email_with_custom_prompt(service)
                return

            if 0 <= label_index < len(labels):
                selected_label = labels[label_index]
                messages = search_by_label(service, selected_label['id'], selected_label['name'])
            else:
                print("Lựa chọn không hợp lệ.")
                return
        except ValueError:
            print("Đầu vào không hợp lệ. Vui lòng nhập một số.")
            return
    elif choice == '3':
        # Xử lý email Gitlab
        handle_gitlab_emails(service)
        return
    elif choice == '4':
        # Return to main menu
        return
    else:
        print("Lựa chọn không hợp lệ.")
        return

    if not messages:
        print("Không tìm thấy email nào khớp với tiêu chí của bạn.")
        print("Quay lại menu tìm kiếm email...")
        # Return to email search options instead of exiting
        analyze_email_with_custom_prompt(service)
        return

    print(f"\nVui lòng chọn một email để phân tích:")

    # Hiển thị danh sách email để lựa chọn
    from gmail_agent.gmail_operations import get_email_details, get_email_subject

    emails_to_display = messages[:10]  # Giới hạn hiển thị 10 email
    for i, msg in enumerate(emails_to_display, 1):
        message = get_email_details(service, msg['id'])
        if message:
            subject = get_email_subject(message)
            print(f"{i}. {subject}")

    if len(messages) > 10:
        print(f"... và {len(messages) - 10} email khác.")

    print(f"{len(emails_to_display) + 1}. Quay lại tìm kiếm email")

    # Lấy lựa chọn của người dùng
    try:
        selection = int(input("\nNhập số thứ tự email để phân tích hoặc chọn quay lại: "))
        if selection == len(emails_to_display) + 1:
            # Return to email search
            analyze_email_with_custom_prompt(service)
            return

        if selection < 1 or selection > len(emails_to_display):
            print("Lựa chọn không hợp lệ.")
            return

        selected_message = messages[selection-1]

        # Lấy nội dung email
        print(f"Đang tải nội dung email...")
        from gmail_agent.email_ai import extract_email_body
        from gmail_agent.gmail_operations import get_sender, get_email_subject, get_recipients

        message = get_email_details(service, selected_message['id'])
        if not message:
            print("Không thể tải nội dung email.")
            return

        # Extract email metadata
        email_body = extract_email_body(message)
        email_subject = get_email_subject(message)
        email_sender = get_sender(message)
        email_recipients = get_recipients(message)

        # Create a structured format that includes metadata
        formatted_email = f"""
METADATA EMAIL:
Từ: {email_sender}
Đến: {email_recipients}
Chủ đề: {email_subject}
---
NỘI DUNG EMAIL:
{email_body}
"""

        # Lấy prompt mặc định từ biến môi trường
        from dotenv import load_dotenv
        import os
        load_dotenv()
        default_prompt = os.getenv("DEFAULT_EMAIL_PROMPT", "Bạn hãy đọc email và tóm tắt lại những ý chính, highlight các keywords cần thiết để tôi có nắm thông tin nhanh hơn. Hãy chú ý các thông tin về người gửi và người nhận trong phần METADATA.")

        custom_prompt = input("\nNhập prompt của bạn (Enter để dùng mặc định): ")
        if not custom_prompt.strip():
            custom_prompt = default_prompt

        # Phân tích email bằng prompt
        print(f"Đang phân tích email... (việc này có thể mất một lát)")
        result = analyze_email_with_prompt(formatted_email, custom_prompt)

        # Add the prompt to the result dictionary with Vietnamese key
        result["prompt_su_dung"] = custom_prompt

        # Hiển thị kết quả
        formatted_result = format_analysis_result(result)
        print("\n")
        print(formatted_result)

        # Lưu kết quả
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"prompt_analysis_{timestamp}.json"
        file_path = save_analysis_result(result, file_name)
        print(f"Kết quả phân tích đã được lưu vào: {file_path}")

    except ValueError:
        print("Đầu vào không hợp lệ. Vui lòng nhập một số.")

def handle_gitlab_emails(service):
    """
    Xử lý chuyên biệt các email Gitlab, đặc biệt là các email thông báo pipeline.

    Tham số:
        service: Phiên bản dịch vụ Gmail API đã được xác thực
    """
    from gmail_agent.gmail_operations import search_by_label, get_email_labels, get_email_details
    from gmail_agent.gitlab_email_handler import analyze_gitlab_email, is_gitlab_pipeline_email

    print("\n===== XỬ LÝ EMAIL GITLAB =====")
    print("1. Tìm tất cả email Gitlab")
    print("2. Tìm email Gitlab thông báo pipeline thất bại")
    print("3. Quay lại menu tìm kiếm")

    choice = input("\nNhập lựa chọn của bạn (1-3): ")

    if choice == "3":
        analyze_email_with_custom_prompt(service)
        return

    # Tìm nhãn Gitlab
    labels = get_email_labels(service)
    gitlab_label_id = None

    for label in labels:
        if label['name'].lower() == 'gitlab':
            gitlab_label_id = label['id']
            break

    if not gitlab_label_id:
        print("Không tìm thấy nhãn 'Gitlab' trong tài khoản Gmail của bạn.")
        print("Vui lòng tạo nhãn Gitlab và gán cho các email Gitlab trước khi sử dụng tính năng này.")
        input("Nhấn Enter để quay lại menu tìm kiếm...")
        analyze_email_with_custom_prompt(service)
        return

    # Tìm email Gitlab
    print("\nĐang tìm kiếm email Gitlab...")
    messages = search_by_label(service, gitlab_label_id, "Gitlab")

    if not messages:
        print("Không tìm thấy email Gitlab nào.")
        input("Nhấn Enter để quay lại menu tìm kiếm...")
        analyze_email_with_custom_prompt(service)
        return

    # Lọc email Gitlab theo tiêu chí
    filtered_messages = []

    if choice == "1":
        print("\nĐang phân tích tất cả email Gitlab...")
        for msg in messages:
            message = get_email_details(service, msg['id'])
            if message and is_gitlab_pipeline_email(message):
                filtered_messages.append(message)

        if not filtered_messages:
            print("Không tìm thấy email thông báo pipeline Gitlab nào.")
            input("Nhấn Enter để quay lại menu tìm kiếm...")
            analyze_email_with_custom_prompt(service)
            return

    elif choice == "2":
        print("\nĐang tìm kiếm email thông báo pipeline thất bại...")
        for msg in messages:
            message = get_email_details(service, msg['id'])
            from gmail_agent.gitlab_email_handler import is_failed_pipeline_email
            if message and is_failed_pipeline_email(message):
                filtered_messages.append(message)

        if not filtered_messages:
            print("Không tìm thấy email thông báo pipeline thất bại nào.")
            input("Nhấn Enter để quay lại menu tìm kiếm...")
            analyze_email_with_custom_prompt(service)
            return
    else:
        print("Lựa chọn không hợp lệ.")
        handle_gitlab_emails(service)
        return

    # Hiển thị danh sách email đã lọc
    from gmail_agent.gmail_operations import get_email_subject

    print(f"\nĐã tìm thấy {len(filtered_messages)} email Gitlab phù hợp:")
    for i, message in enumerate(filtered_messages[:10], 1):
        subject = get_email_subject(message)
        print(f"{i}. {subject}")

    if len(filtered_messages) > 10:
        print(f"... và {len(filtered_messages) - 10} email khác.")

    # Lấy lựa chọn của người dùng
    email_choice = input("\nNhập số thứ tự email để phân tích (0 để quay lại): ")
    try:
        choice_index = int(email_choice)

        if choice_index == 0:
            handle_gitlab_emails(service)
            return

        if 1 <= choice_index <= len(filtered_messages[:10]):
            selected_message = filtered_messages[choice_index - 1]

            # Phân tích email Gitlab
            print("\nĐang phân tích email Gitlab...")
            analysis = analyze_gitlab_email(selected_message)

            # Hiển thị kết quả
            print("\n===== KẾT QUẢ PHÂN TÍCH EMAIL GITLAB =====")
            print(f"Tiêu đề: {analysis['subject']}")
            print(f"Người gửi: {analysis['sender']}")
            print(f"Dự án: {analysis['project_name']}")
            print(f"Commit ID: {analysis['commit_id']}")
            print(f"Môi trường: {analysis['environment']}")
            print(f"Email thông báo thất bại: {'Có' if analysis['is_failed_pipeline'] else 'Không'}")

            # Hiển thị thông tin về URL pipeline
            if analysis['pipeline_url']:
                print(f"\nURL Pipeline: {analysis['pipeline_url']}")
                print(f"Trạng thái URL: {'Có thể truy cập' if analysis['pipeline_url_accessible'] else 'Không thể truy cập'}")
                print(f"Chi tiết: {analysis['accessibility_message']}")
            else:
                print("\nKhông tìm thấy URL pipeline trong email.")

            # Lưu kết quả phân tích
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"gitlab_analysis_{timestamp}.json"
            output_dir = "email_analysis_results"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            file_path = os.path.join(output_dir, file_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)

            print(f"\nKết quả phân tích đã được lưu vào: {file_path}")

            input("\nNhấn Enter để quay lại menu xử lý email Gitlab...")
            handle_gitlab_emails(service)
        else:
            print("Lựa chọn không hợp lệ.")
            handle_gitlab_emails(service)
    except ValueError:
        print("Đầu vào không hợp lệ. Vui lòng nhập một số.")
        handle_gitlab_emails(service)
