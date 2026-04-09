"""
基于词典规则的情感分析器
========================

功能特性：
1. 情感词匹配：精确匹配、模糊匹配、短语匹配
2. 情感强度计算：程度副词修饰、否定词反转、转折词调整
3. 情感极性判断：综合计算、上下文语境、矛盾情感处理
4. 表情符号处理：Unicode表情、微博表情、颜文字

使用示例:
    from backend.services.rule_based_analyzer import RuleBasedSentimentAnalyzer
    
    analyzer = RuleBasedSentimentAnalyzer()
    result = analyzer.analyze("这部电影真的太好看了！强烈推荐！😍")
    print(result)
    # {
    #     'score': 0.85,
    #     'polarity': 'positive',
    #     'label': '正面',
    #     'confidence': 0.92,
    #     'details': {...}
    # }
"""

import os
import re
import json
import logging
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict
from functools import lru_cache

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('RuleBasedAnalyzer')

# 尝试导入jieba
try:
    import jieba
    import jieba.posseg as pseg
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba未安装，将使用简单分词")


# ==================== 数据结构 ====================

@dataclass
class Token:
    """分词结果"""
    text: str
    pos: str = ''  # 词性
    start: int = 0  # 起始位置
    end: int = 0    # 结束位置


@dataclass
class SentimentMatch:
    """情感词匹配结果"""
    word: str
    position: int
    polarity: str  # positive/negative/neutral
    base_score: float
    adjusted_score: float = 0.0
    degree_modifier: float = 1.0
    negation_modifier: float = 1.0
    context_modifier: float = 1.0
    match_type: str = 'exact'  # exact/fuzzy/phrase


@dataclass
class AnalysisResult:
    """分析结果"""
    score: float
    polarity: str
    label: str
    confidence: float
    positive_score: float
    negative_score: float
    neutral_score: float
    matches: List[SentimentMatch]
    tokens: List[Token]
    emoji_sentiment: Dict
    details: Dict


# ==================== 同义词和短语词典 ====================

class SynonymDict:
    """同义词词典"""
    
    # 正面同义词组
    POSITIVE_SYNONYMS = {
        '好': ['棒', '赞', '优秀', '出色', '不错', '可以', '行', '中', '得'],
        '喜欢': ['爱', '钟爱', '热爱', '喜爱', '偏爱', '心水', '种草'],
        '开心': ['高兴', '快乐', '愉快', '欢乐', '欣喜', '喜悦', '乐'],
        '美': ['漂亮', '好看', '帅', '靓', '俊', '俏', '标致'],
        '厉害': ['牛', '强', '猛', '狠', '绝', '神', '秀'],
        '感动': ['动容', '触动', '感触', '感慨'],
        '满意': ['称心', '如意', '顺心', '舒心'],
    }
    
    # 负面同义词组
    NEGATIVE_SYNONYMS = {
        '差': ['烂', '糟', '坏', '次', '渣', '垃圾'],
        '讨厌': ['恨', '厌恶', '反感', '嫌弃', '鄙视'],
        '难过': ['伤心', '悲伤', '痛苦', '心痛', '难受'],
        '生气': ['愤怒', '恼火', '火大', '气愤', '恼怒'],
        '害怕': ['恐惧', '惊恐', '恐慌', '畏惧', '胆怯'],
        '失望': ['沮丧', '灰心', '心寒', '寒心'],
        '无聊': ['乏味', '无趣', '枯燥', '单调'],
    }
    
    def __init__(self):
        self._build_reverse_index()
    
    def _build_reverse_index(self):
        """构建反向索引"""
        self.positive_reverse = {}
        for key, synonyms in self.POSITIVE_SYNONYMS.items():
            self.positive_reverse[key] = key
            for syn in synonyms:
                self.positive_reverse[syn] = key
        
        self.negative_reverse = {}
        for key, synonyms in self.NEGATIVE_SYNONYMS.items():
            self.negative_reverse[key] = key
            for syn in synonyms:
                self.negative_reverse[syn] = key
    
    def get_canonical(self, word: str) -> Tuple[Optional[str], str]:
        """获取规范形式和极性"""
        if word in self.positive_reverse:
            return self.positive_reverse[word], 'positive'
        if word in self.negative_reverse:
            return self.negative_reverse[word], 'negative'
        return None, 'unknown'


