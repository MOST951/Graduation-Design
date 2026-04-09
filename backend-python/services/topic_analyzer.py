"""
热点话题分析模块
================

功能特性：
1. 主题建模 - LDA、NMF算法
2. 关键词提取 - TF-IDF、TextRank
3. 词云生成 - 支持自定义样式
4. 热度趋势 - 时间序列分析

使用示例:
    from backend.services.topic_analyzer import TopicAnalyzer
    
    analyzer = TopicAnalyzer()
    
    # 提取关键词
    keywords = analyzer.extract_keywords(texts)
    
    # 生成词云数据
    wordcloud_data = analyzer.generate_wordcloud(texts)
    
    # 主题建模
    topics = analyzer.topic_modeling(texts, n_topics=5)
"""

import os
import re
import json
import math
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import hashlib

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TopicAnalyzer')

# 尝试导入jieba
try:
    import jieba
    import jieba.analyse
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba未安装，关键词提取功能受限")

# 尝试导入sklearn
try:
    from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation, NMF
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("sklearn未安装，主题建模功能受限")

# 尝试导入numpy
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


# ==================== 配置类 ====================

@dataclass
class TopicConfig:
    """话题分析配置"""
    # 分词配置
    use_jieba: bool = True
    user_dict_path: str = ""
    
    # 关键词提取
    keyword_method: str = "tfidf"  # tfidf, textrank, both
    top_k_keywords: int = 20
    
    # 主题建模
    topic_method: str = "lda"  # lda, nmf
    n_topics: int = 5
    max_iter: int = 100
    
    # 词云配置
    wordcloud_max_words: int = 100
    wordcloud_min_font_size: int = 10
    wordcloud_max_font_size: int = 100
    
    # 停用词
    stopwords_path: str = ""
    custom_stopwords: List[str] = field(default_factory=list)


@dataclass
class KeywordResult:
    """关键词结果"""
    word: str
    weight: float
    frequency: int = 0
    method: str = ""


@dataclass
class TopicResult:
    """主题结果"""
    topic_id: int
    keywords: List[Tuple[str, float]]
    weight: float = 0.0
    label: str = ""


@dataclass
class TrendPoint:
    """趋势数据点"""
    time: str
    count: int
    keywords: List[str]
    sentiment_score: float = 0.0


# ==================== 停用词管理 ====================

