"""
Module tích hợp mock data vào quy trình xử lý pipeline log.
Cho phép sử dụng mock data khi không thể truy cập URL pipeline do giới hạn mạng nội bộ công ty.
"""

from gmail_agent.pipeline_mock_data import get_mock_pipeline_logs, get_all_mock_error_types

def use_mock_pipeline_logs(error_type=None):
    """
    Sử dụng mock data thay cho việc truy cập URL pipeline thực tế.

    Tham số:
        error_type: Loại lỗi cụ thể muốn test. Nếu None, sẽ hiển thị menu để chọn.

    Trả về:
        Kết quả phân tích lỗi pipeline
    """
    available_error_types = get_all_mock_error_types()

    # Nếu không chỉ định loại lỗi, hiển thị menu để người dùng chọn
    if not error_type:
        print("\n===== CHỌN LOẠI LỖI PIPELINE MUỐN TEST =====")
        for i, err_type in enumerate(available_error_types, 1):
            print(f"{i}. {err_type.replace('_', ' ').title()}")

        print("0. Quay lại")

        while True:
            try:
                choice = input("\nNhập lựa chọn của bạn (0-8): ")
                if choice == "0":
                    return None

                choice_index = int(choice) - 1
                if 0 <= choice_index < len(available_error_types):
                    error_type = available_error_types[choice_index]
                    break
                else:
                    print("Lựa chọn không hợp lệ.")
            except ValueError:
                print("Đầu vào không hợp lệ. Vui lòng nhập một số.")

    # Lấy mock data cho loại lỗi đã chọn
    if error_type in available_error_types:
        mock_logs = get_mock_pipeline_logs(error_type)

        # Hiển thị thông tin cơ bản về mock data (chỉ hiển thị logs)
        # Lấy phần logs để hiển thị và phân tích
        logs_to_show = None
        if isinstance(mock_logs, dict) and "logs" in mock_logs:
            logs_raw = mock_logs["logs"]
            if isinstance(logs_raw, str):
                logs_to_show = logs_raw.splitlines()
            elif isinstance(logs_raw, list):
                logs_to_show = logs_raw
        elif isinstance(mock_logs, list):
            logs_to_show = mock_logs

        # Hiển thị logs
        print(f"\n===== MOCK DATA CHO LỖI: {error_type.replace('_', ' ').upper()} =====")
        if logs_to_show and any(line.strip() for line in logs_to_show):
            for idx, line in enumerate(logs_to_show, 1):
                print(f"{idx}. {line}")
        else:
            print("Không có dữ liệu logs để hiển thị.")

        # Phân tích log bằng AI model
        from gmail_agent.ai_models import AIModelService
        ai_service = AIModelService()
        # Tạo prompt cho pipeline log (mock data là pipeline)
        prompt = ai_service._create_gitlab_analysis_prompt("\n".join(logs_to_show))
        ai_result = ai_service.analyze_with_prompt(prompt)
        print("\n===== KẾT QUẢ PHÂN TÍCH AI =====")
        print(ai_result)

        return mock_logs
    else:
        print(f"Không tìm thấy mock data cho loại lỗi: {error_type}")
        print(f"Các loại lỗi có sẵn: {', '.join(available_error_types)}")
        return None


def integrate_mock_pipeline_logs_to_gitlab_analysis(gitlab_analysis):
    """
    Tích hợp chức năng mock pipeline logs vào kết quả phân tích Gitlab.
    Hàm này được sử dụng khi URL pipeline không thể truy cập được.

    Tham số:
        gitlab_analysis: Dictionary chứa kết quả phân tích email Gitlab

    Trả về:
        Dictionary đã được cập nhật với mock data
    """
    if not gitlab_analysis:
        return gitlab_analysis

    # Chỉ tích hợp mock data khi có URL pipeline nhưng không thể truy cập
    if gitlab_analysis.get('pipeline_url') and not gitlab_analysis.get('pipeline_url_accessible'):
        print("\nURL Pipeline không thể truy cập do nằm trong mạng nội bộ công ty.")
        print("Bạn có muốn sử dụng mock data để test chức năng phân tích log lỗi không?")
        print("1. Có, sử dụng mock data")
        print("0. Không, bỏ qua")

        choice = input("\nNhập lựa chọn của bạn (0-1): ")

        if choice == "1":
            # Sử dụng mock data
            mock_result = use_mock_pipeline_logs()

            if mock_result:
                # Cập nhật kết quả phân tích với mock data
                mock_logs = get_mock_pipeline_logs(mock_result.get('error_type', 'build_error'))

                # Đánh dấu rằng đây là dữ liệu giả lập
                if mock_logs:
                    mock_logs["is_mock_data"] = True

                gitlab_analysis['pipeline_logs'] = mock_logs
                gitlab_analysis['error_analysis'] = mock_result
                gitlab_analysis['using_mock_data'] = True

                print("\nĐã tích hợp mock data vào kết quả phân tích.")

    return gitlab_analysis


# Ví dụ sử dụng:
if __name__ == "__main__":
    # Test phân tích lỗi xây dựng
    result = use_mock_pipeline_logs("build_error")
    print("\nKết quả test:", "Thành công" if result else "Thất bại")
