"""
微博情感词典模块
================

提供完整的中文情感分析词典支持：
1. 基础情感词库（正面/负面/程度/否定）
2. 微博特有词库（表情/网络用语/缩写）
3. 领域扩展词库（疫情/娱乐/旅游）
4. 情感强度标注和权重配置

使用示例:
    from backend.resources.sentiment_dict import SentimentDictionary
    
    # 加载词典
    dict_manager = SentimentDictionary()
    
    # 分析情感
    result = dict_manager.analyze("这部电影真的太好看了！")
    print(result)  # {'label': 'positive', 'score': 0.85, 'confidence': 0.9}
"""

import os
import re
import json
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from functools import lru_cache

logger = logging.getLogger('SentimentDictionary')

# 词典根目录
DICT_ROOT = os.path.dirname(__file__)


@dataclass
class SentimentWord:
    """情感词条目"""
    word: str
    polarity: str  # positive/negative/neutral
    intensity: float  # 0-1
    pos: str = ''  # 词性
    domain: str = ''  # 领域
    
    def __hash__(self):
        return hash(self.word)


@dataclass
class DegreeWord:
    """程度副词条目"""
    word: str
    coefficient: float  # 程度系数


@dataclass
class NegationWord:
    """否定词条目"""
    word: str
    strength: float  # 否定强度


