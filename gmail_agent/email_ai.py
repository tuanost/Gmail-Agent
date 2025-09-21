"""
Các thao tác AI để xử lý nội dung email.
Module này cung cấp các chức năng cơ bản để xử lý email: trích xuất nội dung,
tóm tắt, phát hiện thực thể và mục hành động.
Hỗ trợ tiếng Việt.
"""

import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter
import base64
import html
import numpy as np
import string

# Tải các tài nguyên NLTK cần thiết khi chạy lần đầu
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

# Từ dừng tiếng Việt (các từ phổ biến cần lọc ra)
VIETNAMESE_STOPWORDS = {
    'và', 'là', 'của', 'có', 'được', 'không', 'các', 'những', 'một', 'để', 'cho',
    'với', 'trong', 'này', 'đó', 'về', 'từ', 'khi', 'theo', 'tại', 'cũng', 'như',
    'đến', 'vào', 'sẽ', 'nên', 'đã', 'nhưng', 'vì', 'từng', 'nếu', 'thì', 'rằng',
    'hay', 'bị', 'bởi', 'sau', 'phải', 'tới', 'trên', 'dưới', 'đang', 'lúc', 'mà',
    'nhất', 'mình', 'rồi', 'còn', 'cứ', 'lại', 'vẫn', 'ra', 'ở', 'thế', 'nào', 'nó',
    'làm', 'chỉ', 'do', 'ai', 'đều', 'mới', 'thôi', 'vậy', 'tôi', 'bạn', 'anh', 'chị',
    'họ', 'mọi', 'điều', 'việc', 'thêm', 'quá', 'đi', 'chúng', 'ấy', 'ngay', 'thật', 'sự'
}

def decode_email_body(email_data):
    """Giải mã nội dung email từ base64 nếu cần."""
    if not email_data:
        return ""

    try:
        # Thử giải mã base64
        decoded_bytes = base64.urlsafe_b64decode(email_data)
        text = decoded_bytes.decode('utf-8')

        # Loại bỏ thẻ HTML
        text = re.sub('<[^<]+?>', '', text)

        # Giải mã các thực thể HTML
        text = html.unescape(text)

        return text
    except:
        return ""

def extract_email_body(message):
    """Trích xuất và giải mã nội dung email từ một tin nhắn API Gmail."""
    parts = []

    # Hàm để đệ quy trích xuất các phần
    def get_parts(payload):
        if 'parts' in payload:
            for part in payload['parts']:
                get_parts(part)
        elif 'body' in payload and 'data' in payload['body']:
            mime_type = payload.get('mimeType', '')
            if mime_type == 'text/plain' or mime_type.startswith('text/'):
                parts.append(payload['body']['data'])

    # Bắt đầu đệ quy từ payload gốc
    if 'payload' in message:
        get_parts(message['payload'])

    # Nếu có nhiều phần, nối chúng lại
    if parts:
        combined_content = ''.join(parts)
        return decode_email_body(combined_content)

    # Nếu không có phần nào, thử lấy snippet
    if 'snippet' in message:
        return message['snippet']

    return ""

def summarize_text(text, num_sentences=3):
    """
    Tóm tắt văn bản sử dụng thuật toán TF-IDF.
    Hỗ trợ tiếng Việt.

    Tham số:
        text: Văn bản cần tóm tắt
        num_sentences: Số câu trong tóm tắt

    Trả về:
        Chuỗi tóm tắt
    """
    # Kiểm tra đầu vào
    if not text or not text.strip():
        return "Không có nội dung để tóm tắt."

    # Phân tách thành các câu
    sentences = sent_tokenize(text)

    if len(sentences) <= num_sentences:
        return text

    # Tạo ma trận TF-IDF
    vectorizer = TfidfVectorizer(stop_words=list(VIETNAMESE_STOPWORDS))
    try:
        # Tính toán ma trận TF-IDF
        tfidf_matrix = vectorizer.fit_transform(sentences)

        # Tính điểm cho mỗi câu dựa trên tổng điểm TF-IDF
        sentence_scores = np.sum(tfidf_matrix.toarray(), axis=1)

        # Chọn các câu có điểm cao nhất
        top_sentence_indices = sentence_scores.argsort()[-num_sentences:]
        top_sentence_indices = sorted(top_sentence_indices)

        # Tạo tóm tắt từ các câu được chọn
        summary_sentences = [sentences[i] for i in top_sentence_indices]
        summary = ' '.join(summary_sentences)

        return summary

    except ValueError:
        # Nếu có lỗi, trả về các câu đầu tiên
        return ' '.join(sentences[:num_sentences])

