"""
情感分析缓存服务
================

提升情感分析响应速度，减少重复计算

功能：
1. 文本哈希缓存：MD5哈希，相同文本直接返回
2. 分级缓存策略：内存LRU + SQLite本地缓存
3. 批量处理优化：batch inference
4. 缓存管理：命中率统计、LRU清理、预热
"""

import os
import json
import time
import hashlib
import sqlite3
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from functools import lru_cache
from collections import OrderedDict
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('SentimentCache')


@dataclass
class CacheEntry:
    """缓存条目"""
    text_hash: str
    text_preview: str  # 前50字符
    sentiment: float
    confidence: float
    label: str  # positive, negative, neutral
    method: str  # rule, bert, hybrid
    created_at: str
    accessed_at: str
    access_count: int = 1
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CacheStats:
    """缓存统计"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    l1_hits: int = 0  # 内存缓存命中
    l2_hits: int = 0  # SQLite缓存命中
    avg_response_time_ms: float = 0
    
    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            'hit_rate': round(self.hit_rate * 100, 2)
        }


class LRUCache:
    """
    线程安全的LRU缓存
    
    一级缓存：内存缓存
    """
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """获取缓存"""
        with self._lock:
            if key in self._cache:
                # 移动到末尾（最近使用）
                self._cache.move_to_end(key)
                entry = self._cache[key]
                entry.access_count += 1
                entry.accessed_at = datetime.now().isoformat()
                return entry
        return None
    
    def put(self, key: str, entry: CacheEntry):
        """添加缓存"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_size:
                    # 移除最久未使用的
                    self._cache.popitem(last=False)
                self._cache[key] = entry
    
    def remove(self, key: str) -> bool:
        """移除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
        return False
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """缓存大小"""
        return len(self._cache)
    
    def keys(self) -> List[str]:
        """所有键"""
        with self._lock:
            return list(self._cache.keys())


class SQLiteCache:
    """
    SQLite本地缓存
    
    二级缓存：持久化存储
    """
    
    def __init__(self, db_path: str, ttl_hours: int = 24):
        self.db_path = db_path
        self.ttl_hours = ttl_hours
        self._lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sentiment_cache (
                    text_hash TEXT PRIMARY KEY,
                    text_preview TEXT,
                    sentiment REAL,
                    confidence REAL,
                    label TEXT,
                    method TEXT,
                    created_at TEXT,
                    accessed_at TEXT,
                    access_count INTEGER DEFAULT 1
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_accessed_at 
                ON sentiment_cache(accessed_at)
            ''')
            conn.commit()
    
    def get(self, text_hash: str) -> Optional[CacheEntry]:
        """获取缓存"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        'SELECT * FROM sentiment_cache WHERE text_hash = ?',
                        (text_hash,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        # 检查TTL
                        created = datetime.fromisoformat(row['created_at'])
                        if datetime.now() - created > timedelta(hours=self.ttl_hours):
                            # 过期，删除
                            conn.execute(
                                'DELETE FROM sentiment_cache WHERE text_hash = ?',
                                (text_hash,)
                            )
                            conn.commit()
                            return None
                        
                        # 更新访问时间
                        conn.execute('''
                            UPDATE sentiment_cache 
                            SET accessed_at = ?, access_count = access_count + 1
                            WHERE text_hash = ?
                        ''', (datetime.now().isoformat(), text_hash))
                        conn.commit()
                        
                        return CacheEntry(
                            text_hash=row['text_hash'],
                            text_preview=row['text_preview'],
                            sentiment=row['sentiment'],
                            confidence=row['confidence'],
                            label=row['label'],
                            method=row['method'],
                            created_at=row['created_at'],
                            accessed_at=row['accessed_at'],
                            access_count=row['access_count']
                        )
            except Exception as e:
                logger.error(f"SQLite缓存读取失败: {e}")
        return None
    
    def put(self, entry: CacheEntry):
        """添加缓存"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO sentiment_cache 
                        (text_hash, text_preview, sentiment, confidence, label, method, created_at, accessed_at, access_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        entry.text_hash,
                        entry.text_preview,
                        entry.sentiment,
                        entry.confidence,
                        entry.label,
                        entry.method,
                        entry.created_at,
                        entry.accessed_at,
                        entry.access_count
                    ))
                    conn.commit()
            except Exception as e:
                logger.error(f"SQLite缓存写入失败: {e}")
    
    def remove(self, text_hash: str) -> bool:
        """移除缓存"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        'DELETE FROM sentiment_cache WHERE text_hash = ?',
                        (text_hash,)
                    )
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"SQLite缓存删除失败: {e}")
        return False
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('DELETE FROM sentiment_cache')
                    conn.commit()
            except Exception as e:
                logger.error(f"SQLite缓存清空失败: {e}")
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        cutoff = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()
        
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        'DELETE FROM sentiment_cache WHERE created_at < ?',
                        (cutoff,)
                    )
                    conn.commit()
                    return cursor.rowcount
            except Exception as e:
                logger.error(f"清理过期缓存失败: {e}")
        return 0
    
    def size(self) -> int:
        """缓存大小"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute('SELECT COUNT(*) FROM sentiment_cache')
                    return cursor.fetchone()[0]
            except:
                return 0


class SentimentCacheService:
    """
    情感分析缓存服务
    
    分级缓存策略：
    - L1: 内存LRU缓存（快速，容量有限）
    - L2: SQLite本地缓存（持久化，容量大）
    """
    
    def __init__(self, 
                 l1_size: int = 1000,
                 l2_ttl_hours: int = 24,
                 db_path: str = None):
        
        # 缓存层
        self.l1_cache = LRUCache(max_size=l1_size)
        
        db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data', 'sentiment_cache.db'
        )
        self.l2_cache = SQLiteCache(db_path=db_path, ttl_hours=l2_ttl_hours)
        
        # 统计
        self._stats = CacheStats()
        self._stats_lock = threading.Lock()
        
        # 响应时间记录
        self._response_times: List[float] = []
        
        # 批量处理
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        # 情感分析器（延迟加载）
        self._analyzer = None
        
        logger.info(f"缓存服务初始化: L1={l1_size}, L2_TTL={l2_ttl_hours}h")
    
    def _get_analyzer(self):
        """获取情感分析器"""
        if self._analyzer is None:
            try:
                from services.rule_based_analyzer import RuleBasedSentimentAnalyzer
                self._analyzer = RuleBasedSentimentAnalyzer()
            except ImportError:
                logger.warning("无法加载情感分析器，使用模拟分析")
                self._analyzer = None
        return self._analyzer
    
    @staticmethod
    def compute_hash(text: str) -> str:
        """计算文本哈希"""
        # 标准化文本
        normalized = text.strip().lower()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def get(self, text: str) -> Optional[CacheEntry]:
        """
        获取缓存的情感分析结果
        
        查找顺序：L1 -> L2
        """
        start_time = time.time()
        text_hash = self.compute_hash(text)
        
        with self._stats_lock:
            self._stats.total_requests += 1
        
        # L1查找
        entry = self.l1_cache.get(text_hash)
        if entry:
            with self._stats_lock:
                self._stats.cache_hits += 1
                self._stats.l1_hits += 1
            self._record_response_time(start_time)
            return entry
        
        # L2查找
        entry = self.l2_cache.get(text_hash)
        if entry:
            # 提升到L1
            self.l1_cache.put(text_hash, entry)
            with self._stats_lock:
                self._stats.cache_hits += 1
                self._stats.l2_hits += 1
            self._record_response_time(start_time)
            return entry
        
        with self._stats_lock:
            self._stats.cache_misses += 1
        
        self._record_response_time(start_time)
        return None
    
    def put(self, text: str, sentiment: float, confidence: float, 
            label: str, method: str = 'hybrid') -> CacheEntry:
        """
        缓存情感分析结果
        
        同时写入L1和L2
        """
        text_hash = self.compute_hash(text)
        now = datetime.now().isoformat()
        
        entry = CacheEntry(
            text_hash=text_hash,
            text_preview=text[:50],
            sentiment=sentiment,
            confidence=confidence,
            label=label,
            method=method,
            created_at=now,
            accessed_at=now
        )
        
        # 写入L1
        self.l1_cache.put(text_hash, entry)
        
        # 异步写入L2
        self._executor.submit(self.l2_cache.put, entry)
        
        return entry
    
    def analyze(self, text: str, method: str = 'hybrid') -> Dict:
        """
        带缓存的情感分析
        
        Args:
            text: 文本内容
            method: 分析方法 (rule, bert, hybrid)
        
        Returns:
            分析结果
        """
        # 先查缓存
        cached = self.get(text)
        if cached:
            return {
                'text': text,
                'sentiment': cached.sentiment,
                'confidence': cached.confidence,
                'label': cached.label,
                'method': cached.method,
                'cached': True
            }
        
        # 执行分析
        result = self._do_analyze(text, method)
        
        # 缓存结果
        self.put(
            text=text,
            sentiment=result['sentiment'],
            confidence=result['confidence'],
            label=result['label'],
            method=method
        )
        
        result['cached'] = False
        return result
    
    def _do_analyze(self, text: str, method: str) -> Dict:
        """执行实际的情感分析"""
        analyzer = self._get_analyzer()
        
        if analyzer:
            try:
                result = analyzer.analyze(text)
                return {
                    'text': text,
                    'sentiment': result.get('score', 0),
                    'confidence': result.get('confidence', 0.5),
                    'label': result.get('label', 'neutral'),
                    'method': method
                }
            except Exception as e:
                logger.error(f"情感分析失败: {e}")
        
        # 模拟分析
        import random
        sentiment = random.uniform(-1, 1)
        return {
            'text': text,
            'sentiment': sentiment,
            'confidence': random.uniform(0.5, 1.0),
            'label': 'positive' if sentiment > 0.3 else 'negative' if sentiment < -0.3 else 'neutral',
            'method': 'mock'
        }
    
    def analyze_batch(self, texts: List[str], method: str = 'hybrid') -> List[Dict]:
        """
        批量情感分析
        
        优化策略：
        1. 先批量查缓存
        2. 对未命中的批量分析
        3. 批量写入缓存
        """
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []
        
        # 批量查缓存
        for i, text in enumerate(texts):
            cached = self.get(text)
            if cached:
                results[i] = {
                    'text': text,
                    'sentiment': cached.sentiment,
                    'confidence': cached.confidence,
                    'label': cached.label,
                    'method': cached.method,
                    'cached': True
                }
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
        
        # 批量分析未命中的
        if uncached_texts:
            analyzed = self._batch_analyze(uncached_texts, method)
            
            for idx, result in zip(uncached_indices, analyzed):
                results[idx] = result
                
                # 缓存结果
                self.put(
                    text=result['text'],
                    sentiment=result['sentiment'],
                    confidence=result['confidence'],
                    label=result['label'],
                    method=method
                )
        
        return results
    
    def _batch_analyze(self, texts: List[str], method: str) -> List[Dict]:
        """批量执行情感分析"""
        analyzer = self._get_analyzer()
        
        if analyzer and hasattr(analyzer, 'analyze_batch'):
            try:
                results = analyzer.analyze_batch(texts)
                return [{
                    'text': text,
                    'sentiment': r.get('score', 0),
                    'confidence': r.get('confidence', 0.5),
                    'label': r.get('label', 'neutral'),
                    'method': method,
                    'cached': False
                } for text, r in zip(texts, results)]
            except Exception as e:
                logger.error(f"批量分析失败: {e}")
        
        # 逐个分析
        return [self._do_analyze(text, method) for text in texts]
    
    def _record_response_time(self, start_time: float):
        """记录响应时间"""
        elapsed = (time.time() - start_time) * 1000  # 毫秒
        self._response_times.append(elapsed)
        
        # 只保留最近1000条
        if len(self._response_times) > 1000:
            self._response_times = self._response_times[-1000:]
        
        # 更新平均响应时间
        with self._stats_lock:
            self._stats.avg_response_time_ms = sum(self._response_times) / len(self._response_times)
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        with self._stats_lock:
            stats = self._stats.to_dict()
        
        stats['l1_size'] = self.l1_cache.size()
        stats['l2_size'] = self.l2_cache.size()
        
        return stats
    
    def clear_cache(self, level: str = 'all'):
        """
        清空缓存
        
        Args:
            level: 'l1', 'l2', 'all'
        """
        if level in ('l1', 'all'):
            self.l1_cache.clear()
            logger.info("L1缓存已清空")
        
        if level in ('l2', 'all'):
            self.l2_cache.clear()
            logger.info("L2缓存已清空")
    
    def cleanup(self) -> Dict:
        """清理过期缓存"""
        expired_count = self.l2_cache.cleanup_expired()
        return {
            'expired_removed': expired_count,
            'l1_size': self.l1_cache.size(),
            'l2_size': self.l2_cache.size()
        }
    
    def warmup(self, common_texts: List[str] = None):
        """
        缓存预热
        
        预计算常用文本的情感分析结果
        """
        if common_texts is None:
            # 默认常用词
            common_texts = [
                "很好", "不错", "太棒了", "喜欢", "支持",
                "差劲", "垃圾", "失望", "讨厌", "反对",
                "一般", "还行", "普通", "正常", "可以"
            ]
        
        logger.info(f"开始缓存预热: {len(common_texts)} 条文本")
        
        for text in common_texts:
            self.analyze(text)
        
        logger.info("缓存预热完成")
    
    def export_cache(self, filepath: str):
        """导出缓存到文件"""
        data = []
        
        # 导出L1
        for key in self.l1_cache.keys():
            entry = self.l1_cache.get(key)
            if entry:
                data.append(entry.to_dict())
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"缓存已导出到: {filepath}")
    
    def import_cache(self, filepath: str):
        """从文件导入缓存"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for item in data:
                entry = CacheEntry(**item)
                self.l1_cache.put(entry.text_hash, entry)
                self.l2_cache.put(entry)
            
            logger.info(f"已导入 {len(data)} 条缓存")
        except Exception as e:
            logger.error(f"导入缓存失败: {e}")