class SentimentDictionary:
    """
    情感词典管理器
    
    功能：
    - 加载和管理多种情感词典
    - 提供词典查询接口
    - 支持情感分析计算
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化词典管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.dict_root = DICT_ROOT
        
        # 词典存储
        self.positive_words: Dict[str, SentimentWord] = {}
        self.negative_words: Dict[str, SentimentWord] = {}
        self.degree_words: Dict[str, DegreeWord] = {}
        self.negation_words: Dict[str, NegationWord] = {}
        self.emoji_dict: Dict[str, SentimentWord] = {}
        self.internet_dict: Dict[str, SentimentWord] = {}
        self.abbreviation_dict: Dict[str, SentimentWord] = {}
        self.domain_dicts: Dict[str, Dict[str, SentimentWord]] = {}
        
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 加载所有词典
        self._load_all_dictionaries()
        
        logger.info(f"情感词典加载完成: "
                   f"正面词{len(self.positive_words)}个, "
                   f"负面词{len(self.negative_words)}个, "
                   f"程度词{len(self.degree_words)}个, "
                   f"否定词{len(self.negation_words)}个")
    
    def _load_config(self, config_path: str = None) -> Dict:
        """加载配置文件"""
        if config_path is None:
            config_path = os.path.join(self.dict_root, 'config', 'weights.json')
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}")
        
        return {}
    
    def _load_all_dictionaries(self):
        """加载所有词典"""
        # 基础词典
        self._load_basic_dict('positive', self.positive_words)
        self._load_basic_dict('negative', self.negative_words)
        self._load_degree_dict()
        self._load_negation_dict()
        
        # 微博词典
        self._load_emoji_dict()
        self._load_internet_dict()
        self._load_abbreviation_dict()
        
        # 领域词典
        for domain in ['pandemic', 'entertainment', 'tourism']:
            self._load_domain_dict(domain)
    
    def _load_basic_dict(self, dict_type: str, target_dict: Dict):
        """加载基础情感词典"""
        file_path = os.path.join(self.dict_root, 'basic', f'{dict_type}.txt')
        
        if not os.path.exists(file_path):
            logger.warning(f"词典文件不存在: {file_path}")
            return
        
        polarity = 'positive' if dict_type == 'positive' else 'negative'
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 1:
                        word = parts[0]
                        intensity = float(parts[1]) if len(parts) > 1 else 0.5
                        pos = parts[2] if len(parts) > 2 else ''
                        
                        target_dict[word] = SentimentWord(
                            word=word,
                            polarity=polarity,
                            intensity=intensity,
                            pos=pos,
                            domain='basic'
                        )
            
            logger.debug(f"加载{dict_type}词典: {len(target_dict)}个词")
            
        except Exception as e:
            logger.error(f"加载词典失败 {file_path}: {e}")
    
    def _load_degree_dict(self):
        """加载程度副词词典"""
        file_path = os.path.join(self.dict_root, 'basic', 'degree.txt')
        
        if not os.path.exists(file_path):
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 2:
                        word = parts[0]
                        coefficient = float(parts[1])
                        self.degree_words[word] = DegreeWord(word, coefficient)
            
            logger.debug(f"加载程度词典: {len(self.degree_words)}个词")
            
        except Exception as e:
            logger.error(f"加载程度词典失败: {e}")
    
    def _load_negation_dict(self):
        """加载否定词词典"""
        file_path = os.path.join(self.dict_root, 'basic', 'negation.txt')
        
        if not os.path.exists(file_path):
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 2:
                        word = parts[0]
                        strength = float(parts[1])
                        self.negation_words[word] = NegationWord(word, strength)
            
            logger.debug(f"加载否定词典: {len(self.negation_words)}个词")
            
        except Exception as e:
            logger.error(f"加载否定词典失败: {e}")
    
    def _load_emoji_dict(self):
        """加载表情词典"""
        file_path = os.path.join(self.dict_root, 'weibo', 'emoji.txt')
        
        if not os.path.exists(file_path):
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 3:
                        emoji = parts[0]
                        polarity = parts[1]
                        intensity = float(parts[2])
                        
                        self.emoji_dict[emoji] = SentimentWord(
                            word=emoji,
                            polarity=polarity,
                            intensity=intensity,
                            domain='emoji'
                        )
            
            logger.debug(f"加载表情词典: {len(self.emoji_dict)}个")
            
        except Exception as e:
            logger.error(f"加载表情词典失败: {e}")
    
    def _load_internet_dict(self):
        """加载网络用语词典"""
        file_path = os.path.join(self.dict_root, 'weibo', 'internet.txt')
        
        if not os.path.exists(file_path):
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 3:
                        word = parts[0]
                        polarity = parts[1]
                        intensity = float(parts[2])
                        pos = parts[3] if len(parts) > 3 else ''
                        
                        self.internet_dict[word] = SentimentWord(
                            word=word,
                            polarity=polarity,
                            intensity=intensity,
                            pos=pos,
                            domain='internet'
                        )
            
            logger.debug(f"加载网络用语词典: {len(self.internet_dict)}个")
            
        except Exception as e:
            logger.error(f"加载网络用语词典失败: {e}")
    
    def _load_abbreviation_dict(self):
        """加载缩写词典"""
        file_path = os.path.join(self.dict_root, 'weibo', 'abbreviation.txt')
        
        if not os.path.exists(file_path):
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 4:
                        abbr = parts[0]
                        full_form = parts[1]
                        polarity = parts[2]
                        intensity = float(parts[3])
                        
                        self.abbreviation_dict[abbr] = SentimentWord(
                            word=abbr,
                            polarity=polarity,
                            intensity=intensity,
                            domain='abbreviation'
                        )
            
            logger.debug(f"加载缩写词典: {len(self.abbreviation_dict)}个")
            
        except Exception as e:
            logger.error(f"加载缩写词典失败: {e}")
    
    def _load_domain_dict(self, domain: str):
        """加载领域词典"""
        file_path = os.path.join(self.dict_root, 'domain', f'{domain}.txt')
        
        if not os.path.exists(file_path):
            return
        
        self.domain_dicts[domain] = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 3:
                        word = parts[0]
                        polarity = parts[1]
                        intensity = float(parts[2])
                        pos = parts[3] if len(parts) > 3 else ''
                        
                        self.domain_dicts[domain][word] = SentimentWord(
                            word=word,
                            polarity=polarity,
                            intensity=intensity,
                            pos=pos,
                            domain=domain
                        )
            
            logger.debug(f"加载{domain}领域词典: {len(self.domain_dicts[domain])}个")
            
        except Exception as e:
            logger.error(f"加载领域词典失败 {domain}: {e}")
    
    # ==================== 查询接口 ====================
    
    def lookup(self, word: str) -> Optional[SentimentWord]:
        """
        查询词语的情感信息
        
        Args:
            word: 待查询词语
            
        Returns:
            SentimentWord对象或None
        """
        # 优先查询网络用语和缩写
        if word in self.internet_dict:
            return self.internet_dict[word]
        if word in self.abbreviation_dict:
            return self.abbreviation_dict[word]
        if word in self.emoji_dict:
            return self.emoji_dict[word]
        
        # 查询基础词典
        if word in self.positive_words:
            return self.positive_words[word]
        if word in self.negative_words:
            return self.negative_words[word]
        
        # 查询领域词典
        for domain_dict in self.domain_dicts.values():
            if word in domain_dict:
                return domain_dict[word]
        
        return None
    
    def is_positive(self, word: str) -> bool:
        """判断是否为正面词"""
        entry = self.lookup(word)
        return entry is not None and entry.polarity == 'positive'
    
    def is_negative(self, word: str) -> bool:
        """判断是否为负面词"""
        entry = self.lookup(word)
        return entry is not None and entry.polarity == 'negative'
    
    def is_degree_word(self, word: str) -> bool:
        """判断是否为程度副词"""
        return word in self.degree_words
    
    def is_negation(self, word: str) -> bool:
        """判断是否为否定词"""
        return word in self.negation_words
    
    def get_degree_coefficient(self, word: str) -> float:
        """获取程度系数"""
        if word in self.degree_words:
            return self.degree_words[word].coefficient
        return 1.0
    
    def get_negation_strength(self, word: str) -> float:
        """获取否定强度"""
        if word in self.negation_words:
            return self.negation_words[word].strength
        return 0.0
    
    # ==================== 情感分析 ====================
    
    def analyze(self, text: str, domain: str = None) -> Dict:
        """
        分析文本情感
        
        Args:
            text: 输入文本
            domain: 领域（可选）
            
        Returns:
            {
                'label': 'positive/negative/neutral',
                'score': float (-1 to 1),
                'confidence': float (0 to 1),
                'details': {...}
            }
        """
        if not text or len(text.strip()) < 2:
            return {
                'label': 'neutral',
                'score': 0.0,
                'confidence': 0.0,
                'details': {}
            }
        
        # 分词（简单实现，可替换为jieba）
        tokens = self._tokenize(text)
        
        # 计算情感得分
        positive_score = 0.0
        negative_score = 0.0
        word_count = 0
        matched_words = []
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            # 检查否定词
            negation_factor = 1.0
            degree_factor = 1.0
            
            # 向前查找程度词和否定词
            for j in range(max(0, i - 3), i):
                prev_token = tokens[j]
                if self.is_negation(prev_token):
                    negation_factor *= -self.get_negation_strength(prev_token)
                if self.is_degree_word(prev_token):
                    degree_factor *= self.get_degree_coefficient(prev_token)
            
            # 查询情感词
            entry = self.lookup(token)
            if entry:
                base_score = entry.intensity * degree_factor * negation_factor
                
                if entry.polarity == 'positive':
                    if negation_factor < 0:
                        negative_score += abs(base_score)
                    else:
                        positive_score += base_score
                elif entry.polarity == 'negative':
                    if negation_factor < 0:
                        positive_score += abs(base_score)
                    else:
                        negative_score += abs(base_score)
                
                word_count += 1
                matched_words.append({
                    'word': token,
                    'polarity': entry.polarity,
                    'intensity': entry.intensity,
                    'adjusted_score': base_score
                })
            
            i += 1
        
        # 计算最终得分
        total_score = positive_score - negative_score
        
        # 归一化到 [-1, 1]
        if word_count > 0:
            normalized_score = total_score / (word_count * 1.5)
            normalized_score = max(-1.0, min(1.0, normalized_score))
        else:
            normalized_score = 0.0
        
        # 确定标签
        thresholds = self.config.get('thresholds', {})
        pos_threshold = thresholds.get('positive', 0.2)
        neg_threshold = thresholds.get('negative', -0.2)
        
        if normalized_score >= pos_threshold:
            label = 'positive'
        elif normalized_score <= neg_threshold:
            label = 'negative'
        else:
            label = 'neutral'
        
        # 计算置信度
        confidence = min(1.0, abs(normalized_score) + 0.3) if word_count > 0 else 0.0
        
        return {
            'label': label,
            'score': round(normalized_score, 4),
            'confidence': round(confidence, 4),
            'details': {
                'positive_score': round(positive_score, 4),
                'negative_score': round(negative_score, 4),
                'matched_words': matched_words,
                'word_count': word_count
            }
        }
    
    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        # 尝试使用jieba
        try:
            import jieba
            return list(jieba.cut(text))
        except ImportError:
            pass
        
        # 简单分词：按字符和标点分割
        tokens = []
        current_word = ''
        
        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # 中文字符
                current_word += char
            else:
                if current_word:
                    tokens.append(current_word)
                    current_word = ''
                if char.strip():
                    tokens.append(char)
        
        if current_word:
            tokens.append(current_word)
        
        return tokens
    
    # ==================== 统计信息 ====================
    
    def get_stats(self) -> Dict:
        """获取词典统计信息"""
        return {
            'positive_words': len(self.positive_words),
            'negative_words': len(self.negative_words),
            'degree_words': len(self.degree_words),
            'negation_words': len(self.negation_words),
            'emoji': len(self.emoji_dict),
            'internet_slang': len(self.internet_dict),
            'abbreviations': len(self.abbreviation_dict),
            'domain_dicts': {k: len(v) for k, v in self.domain_dicts.items()},
            'total': (len(self.positive_words) + len(self.negative_words) + 
                     len(self.emoji_dict) + len(self.internet_dict) + 
                     len(self.abbreviation_dict) + 
                     sum(len(v) for v in self.domain_dicts.values()))
        }


# 全局词典实例
_dict_instance = None

def get_sentiment_dictionary() -> SentimentDictionary:
    """获取情感词典单例"""
    global _dict_instance
    if _dict_instance is None:
        _dict_instance = SentimentDictionary()
    return _dict_instance


def analyze_sentiment(text: str, domain: str = None) -> Dict:
    """便捷情感分析函数"""
    return get_sentiment_dictionary().analyze(text, domain)