class StopwordsManager:
    """停用词管理器"""
    
    # 默认停用词
    DEFAULT_STOPWORDS = {
        '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        '自己', '这', '那', '他', '她', '它', '们', '这个', '那个', '什么', '怎么',
        '可以', '没', '把', '让', '被', '给', '从', '向', '对', '为', '以', '及',
        '但', '而', '或', '如果', '因为', '所以', '虽然', '但是', '然后', '这样',
        '那样', '这么', '那么', '多', '少', '大', '小', '来', '去', '做', '想',
        '能', '还', '再', '又', '才', '已经', '正在', '一直', '一定', '可能',
        '应该', '必须', '需要', '希望', '觉得', '认为', '知道', '发现', '感觉',
        '真的', '其实', '确实', '当然', '肯定', '一样', '不同', '特别', '非常',
        '比较', '更', '最', '太', '挺', '蛮', '有点', '稍微', '略', '些',
        # 微博特有
        '转发', '微博', '评论', '赞', '回复', '分享', '关注', '粉丝',
        'http', 'https', 'www', 'com', 'cn', '网页', '链接',
    }
    
    def __init__(self, config: TopicConfig = None):
        self.config = config or TopicConfig()
        self.stopwords = set(self.DEFAULT_STOPWORDS)
        
        # 加载自定义停用词
        if self.config.stopwords_path and os.path.exists(self.config.stopwords_path):
            self._load_stopwords(self.config.stopwords_path)
        
        # 添加配置中的停用词
        self.stopwords.update(self.config.custom_stopwords)
    
    def _load_stopwords(self, path: str):
        """加载停用词文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip()
                    if word:
                        self.stopwords.add(word)
            logger.info(f"加载停用词: {path}")
        except Exception as e:
            logger.error(f"加载停用词失败: {e}")
    
    def is_stopword(self, word: str) -> bool:
        """判断是否为停用词"""
        return word in self.stopwords or len(word) < 2
    
    def filter_words(self, words: List[str]) -> List[str]:
        """过滤停用词"""
        return [w for w in words if not self.is_stopword(w)]
    
    def add_stopword(self, word: str):
        """添加停用词"""
        self.stopwords.add(word)
    
    def remove_stopword(self, word: str):
        """移除停用词"""
        self.stopwords.discard(word)


# ==================== 文本预处理 ====================

class TextPreprocessor:
    """文本预处理器"""
    
    # URL正则
    URL_PATTERN = re.compile(r'https?://\S+|www\.\S+')
    # @用户
    AT_PATTERN = re.compile(r'@[\w\u4e00-\u9fff]+')
    # #话题#
    TOPIC_PATTERN = re.compile(r'#([^#]+)#')
    # 表情
    EMOJI_PATTERN = re.compile(r'\[[\w\u4e00-\u9fff]+\]')
    # 特殊字符
    SPECIAL_PATTERN = re.compile(r'[^\w\u4e00-\u9fff\s]')
    
    def __init__(self, config: TopicConfig = None):
        self.config = config or TopicConfig()
        self.stopwords_manager = StopwordsManager(config)
        
        # 加载用户词典
        if JIEBA_AVAILABLE and self.config.user_dict_path:
            if os.path.exists(self.config.user_dict_path):
                jieba.load_userdict(self.config.user_dict_path)
    
    def clean_text(self, text: str) -> str:
        """清洗文本"""
        if not text:
            return ""
        
        # 移除URL
        text = self.URL_PATTERN.sub('', text)
        # 移除@用户
        text = self.AT_PATTERN.sub('', text)
        # 提取话题内容
        text = self.TOPIC_PATTERN.sub(r'\1', text)
        # 移除表情
        text = self.EMOJI_PATTERN.sub('', text)
        # 移除特殊字符
        text = self.SPECIAL_PATTERN.sub(' ', text)
        # 合并空格
        text = ' '.join(text.split())
        
        return text.strip()
    
    def tokenize(self, text: str) -> List[str]:
        """分词"""
        text = self.clean_text(text)
        
        if not text:
            return []
        
        if JIEBA_AVAILABLE and self.config.use_jieba:
            words = list(jieba.cut(text))
        else:
            # 简单按字符分割
            words = list(text)
        
        # 过滤停用词和短词
        words = self.stopwords_manager.filter_words(words)
        
        return words
    
    def extract_topics(self, text: str) -> List[str]:
        """提取话题标签"""
        return self.TOPIC_PATTERN.findall(text)


# ==================== 关键词提取 ====================

class KeywordExtractor:
    """关键词提取器"""
    
    def __init__(self, config: TopicConfig = None):
        self.config = config or TopicConfig()
        self.preprocessor = TextPreprocessor(config)
    
    def extract_tfidf(self, texts: List[str], top_k: int = None) -> List[KeywordResult]:
        """TF-IDF关键词提取"""
        top_k = top_k or self.config.top_k_keywords
        
        if JIEBA_AVAILABLE:
            # 使用jieba的TF-IDF
            combined_text = ' '.join(texts)
            keywords = jieba.analyse.extract_tags(
                combined_text, 
                topK=top_k, 
                withWeight=True
            )
            return [
                KeywordResult(word=w, weight=round(s, 4), method='tfidf')
                for w, s in keywords
            ]
        
        elif SKLEARN_AVAILABLE:
            # 使用sklearn的TF-IDF
            processed_texts = [' '.join(self.preprocessor.tokenize(t)) for t in texts]
            
            vectorizer = TfidfVectorizer(max_features=top_k * 2)
            tfidf_matrix = vectorizer.fit_transform(processed_texts)
            
            # 计算每个词的平均TF-IDF
            feature_names = vectorizer.get_feature_names_out()
            avg_tfidf = tfidf_matrix.mean(axis=0).A1
            
            # 排序
            sorted_indices = avg_tfidf.argsort()[::-1][:top_k]
            
            return [
                KeywordResult(
                    word=feature_names[i],
                    weight=round(avg_tfidf[i], 4),
                    method='tfidf'
                )
                for i in sorted_indices
            ]
        
        else:
            # 降级到词频统计
            return self.extract_frequency(texts, top_k)
    
    def extract_textrank(self, texts: List[str], top_k: int = None) -> List[KeywordResult]:
        """TextRank关键词提取"""
        top_k = top_k or self.config.top_k_keywords
        
        if JIEBA_AVAILABLE:
            combined_text = ' '.join(texts)
            keywords = jieba.analyse.textrank(
                combined_text,
                topK=top_k,
                withWeight=True
            )
            return [
                KeywordResult(word=w, weight=round(s, 4), method='textrank')
                for w, s in keywords
            ]
        else:
            # 降级到TF-IDF
            return self.extract_tfidf(texts, top_k)
    
    def extract_frequency(self, texts: List[str], top_k: int = None) -> List[KeywordResult]:
        """词频统计"""
        top_k = top_k or self.config.top_k_keywords
        
        word_counter = Counter()
        for text in texts:
            words = self.preprocessor.tokenize(text)
            word_counter.update(words)
        
        total = sum(word_counter.values())
        
        return [
            KeywordResult(
                word=word,
                weight=round(count / total, 4),
                frequency=count,
                method='frequency'
            )
            for word, count in word_counter.most_common(top_k)
        ]
    
    def extract(self, texts: List[str], method: str = None, 
                top_k: int = None) -> List[KeywordResult]:
        """提取关键词"""
        method = method or self.config.keyword_method
        
        if method == 'tfidf':
            return self.extract_tfidf(texts, top_k)
        elif method == 'textrank':
            return self.extract_textrank(texts, top_k)
        elif method == 'both':
            # 合并两种方法的结果
            tfidf_results = self.extract_tfidf(texts, top_k)
            textrank_results = self.extract_textrank(texts, top_k)
            
            # 合并并去重
            word_scores = {}
            for r in tfidf_results + textrank_results:
                if r.word in word_scores:
                    word_scores[r.word] = max(word_scores[r.word], r.weight)
                else:
                    word_scores[r.word] = r.weight
            
            sorted_words = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
            return [
                KeywordResult(word=w, weight=round(s, 4), method='combined')
                for w, s in sorted_words[:top_k or self.config.top_k_keywords]
            ]
        else:
            return self.extract_frequency(texts, top_k)


# ==================== 主题建模 ====================

class TopicModeler:
    """主题建模器"""
    
    def __init__(self, config: TopicConfig = None):
        self.config = config or TopicConfig()
        self.preprocessor = TextPreprocessor(config)
        self.vectorizer = None
        self.model = None
    
    def fit_lda(self, texts: List[str], n_topics: int = None) -> List[TopicResult]:
        """LDA主题建模"""
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn未安装，无法进行LDA建模")
            return self._fallback_topics(texts, n_topics)
        
        n_topics = n_topics or self.config.n_topics
        
        # 预处理
        processed_texts = [' '.join(self.preprocessor.tokenize(t)) for t in texts]
        
        # 构建词频矩阵
        self.vectorizer = CountVectorizer(max_features=1000, max_df=0.95, min_df=2)
        doc_term_matrix = self.vectorizer.fit_transform(processed_texts)
        
        # LDA建模
        self.model = LatentDirichletAllocation(
            n_components=n_topics,
            max_iter=self.config.max_iter,
            random_state=42
        )
        self.model.fit(doc_term_matrix)
        
        # 提取主题
        feature_names = self.vectorizer.get_feature_names_out()
        topics = []
        
        for topic_idx, topic in enumerate(self.model.components_):
            top_indices = topic.argsort()[:-11:-1]
            top_words = [(feature_names[i], round(topic[i], 4)) for i in top_indices]
            
            topics.append(TopicResult(
                topic_id=topic_idx,
                keywords=top_words,
                weight=round(topic.sum() / topic.sum(), 4),
                label=f"主题{topic_idx + 1}: {top_words[0][0]}"
            ))
        
        return topics
    
    def fit_nmf(self, texts: List[str], n_topics: int = None) -> List[TopicResult]:
        """NMF主题建模"""
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn未安装，无法进行NMF建模")
            return self._fallback_topics(texts, n_topics)
        
        n_topics = n_topics or self.config.n_topics
        
        # 预处理
        processed_texts = [' '.join(self.preprocessor.tokenize(t)) for t in texts]
        
        # 构建TF-IDF矩阵
        self.vectorizer = TfidfVectorizer(max_features=1000, max_df=0.95, min_df=2)
        tfidf_matrix = self.vectorizer.fit_transform(processed_texts)
        
        # NMF建模
        self.model = NMF(
            n_components=n_topics,
            max_iter=self.config.max_iter,
            random_state=42
        )
        self.model.fit(tfidf_matrix)
        
        # 提取主题
        feature_names = self.vectorizer.get_feature_names_out()
        topics = []
        
        for topic_idx, topic in enumerate(self.model.components_):
            top_indices = topic.argsort()[:-11:-1]
            top_words = [(feature_names[i], round(topic[i], 4)) for i in top_indices]
            
            topics.append(TopicResult(
                topic_id=topic_idx,
                keywords=top_words,
                weight=round(topic.sum(), 4),
                label=f"主题{topic_idx + 1}: {top_words[0][0]}"
            ))
        
        return topics
    
    def _fallback_topics(self, texts: List[str], n_topics: int = None) -> List[TopicResult]:
        """降级方案：基于词频聚类"""
        n_topics = n_topics or self.config.n_topics
        
        # 统计词频
        word_counter = Counter()
        for text in texts:
            words = self.preprocessor.tokenize(text)
            word_counter.update(words)
        
        # 取top词分成n组
        top_words = word_counter.most_common(n_topics * 10)
        words_per_topic = len(top_words) // n_topics
        
        topics = []
        for i in range(n_topics):
            start = i * words_per_topic
            end = start + words_per_topic
            topic_words = top_words[start:end]
            
            total = sum(c for _, c in topic_words)
            keywords = [(w, round(c / total, 4)) for w, c in topic_words[:10]]
            
            topics.append(TopicResult(
                topic_id=i,
                keywords=keywords,
                weight=round(1.0 / n_topics, 4),
                label=f"主题{i + 1}: {keywords[0][0] if keywords else '未知'}"
            ))
        
        return topics
    
    def fit(self, texts: List[str], method: str = None, 
            n_topics: int = None) -> List[TopicResult]:
        """主题建模"""
        method = method or self.config.topic_method
        
        if method == 'lda':
            return self.fit_lda(texts, n_topics)
        elif method == 'nmf':
            return self.fit_nmf(texts, n_topics)
        else:
            return self.fit_lda(texts, n_topics)


# ==================== 词云生成 ====================

class WordCloudGenerator:
    """词云生成器"""
    
    def __init__(self, config: TopicConfig = None):
        self.config = config or TopicConfig()
        self.keyword_extractor = KeywordExtractor(config)
    
    def generate(self, texts: List[str], max_words: int = None) -> List[Dict]:
        """
        生成词云数据
        
        Returns:
            词云数据列表，格式: [{'name': '词', 'value': 权重}, ...]
        """
        max_words = max_words or self.config.wordcloud_max_words
        
        # 提取关键词
        keywords = self.keyword_extractor.extract(texts, top_k=max_words)
        
        # 转换为词云格式
        wordcloud_data = []
        max_weight = max(k.weight for k in keywords) if keywords else 1
        
        for kw in keywords:
            # 归一化权重到字体大小范围
            normalized = kw.weight / max_weight
            font_size = int(
                self.config.wordcloud_min_font_size + 
                normalized * (self.config.wordcloud_max_font_size - self.config.wordcloud_min_font_size)
            )
            
            wordcloud_data.append({
                'name': kw.word,
                'value': round(kw.weight * 1000, 2),  # 放大便于显示
                'textStyle': {
                    'fontSize': font_size
                }
            })
        
        return wordcloud_data
    
    def generate_echarts_option(self, texts: List[str], 
                                max_words: int = None) -> Dict:
        """生成ECharts词云配置"""
        wordcloud_data = self.generate(texts, max_words)
        
        return {
            'tooltip': {
                'show': True
            },
            'series': [{
                'type': 'wordCloud',
                'shape': 'circle',
                'left': 'center',
                'top': 'center',
                'width': '90%',
                'height': '90%',
                'sizeRange': [
                    self.config.wordcloud_min_font_size,
                    self.config.wordcloud_max_font_size
                ],
                'rotationRange': [-45, 45],
                'rotationStep': 15,
                'gridSize': 8,
                'drawOutOfBound': False,
                'textStyle': {
                    'fontFamily': 'sans-serif',
                    'fontWeight': 'bold',
                    'color': 'function() { return "rgb(" + Math.round(Math.random() * 160) + "," + Math.round(Math.random() * 160) + "," + Math.round(Math.random() * 160) + ")"; }'
                },
                'emphasis': {
                    'textStyle': {
                        'shadowBlur': 10,
                        'shadowColor': '#333'
                    }
                },
                'data': wordcloud_data
            }]
        }


# ==================== 热度趋势分析 ====================

class TrendAnalyzer:
    """热度趋势分析器"""
    
    def __init__(self, config: TopicConfig = None):
        self.config = config or TopicConfig()
        self.keyword_extractor = KeywordExtractor(config)
    
    def analyze_trend(self, data: List[Dict], 
                      time_field: str = 'created_at',
                      text_field: str = 'text',
                      interval: str = 'hour') -> List[TrendPoint]:
        """
        分析热度趋势
        
        Args:
            data: 数据列表，包含时间和文本字段
            time_field: 时间字段名
            text_field: 文本字段名
            interval: 时间间隔 (hour/day)
            
        Returns:
            趋势数据点列表
        """
        # 按时间分组
        time_groups = defaultdict(list)
        
        for item in data:
            time_str = item.get(time_field, '')
            text = item.get(text_field, '')
            
            if not time_str or not text:
                continue
            
            try:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                if interval == 'hour':
                    key = dt.strftime('%Y-%m-%d %H:00')
                elif interval == 'day':
                    key = dt.strftime('%Y-%m-%d')
                else:
                    key = dt.strftime('%Y-%m-%d %H:00')
            except:
                continue
            
            time_groups[key].append({
                'text': text,
                'sentiment_score': item.get('sentiment_score', 0)
            })
        
        # 分析每个时间段
        trend_points = []
        
        for time_key in sorted(time_groups.keys()):
            items = time_groups[time_key]
            texts = [item['text'] for item in items]
            
            # 提取关键词
            keywords = self.keyword_extractor.extract(texts, top_k=5)
            keyword_names = [k.word for k in keywords]
            
            # 计算平均情感
            scores = [item['sentiment_score'] for item in items]
            avg_score = sum(scores) / len(scores) if scores else 0
            
            trend_points.append(TrendPoint(
                time=time_key,
                count=len(items),
                keywords=keyword_names,
                sentiment_score=round(avg_score, 4)
            ))
        
        return trend_points
    
    def detect_hotspots(self, trend_points: List[TrendPoint], 
                        threshold: float = 1.5) -> List[Dict]:
        """
        检测热点时段
        
        Args:
            trend_points: 趋势数据点
            threshold: 热点阈值（相对于平均值的倍数）
            
        Returns:
            热点列表
        """
        if not trend_points:
            return []
        
        counts = [p.count for p in trend_points]
        avg_count = sum(counts) / len(counts)
        
        hotspots = []
        for point in trend_points:
            if point.count > avg_count * threshold:
                hotspots.append({
                    'time': point.time,
                    'count': point.count,
                    'ratio': round(point.count / avg_count, 2),
                    'keywords': point.keywords,
                    'sentiment_score': point.sentiment_score
                })
        
        return hotspots


# ==================== 主分析器 ====================

class TopicAnalyzer:
    """
    热点话题分析器
    
    整合关键词提取、主题建模、词云生成、趋势分析
    """
    
    def __init__(self, config: TopicConfig = None):
        self.config = config or TopicConfig()
        self.preprocessor = TextPreprocessor(config)
        self.keyword_extractor = KeywordExtractor(config)
        self.topic_modeler = TopicModeler(config)
        self.wordcloud_generator = WordCloudGenerator(config)
        self.trend_analyzer = TrendAnalyzer(config)
    
    def extract_keywords(self, texts: List[str], 
                        method: str = None,
                        top_k: int = None) -> List[Dict]:
        """
        提取关键词
        
        Returns:
            关键词列表
        """
        results = self.keyword_extractor.extract(texts, method, top_k)
        return [asdict(r) for r in results]
    
    def topic_modeling(self, texts: List[str],
                      method: str = None,
                      n_topics: int = None) -> List[Dict]:
        """
        主题建模
        
        Returns:
            主题列表
        """
        results = self.topic_modeler.fit(texts, method, n_topics)
        return [asdict(r) for r in results]
    
    def generate_wordcloud(self, texts: List[str],
                          max_words: int = None) -> List[Dict]:
        """
        生成词云数据
        
        Returns:
            词云数据（ECharts格式）
        """
        return self.wordcloud_generator.generate(texts, max_words)
    
    def get_wordcloud_option(self, texts: List[str],
                            max_words: int = None) -> Dict:
        """
        获取ECharts词云配置
        
        Returns:
            ECharts option配置
        """
        return self.wordcloud_generator.generate_echarts_option(texts, max_words)
    
    def analyze_trend(self, data: List[Dict],
                     interval: str = 'hour') -> List[Dict]:
        """
        分析热度趋势
        
        Returns:
            趋势数据
        """
        results = self.trend_analyzer.analyze_trend(data, interval=interval)
        return [asdict(r) for r in results]
    
    def detect_hotspots(self, data: List[Dict],
                       interval: str = 'hour',
                       threshold: float = 1.5) -> List[Dict]:
        """
        检测热点
        
        Returns:
            热点列表
        """
        trend_points = self.trend_analyzer.analyze_trend(data, interval=interval)
        return self.trend_analyzer.detect_hotspots(trend_points, threshold)
    
    def full_analysis(self, texts: List[str], 
                     data: List[Dict] = None) -> Dict:
        """
        完整分析
        
        Returns:
            包含所有分析结果的字典
        """
        result = {
            'keywords': self.extract_keywords(texts),
            'topics': self.topic_modeling(texts),
            'wordcloud': self.generate_wordcloud(texts),
            'analysis_time': datetime.now().isoformat()
        }
        
        if data:
            result['trend'] = self.analyze_trend(data)
            result['hotspots'] = self.detect_hotspots(data)
        
        return result


# ==================== 便捷函数 ====================

_analyzer_instance = None

def get_topic_analyzer() -> TopicAnalyzer:
    """获取话题分析器单例"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = TopicAnalyzer()
    return _analyzer_instance


