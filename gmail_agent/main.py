from gmail_agent.gmail_auth import get_gmail_service
from gmail_agent.ai_interface import analyze_email_with_custom_prompt

def main():
    """Hàm chính với menu để chọn loại tìm kiếm."""
    # Display the banner
    print("\n" + "="*40)
    print("Ý tưởng và sản phẩm của TuanNS2".center(40))
    print("="*40)

    while True:
        print("\n===== GMAIL AGENT =====")
        print("1. Phân tích email bằng AI")
        print("2. Thoát")

        choice = input("\nNhập lựa chọn của bạn (1-2): ")

        if choice == '1':
            # Get Gmail service and call analyze_email directly
            service = get_gmail_service()
            analyze_email_with_custom_prompt(service)
        elif choice == '2':
            print("Đang thoát. Tạm biệt!")
            break
        else:
            print("Lựa chọn không hợp lệ. Vui lòng nhập số từ 1 đến 2.")

if __name__ == '__main__':
    main()
