"""
微博数据采集与清洗模块 - 完整数据处理流水线
============================================

实现功能：
1. 多源数据采集（热搜、关键词、话题、用户）
2. 数据清洗与去重
3. 文本预处理与分词
4. 情感分析标注
5. 数据持久化存储

技术特点：
- 异步并发采集
- 增量去重机制
- 多级缓存
- 断点续爬

作者：毕业设计
"""

import os
import sys
import json
import time
import hashlib
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Generator, Any, Set
from dataclasses import dataclass, field, asdict
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DataPipeline')

# 导入爬虫模块
try:
    from crawler.weibo_crawler import WeiboCrawler, WeiboCrawlerTask
    CRAWLER_AVAILABLE = True
except ImportError:
    CRAWLER_AVAILABLE = False
    logger.warning("爬虫模块不可用")

# 导入情感分析模块
try:
    from spark.sentiment_analyzer import SentimentLexicon
    LEXICON_AVAILABLE = True
except ImportError:
    LEXICON_AVAILABLE = False

try:
    from services.hybrid_analyzer import HybridSentimentAnalyzer
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False


# ==================== 配置类 ====================

@dataclass
class PipelineConfig:
    """数据流水线配置"""
    # 采集配置
    max_workers: int = 3                    # 并发采集线程数
    request_interval: float = 2.0           # 请求间隔（秒）
    retry_times: int = 3                    # 重试次数
    timeout: int = 10                       # 请求超时（秒）
    
    # 采集数量
    hot_search_count: int = 50              # 热搜数量
    weibo_per_keyword: int = 100            # 每个关键词采集微博数
    pages_per_keyword: int = 5              # 每个关键词页数
    
    # 清洗配置
    remove_duplicates: bool = True          # 去重
    remove_urls: bool = True                # 移除URL
    remove_mentions: bool = True            # 移除@用户
    remove_hashtags: bool = False           # 移除话题标签
    remove_emojis: bool = False             # 移除表情
    min_text_length: int = 5                # 最小文本长度
    max_text_length: int = 500              # 最大文本长度
    
    # 分析配置
    enable_sentiment: bool = True           # 启用情感分析
    sentiment_method: str = 'hybrid'        # lexicon/bert/hybrid
    
    # 存储配置
    data_dir: str = './data'                # 数据目录
    save_raw: bool = True                   # 保存原始数据
    save_processed: bool = True             # 保存处理后数据
    
    # 缓存配置
    enable_cache: bool = True               # 启用缓存
    cache_ttl: int = 3600                   # 缓存有效期（秒）


@dataclass
class ProcessedWeibo:
    """处理后的微博数据"""
    id: str
    mid: str
    text_raw: str                           # 原始文本
    text_clean: str                         # 清洗后文本
    words: List[str]                        # 分词结果
    
    # 用户信息
    user_id: str
    user_name: str
    user_followers: int
    user_verified: bool
    
    # 互动数据
    reposts_count: int
    comments_count: int
    attitudes_count: int
    
    # 时间信息
    created_at: str
    crawl_time: str
    
    # 情感分析结果
    sentiment: str = 'neutral'              # positive/neutral/negative
    sentiment_score: float = 0.0            # [-1, 1]
    sentiment_confidence: float = 0.0       # [0, 1]
    
    # 元信息
    keyword: str = ''
    source: str = 'weibo'
    data_hash: str = ''                     # 数据指纹（用于去重）


# ==================== 数据清洗器 ====================

