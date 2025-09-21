"""
Các thao tác AI để xử lý nội dung email.
Module này cung cấp các chức năng cơ bản để xử lý email: trích xuất nội dung,
tóm tắt, phát hiện thực thể và mục hành động.
Hỗ trợ tiếng Việt.
"""

import re
import nltk
import logging
import base64
import html
import string
from typing import Dict, List, Set, Any, Optional, Union, Tuple
import numpy as np
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tải các tài nguyên NLTK cần thiết
def _load_nltk_resources() -> None:
    """
    Tải các tài nguyên cần thiết từ NLTK.
    Gọi hàm này trước khi sử dụng các hàm xử lý ngôn ngữ.
    """
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        logger.info("Đang tải các tài nguyên NLTK...")
        nltk.download('punkt')
        nltk.download('stopwords')
        logger.info("Đã tải xong các tài nguyên NLTK")

# Gọi hàm tải tài nguyên
_load_nltk_resources()

# Từ dừng tiếng Việt (các từ phổ biến cần lọc ra)
VIETNAMESE_STOPWORDS: Set[str] = {
    'và', 'là', 'của', 'có', 'được', 'không', 'các', 'những', 'một', 'để', 'cho',
    'với', 'trong', 'này', 'đó', 'về', 'từ', 'khi', 'theo', 'tại', 'cũng', 'như',
    'đến', 'vào', 'sẽ', 'nên', 'đã', 'nhưng', 'vì', 'từng', 'nếu', 'thì', 'rằng',
    'hay', 'bị', 'bởi', 'sau', 'phải', 'tới', 'trên', 'dưới', 'đang', 'lúc', 'mà',
    'nhất', 'mình', 'rồi', 'còn', 'cứ', 'lại', 'vẫn', 'ra', 'ở', 'thế', 'nào', 'nó',
    'làm', 'chỉ', 'do', 'ai', 'đều', 'mới', 'thôi', 'vậy', 'tôi', 'bạn', 'anh', 'chị',
    'họ', 'mọi', 'điều', 'việc', 'thêm', 'quá', 'đi', 'chúng', 'ấy', 'ngay', 'thật', 'sự'
}

def decode_email_body(email_data: str) -> str:
    """
    Giải mã nội dung email từ base64 và xử lý HTML.

    Args:
        email_data: Chuỗi dữ liệu email đã được mã hóa base64

    Returns:
        Nội dung email đã được giải mã và làm sạch HTML
    """
    if not email_data:
        return ""

    try:
        # Giải mã base64
        decoded_bytes = base64.urlsafe_b64decode(email_data)
        text = decoded_bytes.decode('utf-8')

        # Làm sạch HTML
        text = clean_html_content(text)
        return text
    except Exception as e:
        logger.error(f"Lỗi khi giải mã nội dung email: {str(e)}")
        return ""

def clean_html_content(html_content: str) -> str:
    """
    Loại bỏ các thẻ HTML và giải mã các thực thể HTML.

    Args:
        html_content: Chuỗi HTML cần làm sạch

    Returns:
        Chuỗi văn bản đã làm sạch
    """
    # Loại bỏ thẻ HTML
    text = re.sub('<[^<]+?>', '', html_content)

    # Giải mã các thực thể HTML
    text = html.unescape(text)

    # Loại bỏ khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def extract_email_body(message: Dict[str, Any]) -> str:
    """
    Trích xuất và giải mã nội dung email từ một tin nhắn API Gmail.

    Args:
        message: Đối tượng tin nhắn từ Gmail API

    Returns:
        Nội dung email đã được giải mã
    """
    parts = []

    # Hàm để đệ quy trích xuất các phần
    def get_parts(payload: Dict[str, Any]) -> None:
        """Đệ quy qua các phần của email để trích xuất nội dung."""
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

    # Xử lý các phần đã trích xuất
    if parts:
        combined_content = ''.join(parts)
        return decode_email_body(combined_content)

    # Fallback: nếu không có phần nào, thử lấy snippet
    if 'snippet' in message:
        return message['snippet']

    return ""