class PhraseDict:
    """短语词典"""
    
    # 正面短语
    POSITIVE_PHRASES = {
        '太棒了': 0.9,
        '真不错': 0.7,
        '很好看': 0.7,
        '超级棒': 0.9,
        '非常好': 0.8,
        '特别好': 0.8,
        '好厉害': 0.8,
        '太厉害了': 0.9,
        '强烈推荐': 0.8,
        '值得一看': 0.7,
        '值得推荐': 0.7,
        '五星好评': 0.9,
        '满分推荐': 0.9,
        '爱了爱了': 0.9,
        '太可了': 0.8,
        '绝了绝了': 0.9,
        '笑死我了': 0.6,
        '太好笑了': 0.7,
        '感动哭了': 0.8,
        '泪目了': 0.7,
        '太感动了': 0.8,
        '暖心了': 0.8,
        '心动了': 0.7,
        '上头了': 0.7,
        '真香了': 0.8,
        '入坑了': 0.6,
        '种草了': 0.7,
        '安利给大家': 0.7,
        '必须点赞': 0.8,
        '给力啊': 0.8,
        '太给力了': 0.9,
    }
    
    # 负面短语
    NEGATIVE_PHRASES = {
        '太差了': 0.8,
        '真烂': 0.8,
        '很失望': 0.7,
        '非常差': 0.8,
        '特别差': 0.8,
        '太垃圾了': 0.9,
        '不推荐': 0.6,
        '不值得': 0.6,
        '一星差评': 0.9,
        '差评差评': 0.9,
        '无力吐槽': 0.7,
        '一言难尽': 0.6,
        '辣眼睛': 0.7,
        '毁三观': 0.8,
        '受不了': 0.7,
        '忍不了': 0.7,
        '太离谱了': 0.7,
        '离大谱': 0.7,
        '破大防': 0.7,
        '裂开了': 0.6,
        '麻了麻了': 0.6,
        'emo了': 0.6,
        '社死了': 0.7,
        '尴尬死了': 0.7,
        '无语死了': 0.7,
        '气死我了': 0.8,
        '恶心死了': 0.8,
        '烦死了': 0.7,
        '累死了': 0.6,
        '吐了吐了': 0.7,
        '踩雷了': 0.7,
        '翻车了': 0.7,
        '塌房了': 0.8,
    }
    
    # 否定短语（特殊处理）
    NEGATION_PHRASES = {
        '不好': ('negative', 0.6),
        '不行': ('negative', 0.6),
        '不喜欢': ('negative', 0.6),
        '不满意': ('negative', 0.6),
        '不开心': ('negative', 0.6),
        '不高兴': ('negative', 0.6),
        '不值得': ('negative', 0.6),
        '不推荐': ('negative', 0.6),
        '没意思': ('negative', 0.5),
        '没什么': ('neutral', 0.3),
        '还可以': ('positive', 0.4),
        '还不错': ('positive', 0.5),
        '还行吧': ('neutral', 0.3),
        '一般般': ('neutral', 0.3),
        '马马虎虎': ('neutral', 0.3),
    }
    
    def match(self, text: str) -> List[Tuple[str, str, float, int, int]]:
        """
        匹配短语
        
        Returns:
            [(短语, 极性, 强度, 起始位置, 结束位置), ...]
        """
        matches = []
        
        # 匹配正面短语
        for phrase, score in self.POSITIVE_PHRASES.items():
            start = 0
            while True:
                pos = text.find(phrase, start)
                if pos == -1:
                    break
                matches.append((phrase, 'positive', score, pos, pos + len(phrase)))
                start = pos + 1
        
        # 匹配负面短语
        for phrase, score in self.NEGATIVE_PHRASES.items():
            start = 0
            while True:
                pos = text.find(phrase, start)
                if pos == -1:
                    break
                matches.append((phrase, 'negative', score, pos, pos + len(phrase)))
                start = pos + 1
        
        # 匹配否定短语
        for phrase, (polarity, score) in self.NEGATION_PHRASES.items():
            start = 0
            while True:
                pos = text.find(phrase, start)
                if pos == -1:
                    break
                matches.append((phrase, polarity, score, pos, pos + len(phrase)))
                start = pos + 1
        
        # 按位置排序，去除重叠
        matches.sort(key=lambda x: (x[3], -len(x[0])))
        
        return matches


# ==================== 表情处理器 ====================