class DataCleaner:
    """
    数据清洗器
    
    功能：
    1. 文本清洗（URL、@、表情等）
    2. 去重（基于内容指纹）
    3. 文本规范化
    4. 长度过滤
    """
    
    # 清洗正则表达式
    URL_PATTERN = re.compile(r'http[s]?://\S+|www\.\S+')
    MENTION_PATTERN = re.compile(r'@[\w\u4e00-\u9fff]+')
    HASHTAG_PATTERN = re.compile(r'#[^#]+#')
    EMOJI_PATTERN = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # 表情
        u"\U0001F300-\U0001F5FF"  # 符号和象形文字
        u"\U0001F680-\U0001F6FF"  # 交通和地图
        u"\U0001F1E0-\U0001F1FF"  # 旗帜
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        "]+", 
        flags=re.UNICODE
    )
    HTML_PATTERN = re.compile(r'<[^>]+>')
    SPACE_PATTERN = re.compile(r'\s+')
    SPECIAL_PATTERN = re.compile(r'[【】「」『』（）\[\]]+')
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self._seen_hashes: Set[str] = set()
        self._lock = threading.Lock()
    
    def clean_text(self, text: str) -> str:
        """清洗文本"""
        if not text:
            return ''
        
        # 移除HTML标签
        text = self.HTML_PATTERN.sub('', text)
        
        # 按配置清洗
        if self.config.remove_urls:
            text = self.URL_PATTERN.sub('', text)
        
        if self.config.remove_mentions:
            text = self.MENTION_PATTERN.sub('', text)
        
        if self.config.remove_hashtags:
            text = self.HASHTAG_PATTERN.sub('', text)
        
        if self.config.remove_emojis:
            text = self.EMOJI_PATTERN.sub('', text)
        
        # 移除特殊符号
        text = self.SPECIAL_PATTERN.sub('', text)
        
        # 规范化空白
        text = self.SPACE_PATTERN.sub(' ', text).strip()
        
        return text
    
    def compute_hash(self, text: str) -> str:
        """计算文本指纹"""
        # 移除所有空白和标点进行指纹计算
        normalized = re.sub(r'[\s\W]+', '', text.lower())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def is_duplicate(self, text: str) -> bool:
        """检查是否重复"""
        if not self.config.remove_duplicates:
            return False
        
        text_hash = self.compute_hash(text)
        
        with self._lock:
            if text_hash in self._seen_hashes:
                return True
            self._seen_hashes.add(text_hash)
            return False
    
    def is_valid_length(self, text: str) -> bool:
        """检查长度是否有效"""
        length = len(text)
        return self.config.min_text_length <= length <= self.config.max_text_length
    
    def clean_and_validate(self, text: str) -> Optional[str]:
        """清洗并验证文本"""
        # 清洗
        cleaned = self.clean_text(text)
        
        # 长度验证
        if not self.is_valid_length(cleaned):
            return None
        
        # 去重验证
        if self.is_duplicate(cleaned):
            return None
        
        return cleaned
    
    def reset_dedup_cache(self):
        """重置去重缓存"""
        with self._lock:
            self._seen_hashes.clear()
    
    def get_dedup_count(self) -> int:
        """获取已处理的唯一文本数"""
        with self._lock:
            return len(self._seen_hashes)


# ==================== 分词器 ====================

class TextTokenizer:
    """
    中文分词器
    
    支持：
    1. jieba分词
    2. 停用词过滤
    3. 词性标注（可选）
    """
    
    # 默认停用词
    DEFAULT_STOPWORDS = {
        '的', '了', '和', '是', '就', '都', '而', '及', '与', '着',
        '或', '一个', '没有', '我们', '你们', '他们', '她们', '它们',
        '这个', '那个', '这些', '那些', '什么', '怎么', '为什么',
        '哪里', '哪个', '谁', '如何', '可以', '可能', '应该', '不是',
        '但是', '然后', '因为', '所以', '如果', '虽然', '只是',
    }
    
    def __init__(self, use_paddle: bool = False):
        """
        初始化分词器
        
        Args:
            use_paddle: 是否使用paddle模式（更精确但更慢）
        """
        self.use_paddle = use_paddle
        self._jieba_loaded = False
        self._jieba = None
        self._stopwords = self.DEFAULT_STOPWORDS.copy()
    
    def _load_jieba(self):
        """延迟加载jieba"""
        if self._jieba_loaded:
            return
        
        try:
            import jieba
            if self.use_paddle:
                jieba.enable_paddle()
            self._jieba = jieba
            self._jieba_loaded = True
            logger.info("jieba分词器已加载")
        except ImportError:
            logger.warning("jieba未安装")
            self._jieba_loaded = True
    
    def load_stopwords(self, filepath: str):
        """加载停用词文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                words = {line.strip() for line in f if line.strip()}
                self._stopwords.update(words)
            logger.info(f"加载了 {len(words)} 个停用词")
        except Exception as e:
            logger.warning(f"加载停用词失败: {e}")
    
    def tokenize(self, text: str, remove_stopwords: bool = True) -> List[str]:
        """
        分词
        
        Args:
            text: 输入文本
            remove_stopwords: 是否移除停用词
            
        Returns:
            词语列表
        """
        self._load_jieba()
        
        if not self._jieba:
            # 后备方案：简单分割
            return [w for w in re.split(r'\s+', text) if w and len(w) > 1]
        
        words = list(self._jieba.cut(text))
        
        if remove_stopwords:
            words = [w for w in words if w not in self._stopwords and len(w.strip()) > 0]
        
        return words
    
    def tokenize_batch(self, texts: List[str], remove_stopwords: bool = True) -> List[List[str]]:
        """批量分词"""
        return [self.tokenize(t, remove_stopwords) for t in texts]


# ==================== 情感分析器接口 ====================

class SentimentAnalyzerWrapper:
    """
    情感分析器封装
    
    统一词典方法、BERT方法和混合方法的接口
    """
    
    def __init__(self, method: str = 'hybrid'):
        """
        初始化
        
        Args:
            method: 分析方法 (lexicon/bert/hybrid)
        """
        self.method = method
        self._analyzer = None
        self._initialized = False
    
    def _init_analyzer(self):
        """延迟初始化分析器"""
        if self._initialized:
            return
        
        if self.method == 'hybrid' and HYBRID_AVAILABLE:
            self._analyzer = HybridSentimentAnalyzer()
            logger.info("混合分析器已初始化")
        elif self.method == 'lexicon' and LEXICON_AVAILABLE:
            self._analyzer = 'lexicon'
            logger.info("词典分析器已初始化")
        else:
            logger.warning(f"分析方法 {self.method} 不可用，使用词典方法")
            if LEXICON_AVAILABLE:
                self._analyzer = 'lexicon'
        
        self._initialized = True
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        分析单条文本
        
        Returns:
            {
                'sentiment': str,       # positive/neutral/negative
                'score': float,         # [-1, 1]
                'confidence': float,    # [0, 1]
            }
        """
        self._init_analyzer()
        
        if self._analyzer is None:
            return {'sentiment': 'neutral', 'score': 0.0, 'confidence': 0.5}
        
        try:
            if self._analyzer == 'lexicon':
                # 词典方法
                sentiment, score = SentimentLexicon.analyze(text)
                confidence = min(1.0, abs(score) + 0.3)
                return {
                    'sentiment': sentiment,
                    'score': round(score, 4),
                    'confidence': round(confidence, 4)
                }
            else:
                # 混合方法
                result = self._analyzer.analyze(text)
                return {
                    'sentiment': result.polarity,
                    'score': round(result.score, 4),
                    'confidence': round(result.confidence, 4)
                }
        except Exception as e:
            logger.error(f"情感分析失败: {e}")
            return {'sentiment': 'neutral', 'score': 0.0, 'confidence': 0.5}
    
    def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """批量分析"""
        return [self.analyze(t) for t in texts]