def summarize_text(text: str, num_sentences: int = 3) -> str:
    """
    Tóm tắt văn bản sử dụng thuật toán TF-IDF.
    Hỗ trợ tiếng Việt.

    Args:
        text: Văn bản cần tóm tắt
        num_sentences: Số câu trong tóm tắt

    Returns:
        Chuỗi tóm tắt
    """
    # Kiểm tra đầu vào
    if not text or not text.strip():
        logger.warning("Nhận được văn bản trống để tóm tắt")
        return "Không có nội dung để tóm tắt."

    try:
        # Phân tách thành các câu
        sentences = sent_tokenize(text)

        # Nếu số câu ít hơn hoặc bằng yêu cầu, trả về nguyên văn
        if len(sentences) <= num_sentences:
            return text

        # Tạo ma trận TF-IDF với các từ dừng tiếng Việt và tiếng Anh
        combined_stopwords = list(VIETNAMESE_STOPWORDS)
        combined_stopwords.extend(stopwords.words('english'))
        vectorizer = TfidfVectorizer(stop_words=combined_stopwords)

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

    except Exception as e:
        logger.error(f"Lỗi khi tóm tắt văn bản: {str(e)}")
        # Fallback: trả về các câu đầu tiên
        sentences = sent_tokenize(text)
        return ' '.join(sentences[:num_sentences])

def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Trích xuất các thực thể có thể có (tên người, tổ chức, địa điểm) từ văn bản.
    Phương pháp đơn giản dựa trên từ viết hoa.

    Args:
        text: Văn bản cần trích xuất thực thể

    Returns:
        Dictionary chứa các thực thể đã trích xuất
    """
    if not text:
        logger.warning("Nhận được văn bản trống để trích xuất thực thể")
        return {"potential_names": [], "potential_locations": [], "potential_organizations": []}

    try:
        # Danh sách các từ dừng mở rộng bao gồm cả các từ tiếng Việt và tiếng Anh
        stop_words = list(VIETNAMESE_STOPWORDS) + list(stopwords.words('english'))

        # Tiền xử lý văn bản
        text = text.replace('\n', ' ')
        text = clean_html_content(text)

        # Tách thành các từ
        words = word_tokenize(text)

        # Tìm các cụm từ viết hoa
        potential_entities = extract_capitalized_phrases(words, stop_words)

        # Sử dụng Counter để đếm tần suất xuất hiện
        entity_counter = Counter(potential_entities)

        # Phân loại thực thể (đơn giản)
        entities = categorize_entities(entity_counter)

        return entities

    except Exception as e:
        logger.error(f"Lỗi khi trích xuất thực thể: {str(e)}")
        return {"potential_names": [], "potential_locations": [], "potential_organizations": []}

def extract_capitalized_phrases(words: List[str], stop_words: List[str]) -> List[str]:
    """
    Trích xuất các cụm từ viết hoa từ danh sách các từ.

    Args:
        words: Danh sách các từ đã được tách
        stop_words: Danh sách các từ dừng để bỏ qua

    Returns:
        Danh sách các cụm từ viết hoa tiềm năng
    """
    potential_entities = []
    i = 0

    while i < len(words):
        # Kiểm tra nếu từ bắt đầu bằng chữ hoa
        if words[i] and len(words[i]) > 0 and words[i][0].isupper():
            entity = words[i]
            j = i + 1

            # Tìm các từ liền kề cũng viết hoa để tạo thành cụm từ
            while j < len(words) and words[j] and len(words[j]) > 0 and words[j][0].isupper():
                entity += ' ' + words[j]
                j += 1

            # Kiểm tra xem thực thể có đủ dài không và không phải là từ dừng
            if len(entity) > 2 and entity.lower() not in stop_words:
                potential_entities.append(entity)
            i = j
        else:
            i += 1

    return potential_entities

def categorize_entities(entity_counter: Counter) -> Dict[str, List[str]]:
    """
    Phân loại các thực thể thành các nhóm.

    Args:
        entity_counter: Counter chứa các thực thể và tần suất của chúng

    Returns:
        Dictionary phân loại thực thể
    """
    # Lọc các thực thể xuất hiện nhiều hoặc có độ dài lớn
    significant_entities = [entity for entity, count in entity_counter.items()
                           if count > 1 or len(entity.split()) > 1]

    # Phân loại thô (có thể cải thiện bằng NER trong tương lai)
    potential_names = significant_entities.copy()
    potential_organizations = [entity for entity in significant_entities
                              if any(term in entity.lower() for term in ['công ty', 'tổ chức', 'company', 'corp', 'inc', 'ltd'])]
    potential_locations = [entity for entity in significant_entities
                          if any(term in entity.lower() for term in ['đường', 'quận', 'thành phố', 'tỉnh', 'street', 'road', 'city'])]

    # Loại bỏ các thực thể đã được phân loại cụ thể khỏi danh sách names
    for entity in potential_organizations + potential_locations:
        if entity in potential_names:
            potential_names.remove(entity)

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