def extract_entities(text):
    """
    Trích xuất các thực thể có thể có (tên người, tổ chức, địa điểm) từ văn bản.
    Phương pháp đơn giản dựa trên từ viết hoa.

    Tham số:
        text: Văn bản cần trích xuất thực thể

    Trả về:
        Dictionary chứa các thực thể đã trích xuất
    """
    if not text:
        return {"potential_names": [], "potential_locations": [], "potential_organizations": []}

    # Danh sách các từ dừng mở rộng bao gồm cả các từ tiếng Việt thường dùng
    stop_words = list(VIETNAMESE_STOPWORDS) + list(stopwords.words('english'))

    # Tiền xử lý
    text = text.replace('\n', ' ')

    # Tách thành các từ
    words = word_tokenize(text)

    # Tìm các cụm từ viết hoa
    potential_entities = []
    i = 0
    while i < len(words):
        if words[i] and words[i][0].isupper():
            entity = words[i]
            j = i + 1
            while j < len(words) and words[j] and words[j][0].isupper():
                entity += ' ' + words[j]
                j += 1

            # Kiểm tra xem thực thể có đủ dài không và không phải là từ dừng
            if len(entity) > 2 and entity.lower() not in stop_words:
                potential_entities.append(entity)
            i = j
        else:
            i += 1

    # Sử dụng Counter để đếm tần suất xuất hiện
    entity_counter = Counter(potential_entities)

    # Lọc các thực thể xuất hiện nhiều lần hoặc có độ dài lớn
    filtered_entities = [entity for entity, count in entity_counter.items()
                         if count > 1 or len(entity.split()) > 1]

    # Phân loại thực thể một cách đơn giản
    potential_names = []
    potential_locations = []
    potential_organizations = []

    location_indicators = ['Phố', 'Đường', 'Quận', 'Huyện', 'Thành phố', 'TP', 'Tỉnh', 'Làng']
    org_indicators = ['Công ty', 'Tổ chức', 'Đại học', 'Trường', 'Viện', 'Ban', 'Nhóm']

    for entity in filtered_entities:
        if any(entity.startswith(indicator) for indicator in org_indicators):
            potential_organizations.append(entity)
        elif any(entity.startswith(indicator) for indicator in location_indicators):
            potential_locations.append(entity)
        else:
            potential_names.append(entity)

    return {
        "potential_names": potential_names,
        "potential_locations": potential_locations,
        "potential_organizations": potential_organizations
    }

def extract_action_items(text):
    """
    Trích xuất các mục hành động từ văn bản.

    Tham số:
        text: Văn bản cần trích xuất các mục hành động

    Trả về:
        Danh sách các mục hành động đã trích xuất
    """
    if not text:
        return []

    # Mẫu regex cho các dấu hiệu hành động
    action_patterns = [
        r'cần (phải )?([\w\s\.,]+?)(?=\.|$)',
        r'nên (phải )?([\w\s\.,]+?)(?=\.|$)',
        r'hãy (phải )?([\w\s\.,]+?)(?=\.|$)',
        r'phải ([\w\s\.,]+?)(?=\.|$)',
        r'yêu cầu ([\w\s\.,]+?)(?=\.|$)',
        r'đề nghị ([\w\s\.,]+?)(?=\.|$)',
        r'vui lòng ([\w\s\.,]+?)(?=\.|$)',
        r'xin (hãy )?([\w\s\.,]+?)(?=\.|$)',
        r'gửi ([\w\s\.,]+?)(?=\.|$)',
        r'chuyển ([\w\s\.,]+?)(?=\.|$)',
        r'thực hiện ([\w\s\.,]+?)(?=\.|$)',
        r'hoàn thành ([\w\s\.,]+?)(?=\.|$)',
        r'làm ([\w\s\.,]+?)(?=\.|$)',
    ]

    action_items = []

    # Tách thành các câu để xử lý
    sentences = sent_tokenize(text)

    for sentence in sentences:
        # Kiểm tra các mẫu hành động
        for pattern in action_patterns:
            matches = re.findall(pattern, sentence.lower())
            for match in matches:
                if isinstance(match, tuple):
                    action = match[0] if len(match) == 1 else match[1]
                else:
                    action = match

                # Chuẩn hóa hành động và thêm vào danh sách
                action = action.strip()
                if action and len(action) > 3:  # Bỏ qua các hành động quá ngắn
                    action_full = f"{action[0].upper()}{action[1:]}"
                    if action_full not in action_items:
                        action_items.append(action_full)

    return action_items
