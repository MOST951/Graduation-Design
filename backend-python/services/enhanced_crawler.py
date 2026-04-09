"""
增强型微博数据采集与清洗服务
================================

功能特性：
1. 智能重试机制与错误恢复
2. 数据验证与质量检查
3. 增量采集支持
4. 自动Cookie管理
5. 分布式采集支持

作者：毕业设计
"""

import os
import json
import time
import hashlib
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Generator, Callable
from dataclasses import dataclass, field, asdict
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('EnhancedCrawler')

# 导入基础爬虫
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from crawler.weibo_crawler import WeiboCrawler, WeiboCrawlerTask
    CRAWLER_AVAILABLE = True
except ImportError:
    CRAWLER_AVAILABLE = False
    logger.warning("基础爬虫模块未加载")


# ==================== 数据模型 ====================

@dataclass
class CrawlConfig:
    """采集配置"""
    keywords: List[str] = field(default_factory=list)
    crawl_hot: bool = True
    pages_per_keyword: int = 5
    max_retries: int = 3
    retry_delay: float = 5.0
    request_interval: float = 2.0
    max_workers: int = 3
    enable_validation: bool = True
    min_text_length: int = 5
    max_text_length: int = 10000
    deduplicate: bool = True
    save_raw: bool = True


@dataclass 
class CrawlResult:
    """采集结果"""
    task_id: str
    status: str  # running, completed, failed
    start_time: datetime
    end_time: Optional[datetime] = None
    total_collected: int = 0
    total_failed: int = 0
    total_duplicates: int = 0
    data: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    

@dataclass
class DataQualityReport:
    """数据质量报告"""
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    duplicate_records: int = 0
    avg_text_length: float = 0.0
    sentiment_distribution: Dict[str, int] = field(default_factory=dict)
    user_stats: Dict[str, int] = field(default_factory=dict)
    time_range: Dict[str, str] = field(default_factory=dict)


# ==================== 数据验证器 ====================

