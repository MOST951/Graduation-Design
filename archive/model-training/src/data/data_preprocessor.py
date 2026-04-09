import re
import jieba
from typing import List

class DataPreprocessor:
    """Handles text cleaning, tokenization, and normalization."""

    def __init__(self, stopwords: List[str] = None):
        self.stopwords = set(stopwords) if stopwords else set()

    def clean_text(self, text: str) -> str:
        """Remove special characters, URLs, and mentions."""
        text = re.sub(r'http\S+', '', text)  # Remove URLs
        text = re.sub(r'@\w+', '', text)    # Remove mentions
        text = re.sub(r'#\S+#', '', text)   # Remove hashtags
        text = re.sub(r'[\W_]+', ' ', text) # Remove special characters
        return text.strip()

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text using jieba and remove stopwords."""
        tokens = jieba.lcut(text)
        return [token for token in tokens if token.strip() and token not in self.stopwords]

    def normalize(self, tokens: List[str]) -> List[str]:
        """Normalize tokens (e.g., to lowercase)."""
        return [token.lower() for token in tokens]

    def preprocess(self, text: str) -> str:
        """Full preprocessing pipeline."""
        cleaned_text = self.clean_text(text)
        tokens = self.tokenize(cleaned_text)
        normalized_tokens = self.normalize(tokens)
        return ' '.join(normalized_tokens)
