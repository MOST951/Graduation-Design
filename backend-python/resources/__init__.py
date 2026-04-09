# 资源模块
"""
资源模块
========

包含：
- sentiment_dict: 情感词典
"""

from .sentiment_dict import (
    SentimentDictionary,
    SentimentWord,
    get_sentiment_dictionary,
    analyze_sentiment,
)

__all__ = [
    'SentimentDictionary',
    'SentimentWord',
    'get_sentiment_dictionary',
    'analyze_sentiment',
]
