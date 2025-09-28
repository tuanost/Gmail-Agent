from gmail_agent.gmail_auth import get_gmail_service
from gmail_agent.ai_interface import analyze_email_with_custom_prompt
from gmail_agent.ai_connector import discover_available_models, check_model_connectivity
import os
from typing import Tuple, Dict, Any

def select_ai_platform() -> Tuple[str, str]:
    """
    Hiển thị menu để người dùng chọn nền tảng AI và model.

    Returns:
        Tuple[str, str]: (provider, model_name) - Provider AI và tên model đã chọn
    """
    def show_options(options, title):
        print(f"\n{title}")
        for i, opt in enumerate(options, 1):
            print(f"{i}. {opt}")

    def get_choice(options, prompt):
        while True:
            try:
                choice = int(input(prompt)) - 1
                if 0 <= choice < len(options):
                    return options[choice]
                print(f"Lựa chọn không hợp lệ. Vui lòng nhập số từ 1 đến {len(options)}.")
            except ValueError:
                print("Vui lòng nhập một số.")

    available_providers = ["google", "openai", "ollama"]
    while True:
        show_options([p.capitalize() for p in available_providers], "===== CHỌN NỀN TẢNG AI =====")
        selected_provider = get_choice(available_providers, "\nChọn nền tảng AI (nhập số): ")
        env_key = "GOOGLE_API_KEY" if selected_provider == "google" else "OPENAI_API_KEY" if selected_provider == "openai" else None
        if env_key and not os.getenv(env_key):
            print(f"\nKhông tìm thấy {env_key} trong biến môi trường. Vui lòng kiểm tra file .env")
            default_model = os.getenv("DEFAULT_GEMINI_MODEL" if selected_provider == "google" else "DEFAULT_OPENAI_MODEL", "gpt-3.5-turbo")
            print(f"Sử dụng model mặc định: {default_model}")
            return selected_provider, default_model
        print(f"\nĐang lấy danh sách models từ {selected_provider.capitalize()}...")
        models = discover_available_models(selected_provider)
        while True:
            show_options(models, f"Tìm thấy {len(models)} model khả dụng:")
            selected_model = get_choice(models, "\nChọn model AI (nhập số): ")
            print(f"\nĐang kiểm tra kết nối với model: {selected_model}...")
            if check_model_connectivity(selected_provider, selected_model):
                print(f"Kết nối thành công với model: {selected_model}\nĐã chọn model: {selected_model}")
                return selected_provider, selected_model
            print(f"Không thể kết nối tới model: {selected_model}.")
            retry = input("Nhập 1 để chọn lại model, nhập 2 để chọn lại provider: ").strip()
            if retry == '1':
                continue
            elif retry == '2':
                break
        print("Quay lại chọn nền tảng AI.")
        continue

def main():
    """Hàm chính với menu để chọn loại tìm kiếm."""
    # Display the banner
    print("\n" + "="*40)
    print("Ý tưởng và sản phẩm của TuanNS2".center(40))
    print("="*40)

    # Select AI platform and model at the beginning
    ai_provider, ai_model = select_ai_platform()
    if not ai_model:
        print("Không có model khả dụng hoặc bạn đã thoát quá trình chọn. Dừng chương trình.")
        return
    print(f"\nSử dụng AI: {ai_provider.capitalize()} / {ai_model}")

    # Store the selection in environment variables for use throughout the program
    os.environ["CURRENT_AI_PROVIDER"] = ai_provider
    os.environ["CURRENT_AI_MODEL"] = ai_model

    while True:
        print("\n===== GMAIL AGENT =====")
        print("1. Phân tích email bằng AI")
        print("2. Thay đổi nền tảng/model AI")
        print("0. Thoát")

        choice = input("\nNhập lựa chọn của bạn (0-2): ")

        if choice == '1':
            # Get Gmail service and call analyze_email directly
            service = get_gmail_service()
            analyze_email_with_custom_prompt(service)
        elif choice == '2':
            # Allow changing the AI platform/model
            ai_provider, ai_model = select_ai_platform()
            if not ai_model:
                print("Không có model khả dụng hoặc bạn đã thoát quá trình chọn. Dừng chương trình.")
                break
            os.environ["CURRENT_AI_PROVIDER"] = ai_provider
            os.environ["CURRENT_AI_MODEL"] = ai_model
            print(f"\nĐã thay đổi AI thành: {ai_provider.capitalize()} / {ai_model}")
        elif choice == '0':
            print("Đang thoát. Tạm biệt!")
            break
        else:
            print("Lựa chọn không hợp lệ. Vui lòng nhập số từ 0 đến 2.")

if __name__ == '__main__':
    main()