class EmojiProcessor:
    """表情符号处理器"""
    
    # Unicode表情情感映射
    UNICODE_EMOJI = {
        # 正面表情
        '😀': ('positive', 0.7), '😃': ('positive', 0.7), '😄': ('positive', 0.8),
        '😁': ('positive', 0.8), '😆': ('positive', 0.8), '😅': ('positive', 0.5),
        '🤣': ('positive', 0.8), '😂': ('positive', 0.7), '🙂': ('positive', 0.5),
        '😉': ('positive', 0.6), '😊': ('positive', 0.8), '😇': ('positive', 0.8),
        '🥰': ('positive', 0.9), '😍': ('positive', 0.9), '🤩': ('positive', 0.9),
        '😘': ('positive', 0.8), '😗': ('positive', 0.6), '😚': ('positive', 0.7),
        '😋': ('positive', 0.7), '😛': ('positive', 0.6), '😜': ('positive', 0.6),
        '🤗': ('positive', 0.8), '🤭': ('positive', 0.5), '😎': ('positive', 0.7),
        '🥳': ('positive', 0.8), '👍': ('positive', 0.8), '👏': ('positive', 0.8),
        '🙌': ('positive', 0.8), '💪': ('positive', 0.8), '❤️': ('positive', 0.9),
        '💕': ('positive', 0.9), '💖': ('positive', 0.9), '✨': ('positive', 0.6),
        '🎉': ('positive', 0.8), '🎊': ('positive', 0.8), '🌟': ('positive', 0.7),
        '⭐': ('positive', 0.6), '🔥': ('positive', 0.7), '💯': ('positive', 0.8),
        
        # 负面表情
        '😔': ('negative', 0.6), '😢': ('negative', 0.7), '😭': ('negative', 0.8),
        '😤': ('negative', 0.6), '😡': ('negative', 0.8), '😠': ('negative', 0.7),
        '🤬': ('negative', 0.9), '😱': ('negative', 0.8), '😨': ('negative', 0.7),
        '😰': ('negative', 0.7), '😥': ('negative', 0.6), '😓': ('negative', 0.5),
        '😩': ('negative', 0.7), '😫': ('negative', 0.7), '😖': ('negative', 0.6),
        '😣': ('negative', 0.6), '😞': ('negative', 0.7), '😒': ('negative', 0.5),
        '🙄': ('negative', 0.5), '😑': ('negative', 0.4), '😐': ('negative', 0.3),
        '👎': ('negative', 0.8), '💔': ('negative', 0.8), '😷': ('negative', 0.4),
        '🤢': ('negative', 0.7), '🤮': ('negative', 0.8), '💀': ('negative', 0.6),
        '☠️': ('negative', 0.7), '💩': ('negative', 0.6), '🖕': ('negative', 0.9),
        
        # 中性表情
        '🤔': ('neutral', 0.3), '😶': ('neutral', 0.2), '🙃': ('neutral', 0.3),
        '😴': ('neutral', 0.3), '🥱': ('neutral', 0.3), '🤐': ('neutral', 0.3),
    }
    
    # 微博文字表情
    WEIBO_EMOJI = {
        '[微笑]': ('positive', 0.6), '[可爱]': ('positive', 0.7),
        '[太开心]': ('positive', 0.8), '[鼓掌]': ('positive', 0.8),
        '[嘻嘻]': ('positive', 0.6), '[哈哈]': ('positive', 0.7),
        '[笑cry]': ('positive', 0.7), '[爱你]': ('positive', 0.9),
        '[亲亲]': ('positive', 0.8), '[心]': ('positive', 0.8),
        '[赞]': ('positive', 0.8), '[good]': ('positive', 0.7),
        '[给力]': ('positive', 0.8), '[威武]': ('positive', 0.7),
        '[鲜花]': ('positive', 0.7), '[蛋糕]': ('positive', 0.6),
        
        '[泪]': ('negative', 0.6), '[悲伤]': ('negative', 0.7),
        '[伤心]': ('negative', 0.7), '[失望]': ('negative', 0.7),
        '[委屈]': ('negative', 0.6), '[可怜]': ('negative', 0.6),
        '[怒]': ('negative', 0.7), '[抓狂]': ('negative', 0.7),
        '[怒骂]': ('negative', 0.8), '[鄙视]': ('negative', 0.7),
        '[吐]': ('negative', 0.6), '[衰]': ('negative', 0.6),
        '[骷髅]': ('negative', 0.5), '[弱]': ('negative', 0.6),
        
        '[思考]': ('neutral', 0.3), '[疑问]': ('neutral', 0.3),
        '[黑线]': ('neutral', 0.3), '[汗]': ('neutral', 0.3),
        '[挖鼻]': ('neutral', 0.2), '[围观]': ('neutral', 0.3),
    }
    
    # 颜文字
    KAOMOJI = {
        # 正面
        '(^_^)': ('positive', 0.7), '(^^)': ('positive', 0.6),
        '(*^_^*)': ('positive', 0.8), '(≧▽≦)': ('positive', 0.8),
        '(｡◕‿◕｡)': ('positive', 0.8), '(◕‿◕)': ('positive', 0.7),
        '(✿◠‿◠)': ('positive', 0.8), '(◠‿◠)': ('positive', 0.7),
        '(´▽`)': ('positive', 0.7), '(^o^)': ('positive', 0.7),
        '\\(^o^)/': ('positive', 0.8), '(๑>◡<๑)': ('positive', 0.8),
        '(｡♥‿♥｡)': ('positive', 0.9), '(♥ω♥)': ('positive', 0.9),
        'ヽ(✿ﾟ▽ﾟ)ノ': ('positive', 0.8), '(ノ´▽`)ノ': ('positive', 0.7),
        
        # 负面
        '(T_T)': ('negative', 0.7), '(;_;)': ('negative', 0.7),
        '(╥_╥)': ('negative', 0.7), '(ಥ_ಥ)': ('negative', 0.8),
        '(╯°□°)╯': ('negative', 0.7), '(ノಠ益ಠ)ノ': ('negative', 0.8),
        '(¬_¬)': ('negative', 0.5), '(-_-)': ('negative', 0.4),
        '(>_<)': ('negative', 0.6), '(×_×)': ('negative', 0.6),
        'orz': ('negative', 0.5), 'OTZ': ('negative', 0.5),
        '_(:з」∠)_': ('negative', 0.5), '(´;ω;`)': ('negative', 0.7),
        
        # 中性
        '(・_・)': ('neutral', 0.3), '(._.)': ('neutral', 0.3),
        '(°_°)': ('neutral', 0.3), '(・・)': ('neutral', 0.3),
    }
    
    def __init__(self):
        # 合并所有表情
        self.all_emoji = {}
        self.all_emoji.update(self.UNICODE_EMOJI)
        self.all_emoji.update(self.WEIBO_EMOJI)
        self.all_emoji.update(self.KAOMOJI)
        
        # 构建正则模式
        self._build_patterns()
    
    def _build_patterns(self):
        """构建匹配模式"""
        # Unicode表情模式
        self.unicode_pattern = re.compile(
            r'[\U0001F600-\U0001F64F'  # 表情符号
            r'\U0001F300-\U0001F5FF'   # 符号和象形文字
            r'\U0001F680-\U0001F6FF'   # 交通和地图
            r'\U0001F1E0-\U0001F1FF'   # 旗帜
            r'\U00002702-\U000027B0'   # 装饰符号
            r'\U0001F900-\U0001F9FF'   # 补充符号
            r'\U00002600-\U000026FF'   # 杂项符号
            r']+', re.UNICODE
        )
        
        # 微博表情模式
        self.weibo_pattern = re.compile(r'\[[^\[\]]+\]')
    
    def extract_emoji(self, text: str) -> List[Tuple[str, str, float, int]]:
        """
        提取表情符号
        
        Returns:
            [(表情, 极性, 强度, 位置), ...]
        """
        results = []
        
        # 提取Unicode表情
        for match in self.unicode_pattern.finditer(text):
            emoji = match.group()
            for char in emoji:
                if char in self.all_emoji:
                    polarity, score = self.all_emoji[char]
                    results.append((char, polarity, score, match.start()))
        
        # 提取微博表情
        for match in self.weibo_pattern.finditer(text):
            emoji = match.group()
            if emoji in self.all_emoji:
                polarity, score = self.all_emoji[emoji]
                results.append((emoji, polarity, score, match.start()))
        
        # 提取颜文字
        for kaomoji, (polarity, score) in self.KAOMOJI.items():
            pos = text.find(kaomoji)
            if pos != -1:
                results.append((kaomoji, polarity, score, pos))
        
        return results
    
    def calculate_emoji_sentiment(self, text: str) -> Dict:
        """计算表情情感"""
        emojis = self.extract_emoji(text)
        
        if not emojis:
            return {
                'score': 0.0,
                'polarity': 'neutral',
                'count': 0,
                'emojis': []
            }
        
        positive_score = 0.0
        negative_score = 0.0
        
        for emoji, polarity, score, pos in emojis:
            if polarity == 'positive':
                positive_score += score
            elif polarity == 'negative':
                negative_score += score
        
        total_score = positive_score - negative_score
        count = len(emojis)
        
        if count > 0:
            normalized_score = total_score / count
        else:
            normalized_score = 0.0
        
        if normalized_score > 0.1:
            polarity = 'positive'
        elif normalized_score < -0.1:
            polarity = 'negative'
        else:
            polarity = 'neutral'
        
        return {
            'score': normalized_score,
            'polarity': polarity,
            'count': count,
            'emojis': emojis
        }