def extract_keywords(texts: List[str], top_k: int = 20) -> List[Dict]:
    """提取关键词"""
    return get_topic_analyzer().extract_keywords(texts, top_k=top_k)


def generate_wordcloud(texts: List[str], max_words: int = 100) -> List[Dict]:
    """生成词云"""
    return get_topic_analyzer().generate_wordcloud(texts, max_words)


def topic_modeling(texts: List[str], n_topics: int = 5) -> List[Dict]:
    """主题建模"""
    return get_topic_analyzer().topic_modeling(texts, n_topics=n_topics)


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    # 测试数据
    test_texts = [
        "今天天气真好，出去旅游心情很棒！",
        "这个景点太美了，强烈推荐大家来玩",
        "旅游途中遇到了很多有趣的人",
        "酒店服务态度很差，非常失望",
        "美食太好吃了，不虚此行",
        "景区人太多了，体验很差",
        "导游讲解很专业，学到了很多知识",
        "交通不太方便，建议自驾游",
        "风景如画，拍了很多美照",
        "价格有点贵，性价比一般",
    ]
    
    print("=" * 60)
    print("热点话题分析测试")
    print("=" * 60)
    
    analyzer = TopicAnalyzer()
    
    # 1. 关键词提取
    print("\n【关键词提取】")
    keywords = analyzer.extract_keywords(test_texts, top_k=10)
    for kw in keywords[:10]:
        print(f"  {kw['word']}: {kw['weight']:.4f}")
    
    # 2. 主题建模
    print("\n【主题建模】")
    topics = analyzer.topic_modeling(test_texts, n_topics=3)
    for topic in topics:
        print(f"  {topic['label']}")
        print(f"    关键词: {', '.join([w for w, _ in topic['keywords'][:5]])}")
    
    # 3. 词云数据
    print("\n【词云数据】")
    wordcloud = analyzer.generate_wordcloud(test_texts, max_words=20)
    for item in wordcloud[:5]:
        print(f"  {item['name']}: {item['value']}")
    
    # 4. 完整分析
    print("\n【完整分析】")
    full_result = analyzer.full_analysis(test_texts)
    print(f"  关键词数: {len(full_result['keywords'])}")
    print(f"  主题数: {len(full_result['topics'])}")
    print(f"  词云词数: {len(full_result['wordcloud'])}")
    print(f"  分析时间: {full_result['analysis_time']}")
