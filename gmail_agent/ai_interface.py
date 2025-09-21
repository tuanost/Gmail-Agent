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
    print("3. Quay lại menu chính")

    choice = input("\nNhập lựa chọn của bạn (1-3): ")

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