# ==================== 主分析器类 ====================

class RuleBasedSentimentAnalyzer:
    """
    基于词典规则的情感分析器
    
    特性：
    - 精确匹配和模糊匹配
    - 短语匹配
    - 程度副词修饰
    - 否定词反转
    - 转折词调整
    - 表情符号处理
    """
    
    def __init__(self, dict_path: str = None):
        """
        初始化分析器
        
        Args:
            dict_path: 词典路径
        """
        # 加载词典
        self._load_dictionaries(dict_path)
        
        # 初始化辅助组件
        self.synonym_dict = SynonymDict()
        self.phrase_dict = PhraseDict()
        self.emoji_processor = EmojiProcessor()
        
        # 配置参数
        self.config = {
            'negation_window': 3,      # 否定词影响窗口
            'degree_window': 2,        # 程度词影响窗口
            'transition_weight': 1.2,  # 转折词权重
            'emoji_weight': 0.8,       # 表情权重
            'phrase_weight': 1.2,      # 短语权重
        }
        
        logger.info("RuleBasedSentimentAnalyzer初始化完成")
    
    def _load_dictionaries(self, dict_path: str = None):
        """加载情感词典"""
        # 尝试从sentiment_dict模块加载
        try:
            from ..resources.sentiment_dict import SentimentDictionary
            self.dict_manager = SentimentDictionary()
            self._use_dict_manager = True
            logger.info("使用SentimentDictionary加载词典")
            return
        except ImportError:
            pass
        
        self._use_dict_manager = False
        
        # 内置基础词典
        self.positive_dict = {
            '好': 0.6, '棒': 0.7, '赞': 0.7, '优秀': 0.8, '喜欢': 0.7,
            '爱': 0.8, '开心': 0.7, '高兴': 0.7, '快乐': 0.8, '幸福': 0.9,
            '美好': 0.8, '精彩': 0.8, '厉害': 0.7, '牛': 0.7, '强': 0.6,
            '帅': 0.7, '美': 0.7, '漂亮': 0.7, '可爱': 0.7, '温暖': 0.7,
            '感动': 0.8, '支持': 0.6, '期待': 0.6, '希望': 0.6, '成功': 0.8,
            '胜利': 0.8, '加油': 0.7, '努力': 0.6, '进步': 0.7, '满意': 0.7,
            '舒服': 0.7, '享受': 0.7, '惊喜': 0.8, '感谢': 0.7, '祝福': 0.7,
            '恭喜': 0.7, '点赞': 0.6, '推荐': 0.6, '值得': 0.6, '完美': 0.9,
            '出色': 0.8, '杰出': 0.8, '卓越': 0.9, '一流': 0.8, '顶级': 0.9,
            'yyds': 0.9, '绝绝子': 0.9, '无敌': 0.9, '封神': 0.9, '神仙': 0.9,
            '宝藏': 0.8, '惊艳': 0.8, '炸裂': 0.8, '给力': 0.8, '真香': 0.8,
        }
        
        self.negative_dict = {
            '差': 0.6, '烂': 0.7, '垃圾': 0.8, '讨厌': 0.7, '恨': 0.8,
            '愤怒': 0.8, '生气': 0.7, '难过': 0.7, '伤心': 0.7, '失望': 0.7,
            '糟糕': 0.7, '恶心': 0.8, '无语': 0.6, '崩溃': 0.8, '绝望': 0.9,
            '痛苦': 0.8, '悲伤': 0.8, '郁闷': 0.7, '烦躁': 0.7, '烦': 0.6,
            '可怕': 0.7, '恐怖': 0.8, '害怕': 0.7, '担心': 0.6, '焦虑': 0.7,
            '累': 0.5, '疲惫': 0.6, '失败': 0.7, '问题': 0.5, '错误': 0.6,
            '骗': 0.8, '假': 0.7, '坑': 0.7, '傻': 0.7, '蠢': 0.7,
            '破防': 0.6, 'emo': 0.6, '裂开': 0.6, '麻了': 0.6, '社死': 0.7,
            '尴尬': 0.5, '离谱': 0.6, '翻车': 0.6, '塌房': 0.7, '踩雷': 0.7,
        }
        
        self.degree_dict = {
            '极其': 2.8, '极度': 2.8, '极为': 2.7, '万分': 2.8, '无比': 2.8,
            '非常': 2.0, '特别': 2.0, '超级': 2.2, '超': 2.0, '巨': 2.0,
            '很': 1.5, '太': 1.8, '真': 1.5, '好': 1.3, '挺': 1.3,
            '蛮': 1.3, '相当': 1.6, '十分': 1.8, '格外': 1.6, '尤其': 1.6,
            '比较': 1.2, '较': 1.2, '颇': 1.3, '实在': 1.3, '确实': 1.3,
            '有点': 0.7, '有些': 0.7, '稍微': 0.7, '略': 0.7, '些': 0.8,
        }
        
        self.negation_dict = {
            '不': 1.0, '不是': 1.0, '不会': 1.0, '不能': 1.0, '不要': 1.0,
            '没': 1.0, '没有': 1.0, '无': 1.0, '无法': 1.0, '未': 1.0,
            '别': 1.0, '莫': 1.0, '勿': 1.0, '非': 1.0, '并非': 1.0,
            '从不': 1.0, '从未': 1.0, '绝不': 1.0, '决不': 1.0, '毫不': 1.0,
            '不太': 0.7, '不很': 0.7, '不大': 0.7, '不怎么': 0.6,
        }
        
        self.transition_words = {
            '但': 1.2, '但是': 1.2, '可是': 1.2, '然而': 1.2, '却': 1.2,
            '不过': 1.1, '只是': 1.0, '虽然': 0.8, '尽管': 0.8,
        }
    
    def tokenize(self, text: str) -> List[Token]:
        """
        分词
        
        Args:
            text: 输入文本
            
        Returns:
            Token列表
        """
        tokens = []
        
        if JIEBA_AVAILABLE:
            # 使用jieba分词
            words = pseg.cut(text)
            pos = 0
            for word, flag in words:
                start = text.find(word, pos)
                if start == -1:
                    start = pos
                end = start + len(word)
                tokens.append(Token(
                    text=word,
                    pos=flag,
                    start=start,
                    end=end
                ))
                pos = end
        else:
            # 简单分词
            current_word = ''
            start = 0
            
            for i, char in enumerate(text):
                if '\u4e00' <= char <= '\u9fff':  # 中文
                    current_word += char
                else:
                    if current_word:
                        tokens.append(Token(
                            text=current_word,
                            start=start,
                            end=i
                        ))
                        current_word = ''
                    if char.strip():
                        tokens.append(Token(
                            text=char,
                            start=i,
                            end=i + 1
                        ))
                    start = i + 1
            
            if current_word:
                tokens.append(Token(
                    text=current_word,
                    start=start,
                    end=len(text)
                ))
        
        return tokens
    
    def match_sentiment_words(self, tokens: List[Token], text: str) -> List[SentimentMatch]:
        """
        匹配情感词
        
        Args:
            tokens: 分词结果
            text: 原始文本
            
        Returns:
            SentimentMatch列表
        """
        matches = []
        matched_positions = set()
        
        # 1. 短语匹配（优先级最高）
        phrase_matches = self.phrase_dict.match(text)
        for phrase, polarity, score, start, end in phrase_matches:
            matches.append(SentimentMatch(
                word=phrase,
                position=start,
                polarity=polarity,
                base_score=score,
                adjusted_score=score * self.config['phrase_weight'],
                match_type='phrase'
            ))
            # 标记已匹配位置
            for pos in range(start, end):
                matched_positions.add(pos)
        
        # 2. 精确匹配
        for i, token in enumerate(tokens):
            # 跳过已被短语匹配的位置
            if token.start in matched_positions:
                continue
            
            word = token.text
            
            # 使用词典管理器
            if self._use_dict_manager:
                entry = self.dict_manager.lookup(word)
                if entry:
                    matches.append(SentimentMatch(
                        word=word,
                        position=i,
                        polarity=entry.polarity,
                        base_score=entry.intensity,
                        adjusted_score=entry.intensity,
                        match_type='exact'
                    ))
                    continue
            
            # 使用内置词典
            if word in self.positive_dict:
                matches.append(SentimentMatch(
                    word=word,
                    position=i,
                    polarity='positive',
                    base_score=self.positive_dict[word],
                    adjusted_score=self.positive_dict[word],
                    match_type='exact'
                ))
            elif word in self.negative_dict:
                matches.append(SentimentMatch(
                    word=word,
                    position=i,
                    polarity='negative',
                    base_score=self.negative_dict[word],
                    adjusted_score=self.negative_dict[word],
                    match_type='exact'
                ))
            else:
                # 3. 模糊匹配（同义词）
                canonical, polarity = self.synonym_dict.get_canonical(word)
                if canonical:
                    if polarity == 'positive' and canonical in self.positive_dict:
                        score = self.positive_dict[canonical] * 0.9  # 同义词略降权
                    elif polarity == 'negative' and canonical in self.negative_dict:
                        score = self.negative_dict[canonical] * 0.9
                    else:
                        score = 0.5
                    
                    matches.append(SentimentMatch(
                        word=word,
                        position=i,
                        polarity=polarity,
                        base_score=score,
                        adjusted_score=score,
                        match_type='fuzzy'
                    ))
        
        return matches
    
    def apply_degree_modifiers(self, matches: List[SentimentMatch], 
                               tokens: List[Token]) -> List[SentimentMatch]:
        """
        应用程度副词修饰
        
        Args:
            matches: 情感词匹配结果
            tokens: 分词结果
            
        Returns:
            修饰后的匹配结果
        """
        # 获取程度词典
        if self._use_dict_manager:
            degree_dict = {w: d.coefficient for w, d in self.dict_manager.degree_words.items()}
        else:
            degree_dict = self.degree_dict
        
        # 找出所有程度词位置
        degree_positions = {}
        for i, token in enumerate(tokens):
            if token.text in degree_dict:
                degree_positions[i] = degree_dict[token.text]
        
        # 应用程度修饰
        window = self.config['degree_window']
        for match in matches:
            if match.match_type == 'phrase':
                continue  # 短语不受程度词影响
            
            pos = match.position
            modifier = 1.0
            
            # 查找前面的程度词
            for i in range(max(0, pos - window), pos):
                if i in degree_positions:
                    modifier *= degree_positions[i]
            
            match.degree_modifier = modifier
            match.adjusted_score = match.base_score * modifier
        
        return matches
    
    def apply_negations(self, matches: List[SentimentMatch], 
                        tokens: List[Token]) -> List[SentimentMatch]:
        """
        应用否定词反转
        
        Args:
            matches: 情感词匹配结果
            tokens: 分词结果
            
        Returns:
            处理后的匹配结果
        """
        # 获取否定词典
        if self._use_dict_manager:
            negation_dict = {w: n.strength for w, n in self.dict_manager.negation_words.items()}
        else:
            negation_dict = self.negation_dict
        
        # 找出所有否定词位置
        negation_positions = {}
        for i, token in enumerate(tokens):
            if token.text in negation_dict:
                negation_positions[i] = negation_dict[token.text]
        
        # 应用否定
        window = self.config['negation_window']
        for match in matches:
            if match.match_type == 'phrase':
                continue  # 短语已处理否定
            
            pos = match.position
            negation_count = 0
            
            # 查找前面的否定词
            for i in range(max(0, pos - window), pos):
                if i in negation_positions:
                    negation_count += 1
            
            # 奇数个否定词反转极性
            if negation_count % 2 == 1:
                match.negation_modifier = -1.0
                match.adjusted_score *= -1
                # 反转极性
                if match.polarity == 'positive':
                    match.polarity = 'negative'
                elif match.polarity == 'negative':
                    match.polarity = 'positive'
        
        return matches
    
    def apply_transitions(self, matches: List[SentimentMatch], 
                          tokens: List[Token]) -> List[SentimentMatch]:
        """
        应用转折词调整
        
        转折词后的情感词权重增加
        
        Args:
            matches: 情感词匹配结果
            tokens: 分词结果
            
        Returns:
            调整后的匹配结果
        """
        # 找出转折词位置
        transition_positions = []
        for i, token in enumerate(tokens):
            if token.text in self.transition_words:
                transition_positions.append(i)
        
        if not transition_positions:
            return matches
        
        # 转折词后的情感词权重增加
        weight = self.config['transition_weight']
        for match in matches:
            pos = match.position
            
            # 检查是否在转折词之后
            for trans_pos in transition_positions:
                if pos > trans_pos:
                    match.context_modifier = weight
                    match.adjusted_score *= weight
                    break
        
        return matches
    
    def aggregate_scores(self, matches: List[SentimentMatch], 
                         emoji_sentiment: Dict) -> Tuple[float, float, float]:
        """
        聚合情感得分
        
        Args:
            matches: 情感词匹配结果
            emoji_sentiment: 表情情感结果
            
        Returns:
            (正面得分, 负面得分, 中性得分)
        """
        positive_score = 0.0
        negative_score = 0.0
        neutral_score = 0.0
        
        # 聚合词语情感
        for match in matches:
            if match.polarity == 'positive':
                positive_score += abs(match.adjusted_score)
            elif match.polarity == 'negative':
                negative_score += abs(match.adjusted_score)
            else:
                neutral_score += abs(match.adjusted_score)
        
        # 聚合表情情感
        emoji_weight = self.config['emoji_weight']
        if emoji_sentiment['count'] > 0:
            for emoji, polarity, score, pos in emoji_sentiment['emojis']:
                if polarity == 'positive':
                    positive_score += score * emoji_weight
                elif polarity == 'negative':
                    negative_score += score * emoji_weight
                else:
                    neutral_score += score * emoji_weight
        
        return positive_score, negative_score, neutral_score
    
    def determine_polarity(self, positive_score: float, 
                           negative_score: float,
                           neutral_score: float) -> Tuple[str, str, float]:
        """
        确定情感极性
        
        Args:
            positive_score: 正面得分
            negative_score: 负面得分
            neutral_score: 中性得分
            
        Returns:
            (极性, 标签, 归一化得分)
        """
        total = positive_score + negative_score + neutral_score
        
        if total == 0:
            return 'neutral', '中性', 0.0
        
        # 计算净得分
        net_score = positive_score - negative_score
        
        # 归一化到 [-1, 1]
        max_score = max(positive_score, negative_score, 0.001)
        normalized_score = net_score / (total + 0.001)
        normalized_score = max(-1.0, min(1.0, normalized_score))
        
        # 确定极性和标签
        if normalized_score >= 0.6:
            return 'positive', '强烈正面', normalized_score
        elif normalized_score >= 0.2:
            return 'positive', '正面', normalized_score
        elif normalized_score <= -0.6:
            return 'negative', '强烈负面', normalized_score
        elif normalized_score <= -0.2:
            return 'negative', '负面', normalized_score
        else:
            return 'neutral', '中性', normalized_score
    
    def calculate_confidence(self, matches: List[SentimentMatch], 
                             emoji_sentiment: Dict,
                             text_length: int) -> float:
        """
        计算置信度
        
        Args:
            matches: 情感词匹配结果
            emoji_sentiment: 表情情感结果
            text_length: 文本长度
            
        Returns:
            置信度 (0-1)
        """
        if text_length == 0:
            return 0.0
        
        # 基于匹配数量
        match_count = len(matches) + emoji_sentiment['count']
        
        if match_count == 0:
            return 0.1
        
        # 匹配覆盖率
        coverage = min(1.0, match_count / (text_length / 5))
        
        # 匹配一致性
        polarities = [m.polarity for m in matches]
        if emoji_sentiment['count'] > 0:
            polarities.append(emoji_sentiment['polarity'])
        
        if not polarities:
            consistency = 0.5
        else:
            positive_count = polarities.count('positive')
            negative_count = polarities.count('negative')
            total = len(polarities)
            
            if positive_count > negative_count:
                consistency = positive_count / total
            elif negative_count > positive_count:
                consistency = negative_count / total
            else:
                consistency = 0.5
        
        # 综合置信度
        confidence = 0.3 + 0.4 * coverage + 0.3 * consistency
        
        return min(1.0, confidence)
    
    def analyze(self, text: str) -> Dict:
        """
        分析文本情感
        
        Args:
            text: 输入文本
            
        Returns:
            分析结果字典
        """
        if not text or len(text.strip()) < 1:
            return {
                'score': 0.0,
                'polarity': 'neutral',
                'label': '中性',
                'confidence': 0.0,
                'positive_score': 0.0,
                'negative_score': 0.0,
                'neutral_score': 0.0,
                'matches': [],
                'emoji_sentiment': {'score': 0, 'polarity': 'neutral', 'count': 0, 'emojis': []},
                'details': {}
            }
        
        # 1. 分词
        tokens = self.tokenize(text)
        
        # 2. 表情处理
        emoji_sentiment = self.emoji_processor.calculate_emoji_sentiment(text)
        
        # 3. 情感词匹配
        matches = self.match_sentiment_words(tokens, text)
        
        # 4. 程度词修饰
        matches = self.apply_degree_modifiers(matches, tokens)
        
        # 5. 否定词处理
        matches = self.apply_negations(matches, tokens)
        
        # 6. 转折词调整
        matches = self.apply_transitions(matches, tokens)
        
        # 7. 聚合得分
        positive_score, negative_score, neutral_score = self.aggregate_scores(
            matches, emoji_sentiment
        )
        
        # 8. 确定极性
        polarity, label, score = self.determine_polarity(
            positive_score, negative_score, neutral_score
        )
        
        # 9. 计算置信度
        confidence = self.calculate_confidence(matches, emoji_sentiment, len(text))
        
        # 构建结果
        result = {
            'score': round(score, 4),
            'polarity': polarity,
            'label': label,
            'confidence': round(confidence, 4),
            'positive_score': round(positive_score, 4),
            'negative_score': round(negative_score, 4),
            'neutral_score': round(neutral_score, 4),
            'matches': [
                {
                    'word': m.word,
                    'position': m.position,
                    'polarity': m.polarity,
                    'base_score': m.base_score,
                    'adjusted_score': m.adjusted_score,
                    'degree_modifier': m.degree_modifier,
                    'negation_modifier': m.negation_modifier,
                    'match_type': m.match_type
                }
                for m in matches
            ],
            'emoji_sentiment': emoji_sentiment,
            'details': {
                'token_count': len(tokens),
                'match_count': len(matches),
                'emoji_count': emoji_sentiment['count']
            }
        }
        
        return result
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """
        批量分析
        
        Args:
            texts: 文本列表
            
        Returns:
            分析结果列表
        """
        return [self.analyze(text) for text in texts]
    
    def get_sentiment_words(self, text: str) -> Dict[str, List[str]]:
        """
        提取情感词
        
        Args:
            text: 输入文本
            
        Returns:
            {'positive': [...], 'negative': [...], 'neutral': [...]}
        """
        result = self.analyze(text)
        
        words = {'positive': [], 'negative': [], 'neutral': []}
        
        for match in result['matches']:
            words[match['polarity']].append(match['word'])
        
        return words