class DataValidator:
    """微博数据验证器"""
    
    # 必需字段
    REQUIRED_FIELDS = ['id', 'text', 'user']
    
    # 文本清洗模式
    CLEAN_PATTERNS = {
        'html': re.compile(r'<[^>]+>'),
        'url': re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+'),
        'whitespace': re.compile(r'\s+'),
    }
    
    def __init__(self, config: CrawlConfig):
        self.config = config
        self.seen_ids = set()
        self.seen_hashes = set()
    
    def validate(self, weibo: Dict) -> tuple[bool, str]:
        """
        验证微博数据
        
        Returns:
            (is_valid, error_message)
        """
        # 1. 检查必需字段
        for field in self.REQUIRED_FIELDS:
            if field not in weibo or weibo[field] is None:
                return False, f"缺少必需字段: {field}"
        
        # 2. 检查文本
        text = weibo.get('text', '')
        if not text:
            return False, "文本为空"
        
        # 清洗后检查长度
        cleaned_text = self._clean_text(text)
        if len(cleaned_text) < self.config.min_text_length:
            return False, f"文本过短: {len(cleaned_text)} < {self.config.min_text_length}"
        
        if len(cleaned_text) > self.config.max_text_length:
            return False, f"文本过长: {len(cleaned_text)} > {self.config.max_text_length}"
        
        # 3. 检查重复
        if self.config.deduplicate:
            weibo_id = str(weibo.get('id', ''))
            if weibo_id in self.seen_ids:
                return False, "ID重复"
            
            text_hash = self._hash_text(cleaned_text)
            if text_hash in self.seen_hashes:
                return False, "内容重复"
            
            self.seen_ids.add(weibo_id)
            self.seen_hashes.add(text_hash)
        
        return True, ""
    
    def _clean_text(self, text: str) -> str:
        """清洗文本"""
        for pattern in self.CLEAN_PATTERNS.values():
            text = pattern.sub('', text)
        return text.strip()
    
    def _hash_text(self, text: str) -> str:
        """计算文本哈希"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def reset(self):
        """重置验证器状态"""
        self.seen_ids.clear()
        self.seen_hashes.clear()


# ==================== 数据清洗器 ====================

class DataCleaner:
    """微博数据清洗器"""
    
    # 表情映射（用于情感分析）
    EMOJI_SENTIMENT = {
        '😊': 1, '😄': 1, '😃': 1, '🥰': 1, '😍': 1, '👍': 1, '❤': 1, '💕': 1,
        '😢': -1, '😭': -1, '😡': -1, '😠': -1, '👎': -1, '💔': -1, '😤': -1,
    }
    
    # 敏感词过滤（基础列表）
    SENSITIVE_WORDS = set()
    
    def __init__(self):
        self._load_sensitive_words()
    
    def _load_sensitive_words(self):
        """加载敏感词库"""
        sensitive_path = os.path.join(
            os.path.dirname(__file__), '..', 'resources', 'sensitive_words.txt'
        )
        if os.path.exists(sensitive_path):
            try:
                with open(sensitive_path, 'r', encoding='utf-8') as f:
                    self.SENSITIVE_WORDS = set(line.strip() for line in f if line.strip())
            except Exception as e:
                logger.warning(f"加载敏感词库失败: {e}")
    
    def clean(self, weibo: Dict) -> Dict:
        """
        清洗微博数据
        
        Args:
            weibo: 原始微博数据
            
        Returns:
            清洗后的数据
        """
        cleaned = weibo.copy()
        
        # 1. 清洗文本
        text = cleaned.get('text', '')
        cleaned['text_raw'] = text
        cleaned['text'] = self._clean_text(text)
        
        # 2. 提取特征
        cleaned['extracted_urls'] = self._extract_urls(text)
        cleaned['extracted_mentions'] = self._extract_mentions(text)
        cleaned['extracted_hashtags'] = self._extract_hashtags(text)
        cleaned['emoji_sentiment'] = self._analyze_emoji_sentiment(text)
        
        # 3. 标准化字段
        cleaned['reposts_count'] = int(cleaned.get('reposts_count', 0) or 0)
        cleaned['comments_count'] = int(cleaned.get('comments_count', 0) or 0)
        cleaned['attitudes_count'] = int(cleaned.get('attitudes_count', 0) or 0)
        
        # 4. 计算热度分数
        cleaned['heat_score'] = self._calculate_heat(cleaned)
        
        # 5. 添加处理时间戳
        cleaned['processed_at'] = datetime.now().isoformat()
        
        return cleaned
    
    def _clean_text(self, text: str) -> str:
        """清洗文本内容"""
        if not text:
            return ""
        
        # 去除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 去除URL
        text = re.sub(r'https?://[^\s<>"{}|\\^`\[\]]+', '', text)
        
        # 处理@提及（保留内容但去除@符号）
        text = re.sub(r'@[\w\u4e00-\u9fff]+', '', text)
        
        # 处理话题标签（保留话题内容）
        text = re.sub(r'#([^#]+)#', r'\1', text)
        
        # 规范化空白
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_urls(self, text: str) -> List[str]:
        """提取URL"""
        return re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)
    
    def _extract_mentions(self, text: str) -> List[str]:
        """提取@提及"""
        return re.findall(r'@([\w\u4e00-\u9fff]+)', text)
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """提取话题标签"""
        return re.findall(r'#([^#]+)#', text)
    
    def _analyze_emoji_sentiment(self, text: str) -> float:
        """分析表情情感"""
        sentiment_sum = 0
        count = 0
        
        for emoji, score in self.EMOJI_SENTIMENT.items():
            if emoji in text:
                sentiment_sum += score
                count += 1
        
        return sentiment_sum / count if count > 0 else 0
    
    def _calculate_heat(self, weibo: Dict) -> float:
        """计算热度分数"""
        import math
        
        reposts = weibo.get('reposts_count', 0)
        comments = weibo.get('comments_count', 0)
        likes = weibo.get('attitudes_count', 0)
        
        # 加权热度公式
        raw_heat = 3 * reposts + 2 * comments + likes
        
        # 对数平滑
        return math.log(1 + raw_heat)


# ==================== 增强型爬虫服务 ====================

class EnhancedCrawlerService:
    """
    增强型微博采集服务
    
    特性：
    1. 智能重试与错误恢复
    2. 并发采集
    3. 数据验证与清洗
    4. 增量采集
    5. 实时进度回调
    """
    
    def __init__(self, config: CrawlConfig = None):
        self.config = config or CrawlConfig()
        self.validator = DataValidator(self.config)
        self.cleaner = DataCleaner()
        self._stop_flag = False
        self._lock = threading.Lock()
        
        # 统计信息
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retried_requests': 0,
        }
    
    def crawl(self, progress_callback: Callable = None) -> CrawlResult:
        """
        执行采集任务
        
        Args:
            progress_callback: 进度回调函数 (progress, message)
            
        Returns:
            CrawlResult
        """
        if not CRAWLER_AVAILABLE:
            return CrawlResult(
                task_id=self._generate_task_id(),
                status='failed',
                start_time=datetime.now(),
                errors=['爬虫模块不可用']
            )
        
        task_id = self._generate_task_id()
        result = CrawlResult(
            task_id=task_id,
            status='running',
            start_time=datetime.now()
        )
        
        try:
            self._stop_flag = False
            self.validator.reset()
            
            all_data = []
            
            # 1. 采集热搜
            if self.config.crawl_hot:
                if progress_callback:
                    progress_callback(10, "正在获取热搜榜...")
                
                hot_data = self._crawl_hot_search()
                all_data.extend(hot_data)
                
                if progress_callback:
                    progress_callback(30, f"热搜数据采集完成，共 {len(hot_data)} 条")
            
            # 2. 按关键词采集
            if self.config.keywords:
                total_keywords = len(self.config.keywords)
                
                for i, keyword in enumerate(self.config.keywords):
                    if self._stop_flag:
                        break
                    
                    progress = 30 + int(60 * (i + 1) / total_keywords)
                    if progress_callback:
                        progress_callback(progress, f"正在采集关键词: {keyword}")
                    
                    keyword_data = self._crawl_keyword(keyword)
                    all_data.extend(keyword_data)
            
            # 3. 数据验证和清洗
            if progress_callback:
                progress_callback(90, "正在验证和清洗数据...")
            
            validated_data = []
            for weibo in all_data:
                is_valid, error = self.validator.validate(weibo)
                if is_valid:
                    cleaned = self.cleaner.clean(weibo)
                    validated_data.append(cleaned)
                    result.total_collected += 1
                else:
                    result.total_failed += 1
                    if 'duplicate' in error.lower():
                        result.total_duplicates += 1
            
            result.data = validated_data
            result.status = 'completed'
            result.end_time = datetime.now()
            
            if progress_callback:
                progress_callback(100, f"采集完成，共 {result.total_collected} 条有效数据")
            
            # 4. 保存数据
            if self.config.save_raw:
                self._save_result(result)
            
        except Exception as e:
            result.status = 'failed'
            result.errors.append(str(e))
            result.end_time = datetime.now()
            logger.error(f"采集失败: {e}", exc_info=True)
        
        return result
    
    def _crawl_hot_search(self) -> List[Dict]:
        """采集热搜相关微博"""
        crawler = WeiboCrawler()
        all_data = []
        
        # 获取热搜榜
        hot_list = self._retry_request(crawler.get_hot_search)
        
        if not hot_list:
            logger.warning("获取热搜榜失败")
            return []
        
        # 采集前5个热搜话题
        for hot in hot_list[:5]:
            if self._stop_flag:
                break
            
            topic = hot.get('title', '')
            if not topic:
                continue
            
            logger.info(f"采集热搜话题: {topic}")
            
            for page in range(1, self.config.pages_per_keyword + 1):
                if self._stop_flag:
                    break
                
                try:
                    weibos = list(self._retry_request(
                        lambda: list(crawler.search_weibo(topic, page))
                    ) or [])
                    all_data.extend(weibos)
                except Exception as e:
                    logger.warning(f"采集话题 {topic} 第{page}页失败: {e}")
                
                time.sleep(self.config.request_interval)
        
        return all_data
    
    def _crawl_keyword(self, keyword: str) -> List[Dict]:
        """采集关键词相关微博"""
        crawler = WeiboCrawler()
        all_data = []
        
        for page in range(1, self.config.pages_per_keyword + 1):
            if self._stop_flag:
                break
            
            try:
                weibos = list(self._retry_request(
                    lambda: list(crawler.search_weibo(keyword, page))
                ) or [])
                all_data.extend(weibos)
                logger.info(f"关键词 '{keyword}' 第{page}页采集 {len(weibos)} 条")
            except Exception as e:
                logger.warning(f"采集关键词 {keyword} 第{page}页失败: {e}")
            
            time.sleep(self.config.request_interval)
        
        return all_data
    
    def _retry_request(self, func: Callable, *args, **kwargs):
        """带重试的请求"""
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                with self._lock:
                    self.stats['total_requests'] += 1
                
                result = func(*args, **kwargs)
                
                with self._lock:
                    self.stats['successful_requests'] += 1
                
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                
                with self._lock:
                    self.stats['retried_requests'] += 1
                
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
        
        with self._lock:
            self.stats['failed_requests'] += 1
        
        logger.error(f"请求最终失败: {last_error}")
        return None
    
    def _generate_task_id(self) -> str:
        """生成任务ID"""
        return f"crawl_{int(time.time() * 1000)}"
    
    def _save_result(self, result: CrawlResult):
        """保存采集结果"""
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'data'
        )
        os.makedirs(data_dir, exist_ok=True)
        
        filepath = os.path.join(data_dir, f'crawl_result_{result.task_id}.json')
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result.data, f, ensure_ascii=False, indent=2)
            logger.info(f"数据已保存到: {filepath}")
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
    
    def stop(self):
        """停止采集"""
        self._stop_flag = True
        logger.info("采集任务已停止")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            return self.stats.copy()
    
    def generate_quality_report(self, data: List[Dict]) -> DataQualityReport:
        """
        生成数据质量报告
        
        Args:
            data: 微博数据列表
            
        Returns:
            DataQualityReport
        """
        report = DataQualityReport()
        report.total_records = len(data)
        
        if not data:
            return report
        
        # 统计
        text_lengths = []
        sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        user_counts = {}
        timestamps = []
        
        for weibo in data:
            # 文本长度
            text = weibo.get('text', '')
            text_lengths.append(len(text))
            
            # 情感分布
            sentiment = weibo.get('sentiment', 'neutral')
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1
            
            # 用户统计
            user_id = str(weibo.get('user', {}).get('id', 'unknown'))
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
            
            # 时间范围
            created_at = weibo.get('created_at', '')
            if created_at:
                timestamps.append(created_at)
            
            report.valid_records += 1
        
        # 计算统计值
        report.avg_text_length = sum(text_lengths) / len(text_lengths) if text_lengths else 0
        report.sentiment_distribution = sentiment_counts
        report.user_stats = {
            'unique_users': len(user_counts),
            'avg_posts_per_user': len(data) / len(user_counts) if user_counts else 0
        }
        
        if timestamps:
            timestamps.sort()
            report.time_range = {
                'start': timestamps[0],
                'end': timestamps[-1]
            }
        
        return report


# ==================== 便捷函数 ====================

def crawl_weibo(
    keywords: List[str] = None,
    crawl_hot: bool = True,
    pages: int = 5,
    progress_callback: Callable = None
) -> CrawlResult:
    """
    便捷的微博采集函数
    
    Args:
        keywords: 关键词列表
        crawl_hot: 是否采集热搜
        pages: 每个关键词采集页数
        progress_callback: 进度回调
        
    Returns:
        CrawlResult
    """
    config = CrawlConfig(
        keywords=keywords or [],
        crawl_hot=crawl_hot,
        pages_per_keyword=pages
    )
    
    service = EnhancedCrawlerService(config)
    return service.crawl(progress_callback)


def validate_weibo_data(data: List[Dict]) -> DataQualityReport:
    """验证微博数据质量"""
    config = CrawlConfig()
    service = EnhancedCrawlerService(config)
    return service.generate_quality_report(data)


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='增强型微博采集工具')
    parser.add_argument('--keywords', nargs='+', help='搜索关键词')
    parser.add_argument('--hot', action='store_true', default=True, help='采集热搜')
    parser.add_argument('--pages', type=int, default=3, help='每个关键词采集页数')
    
    args = parser.parse_args()
    
    def progress_handler(progress, message):
        print(f"[{progress}%] {message}")
    
    result = crawl_weibo(
        keywords=args.keywords,
        crawl_hot=args.hot,
        pages=args.pages,
        progress_callback=progress_handler
    )
    
    print(f"\n采集完成:")
    print(f"  状态: {result.status}")
    print(f"  有效数据: {result.total_collected}")
    print(f"  失败数据: {result.total_failed}")
    print(f"  重复数据: {result.total_duplicates}")
    print(f"  耗时: {(result.end_time - result.start_time).total_seconds():.2f}秒")