# 全局单例
_cache_service: Optional[SentimentCacheService] = None


def get_cache_service() -> SentimentCacheService:
    """获取缓存服务单例"""
    global _cache_service
    if _cache_service is None:
        _cache_service = SentimentCacheService()
    return _cache_service


# ==================== 便捷函数 ====================

def cached_analyze(text: str, method: str = 'hybrid') -> Dict:
    """带缓存的情感分析"""
    return get_cache_service().analyze(text, method)


def cached_analyze_batch(texts: List[str], method: str = 'hybrid') -> List[Dict]:
    """带缓存的批量情感分析"""
    return get_cache_service().analyze_batch(texts, method)


def get_cache_stats() -> Dict:
    """获取缓存统计"""
    return get_cache_service().get_stats()


# ==================== 装饰器 ====================

def sentiment_cached(method: str = 'hybrid'):
    """
    情感分析缓存装饰器
    
    用法:
        @sentiment_cached()
        def my_analyze(text):
            return do_analysis(text)
    """
    def decorator(func):
        def wrapper(text, *args, **kwargs):
            cache = get_cache_service()
            
            # 查缓存
            cached = cache.get(text)
            if cached:
                return {
                    'sentiment': cached.sentiment,
                    'confidence': cached.confidence,
                    'label': cached.label,
                    'cached': True
                }
            
            # 执行原函数
            result = func(text, *args, **kwargs)
            
            # 缓存结果
            cache.put(
                text=text,
                sentiment=result.get('sentiment', result.get('score', 0)),
                confidence=result.get('confidence', 0.5),
                label=result.get('label', 'neutral'),
                method=method
            )
            
            result['cached'] = False
            return result
        
        return wrapper
    return decorator


if __name__ == '__main__':
    # 测试缓存服务
    cache = SentimentCacheService()
    
    # 预热
    cache.warmup()
    
    # 测试单条分析
    print("\n单条分析测试:")
    result1 = cache.analyze("这个产品真的很好用")
    print(f"  结果: {result1}")
    
    result2 = cache.analyze("这个产品真的很好用")  # 应该命中缓存
    print(f"  缓存命中: {result2}")
    
    # 测试批量分析
    print("\n批量分析测试:")
    texts = [
        "今天天气真好",
        "这个产品真的很好用",  # 应该命中缓存
        "服务态度太差了",
        "一般般吧"
    ]
    results = cache.analyze_batch(texts)
    for r in results:
        print(f"  {r['text'][:10]}... -> {r['label']} (cached={r['cached']})")
    
    # 统计
    print("\n缓存统计:")
    stats = cache.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