# ==================== 数据处理流水线 ====================

class DataPipeline:
    """
    数据处理流水线
    
    完整的数据采集->清洗->分析->存储流程
    """
    
    def __init__(self, config: PipelineConfig = None):
        """
        初始化流水线
        
        Args:
            config: 流水线配置
        """
        self.config = config or PipelineConfig()
        
        # 初始化组件
        self.cleaner = DataCleaner(self.config)
        self.tokenizer = TextTokenizer()
        self.sentiment_analyzer = SentimentAnalyzerWrapper(self.config.sentiment_method)
        
        # 爬虫（延迟初始化）
        self._crawler = None
        
        # 数据存储
        self._data_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data'
        )
        os.makedirs(self._data_dir, exist_ok=True)
        
        # 统计信息
        self.stats = {
            'total_crawled': 0,
            'total_cleaned': 0,
            'total_duplicates': 0,
            'total_invalid': 0,
            'total_processed': 0,
            'start_time': None,
            'end_time': None,
        }
        
        logger.info("DataPipeline初始化完成")
    
    def _get_crawler(self) -> WeiboCrawler:
        """获取爬虫实例"""
        if self._crawler is None:
            if not CRAWLER_AVAILABLE:
                raise RuntimeError("爬虫模块不可用")
            self._crawler = WeiboCrawler()
        return self._crawler
    
    def crawl_hot_search(self) -> List[Dict]:
        """
        采集热搜榜
        
        Returns:
            热搜列表
        """
        logger.info("开始采集热搜榜...")
        crawler = self._get_crawler()
        
        hot_list = crawler.get_hot_search()
        logger.info(f"热搜榜采集完成，共 {len(hot_list)} 条")
        
        # 保存
        if self.config.save_raw:
            self._save_data(hot_list, 'hotsearch')
        
        return hot_list
    
    def crawl_by_keywords(self, keywords: List[str], 
                          progress_callback: callable = None) -> List[Dict]:
        """
        按关键词采集微博
        
        Args:
            keywords: 关键词列表
            progress_callback: 进度回调函数
            
        Returns:
            微博数据列表
        """
        logger.info(f"开始按关键词采集，关键词: {keywords}")
        crawler = self._get_crawler()
        
        all_data = []
        total_keywords = len(keywords)
        
        for idx, keyword in enumerate(keywords):
            logger.info(f"采集关键词 [{idx+1}/{total_keywords}]: {keyword}")
            keyword_data = []
            
            for page in range(1, self.config.pages_per_keyword + 1):
                try:
                    for weibo in crawler.search_weibo(keyword, page):
                        keyword_data.append(weibo)
                        
                        if len(keyword_data) >= self.config.weibo_per_keyword:
                            break
                    
                    if len(keyword_data) >= self.config.weibo_per_keyword:
                        break
                    
                    time.sleep(self.config.request_interval)
                    
                except Exception as e:
                    logger.error(f"采集页面失败: {e}")
                    continue
            
            all_data.extend(keyword_data)
            self.stats['total_crawled'] += len(keyword_data)
            
            # 进度回调
            if progress_callback:
                progress_callback({
                    'keyword': keyword,
                    'index': idx + 1,
                    'total': total_keywords,
                    'count': len(keyword_data),
                    'total_count': len(all_data)
                })
            
            logger.info(f"关键词 '{keyword}' 采集完成，共 {len(keyword_data)} 条")
        
        # 保存原始数据
        if self.config.save_raw and all_data:
            self._save_data(all_data, 'raw_weibo')
        
        logger.info(f"关键词采集完成，总计 {len(all_data)} 条")
        return all_data
    
    def process_data(self, raw_data: List[Dict]) -> List[ProcessedWeibo]:
        """
        处理原始数据
        
        Args:
            raw_data: 原始微博数据
            
        Returns:
            处理后的数据列表
        """
        logger.info(f"开始处理数据，共 {len(raw_data)} 条...")
        processed_list = []
        
        for item in raw_data:
            try:
                # 提取原始文本
                text_raw = item.get('text', '')
                if not text_raw:
                    self.stats['total_invalid'] += 1
                    continue
                
                # 清洗文本
                text_clean = self.cleaner.clean_and_validate(text_raw)
                if text_clean is None:
                    if self.cleaner.is_duplicate(text_raw):
                        self.stats['total_duplicates'] += 1
                    else:
                        self.stats['total_invalid'] += 1
                    continue
                
                self.stats['total_cleaned'] += 1
                
                # 分词
                words = self.tokenizer.tokenize(text_clean)
                
                # 情感分析
                sentiment_result = {'sentiment': 'neutral', 'score': 0.0, 'confidence': 0.5}
                if self.config.enable_sentiment:
                    sentiment_result = self.sentiment_analyzer.analyze(text_clean)
                
                # 提取用户信息
                user = item.get('user', {}) or {}
                
                # 构建处理后数据
                processed = ProcessedWeibo(
                    id=str(item.get('id', '')),
                    mid=str(item.get('mid', '')),
                    text_raw=text_raw,
                    text_clean=text_clean,
                    words=words,
                    user_id=str(user.get('id', '')),
                    user_name=user.get('screen_name', ''),
                    user_followers=user.get('followers_count', 0),
                    user_verified=user.get('verified', False),
                    reposts_count=item.get('reposts_count', 0),
                    comments_count=item.get('comments_count', 0),
                    attitudes_count=item.get('attitudes_count', 0),
                    created_at=item.get('created_at', ''),
                    crawl_time=item.get('crawl_time', datetime.now().isoformat()),
                    sentiment=sentiment_result['sentiment'],
                    sentiment_score=sentiment_result['score'],
                    sentiment_confidence=sentiment_result['confidence'],
                    keyword=item.get('keyword', ''),
                    source='weibo',
                    data_hash=self.cleaner.compute_hash(text_raw)
                )
                
                processed_list.append(processed)
                self.stats['total_processed'] += 1
                
            except Exception as e:
                logger.error(f"处理数据失败: {e}")
                self.stats['total_invalid'] += 1
                continue
        
        # 保存处理后数据
        if self.config.save_processed and processed_list:
            self._save_processed_data(processed_list)
        
        logger.info(f"数据处理完成，成功处理 {len(processed_list)} 条")
        return processed_list
    
    def run_full_pipeline(self, keywords: List[str] = None,
                          crawl_hot: bool = True,
                          progress_callback: callable = None) -> Dict[str, Any]:
        """
        运行完整流水线
        
        Args:
            keywords: 关键词列表（可选）
            crawl_hot: 是否爬取热搜相关微博
            progress_callback: 进度回调
            
        Returns:
            处理结果统计
        """
        self.stats['start_time'] = datetime.now().isoformat()
        logger.info("========== 开始运行完整流水线 ==========")
        
        all_raw_data = []
        
        # 1. 采集热搜
        if crawl_hot:
            try:
                hot_list = self.crawl_hot_search()
                
                # 采集热搜话题的微博
                hot_keywords = [h['title'] for h in hot_list[:5]]
                if hot_keywords:
                    hot_weibo = self.crawl_by_keywords(
                        hot_keywords, 
                        progress_callback
                    )
                    all_raw_data.extend(hot_weibo)
            except Exception as e:
                logger.error(f"热搜采集失败: {e}")
        
        # 2. 按关键词采集
        if keywords:
            keyword_weibo = self.crawl_by_keywords(keywords, progress_callback)
            all_raw_data.extend(keyword_weibo)
        
        # 3. 数据处理
        processed_data = self.process_data(all_raw_data)
        
        self.stats['end_time'] = datetime.now().isoformat()
        
        # 4. 生成统计报告
        result = {
            **self.stats,
            'processed_data_count': len(processed_data),
            'sentiment_distribution': self._calculate_sentiment_distribution(processed_data),
            'top_keywords': self._extract_top_keywords(processed_data),
        }
        
        logger.info("========== 流水线运行完成 ==========")
        logger.info(f"统计: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        return result
    
    def _calculate_sentiment_distribution(self, data: List[ProcessedWeibo]) -> Dict[str, int]:
        """计算情感分布"""
        distribution = {'positive': 0, 'neutral': 0, 'negative': 0}
        for item in data:
            sentiment = item.sentiment
            if sentiment in distribution:
                distribution[sentiment] += 1
        return distribution
    
    def _extract_top_keywords(self, data: List[ProcessedWeibo], top_k: int = 20) -> List[Dict]:
        """提取高频关键词"""
        from collections import Counter
        word_counter = Counter()
        
        for item in data:
            word_counter.update(item.words)
        
        return [
            {'word': word, 'count': count}
            for word, count in word_counter.most_common(top_k)
        ]
    
    def _save_data(self, data: List[Dict], prefix: str):
        """保存数据"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{prefix}_{timestamp}.json"
        filepath = os.path.join(self._data_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"数据已保存: {filepath}")
    
    def _save_processed_data(self, data: List[ProcessedWeibo]):
        """保存处理后数据"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"processed_{timestamp}.json"
        filepath = os.path.join(self._data_dir, filename)
        
        # 转换为字典列表
        dict_data = [asdict(item) for item in data]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dict_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"处理后数据已保存: {filepath}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'dedup_cache_size': self.cleaner.get_dedup_count(),
        }
    
    def reset(self):
        """重置流水线状态"""
        self.cleaner.reset_dedup_cache()
        self.stats = {
            'total_crawled': 0,
            'total_cleaned': 0,
            'total_duplicates': 0,
            'total_invalid': 0,
            'total_processed': 0,
            'start_time': None,
            'end_time': None,
        }
        logger.info("流水线状态已重置")