# ==================== 便捷函数 ====================

_analyzer_instance = None

def get_analyzer() -> RuleBasedSentimentAnalyzer:
    """获取分析器单例"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = RuleBasedSentimentAnalyzer()
    return _analyzer_instance


def analyze_sentiment(text: str) -> Dict:
    """便捷情感分析函数"""
    return get_analyzer().analyze(text)


def analyze_batch(texts: List[str]) -> List[Dict]:
    """批量情感分析"""
    return get_analyzer().analyze_batch(texts)


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    import sys
    
    analyzer = RuleBasedSentimentAnalyzer()
    
    # 测试用例
    test_texts = [
        "这部电影真的太好看了！强烈推荐！😍",
        "服务态度太差了，非常失望",
        "还可以吧，一般般",
        "虽然有点贵，但是质量真的很好",
        "不是很喜欢，感觉不太行",
        "yyds！绝绝子！太可了！",
        "破防了😭裂开了麻了",
        "这个产品不好用，但是客服态度很好",
        "哈哈哈笑死我了太好笑了🤣",
        "无语😑一言难尽",
    ]
    
    print("=" * 60)
    print("基于词典规则的情感分析测试")
    print("=" * 60)
    
    for text in test_texts:
        result = analyzer.analyze(text)
        print(f"\n文本: {text}")
        print(f"极性: {result['polarity']} ({result['label']})")
        print(f"得分: {result['score']:.4f}")
        print(f"置信度: {result['confidence']:.4f}")
        print(f"正面/负面/中性: {result['positive_score']:.2f}/{result['negative_score']:.2f}/{result['neutral_score']:.2f}")
        if result['matches']:
            words = [f"{m['word']}({m['polarity'][0]})" for m in result['matches'][:5]]
            print(f"匹配词: {', '.join(words)}")
        print("-" * 40)