# ==================== 便捷函数 ====================

_pipeline_instance = None

def get_pipeline() -> DataPipeline:
    """获取流水线单例"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = DataPipeline()
    return _pipeline_instance


def run_pipeline(keywords: List[str] = None, 
                 crawl_hot: bool = True) -> Dict[str, Any]:
    """运行数据流水线"""
    pipeline = get_pipeline()
    return pipeline.run_full_pipeline(keywords, crawl_hot)


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='微博数据采集与处理流水线')
    parser.add_argument('--keywords', '-k', nargs='+', help='关键词列表')
    parser.add_argument('--no-hot', action='store_true', help='不采集热搜')
    parser.add_argument('--test', action='store_true', help='测试模式')
    
    args = parser.parse_args()
    
    if args.test:
        # 测试模式
        print("=" * 60)
        print("数据流水线测试")
        print("=" * 60)
        
        pipeline = DataPipeline()
        
        # 测试数据清洗
        test_texts = [
            "这个产品太棒了！http://example.com @测试用户 #话题#",
            "服务态度很差，非常失望😭",
            "一般般吧",
        ]
        
        print("\n测试数据清洗:")
        for text in test_texts:
            cleaned = pipeline.cleaner.clean_text(text)
            print(f"  原始: {text}")
            print(f"  清洗: {cleaned}")
            print()
        
        # 测试分词
        print("测试分词:")
        for text in test_texts:
            words = pipeline.tokenizer.tokenize(text)
            print(f"  文本: {text}")
            print(f"  分词: {words}")
            print()
        
        # 测试情感分析
        print("测试情感分析:")
        for text in test_texts:
            result = pipeline.sentiment_analyzer.analyze(text)
            print(f"  文本: {text}")
            print(f"  情感: {result}")
            print()
    else:
        # 正常运行
        result = run_pipeline(args.keywords, not args.no_hot)
        print(json.dumps(result, ensure_ascii=False, indent=2))

