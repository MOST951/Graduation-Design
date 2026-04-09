"""
HBase 查询优化器
================

优化热点话题查询性能

功能：
1. 行键设计优化：时间倒序、预分区
2. 查询缓存：常用查询结果缓存
3. 批量操作优化：BufferedMutator、Scan+Filter
4. 监控与调优：响应时间监控、自动参数调整
"""

import os
import json
import time
import hashlib
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from collections import OrderedDict
from functools import wraps

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('HBaseOptimizer')


@dataclass
class QueryMetrics:
    """查询性能指标"""
    query_type: str
    table_name: str
    row_count: int
    response_time_ms: float
    cache_hit: bool
    timestamp: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    data: Any
    created_at: str
    accessed_at: str
    access_count: int = 1
    ttl_seconds: int = 300  # 5分钟默认TTL
    
    def is_expired(self) -> bool:
        created = datetime.fromisoformat(self.created_at)
        return datetime.now() - created > timedelta(seconds=self.ttl_seconds)


class QueryCache:
    """
    查询结果缓存
    
    LRU缓存 + TTL过期
    """
    
    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                
                # 检查过期
                if entry.is_expired():
                    del self._cache[key]
                    return None
                
                # 更新访问信息
                entry.accessed_at = datetime.now().isoformat()
                entry.access_count += 1
                self._cache.move_to_end(key)
                
                return entry.data
        return None
    
    def put(self, key: str, data: Any, ttl: int = None):
        """添加缓存"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key].data = data
                self._cache[key].accessed_at = datetime.now().isoformat()
            else:
                if len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)
                
                now = datetime.now().isoformat()
                self._cache[key] = CacheEntry(
                    key=key,
                    data=data,
                    created_at=now,
                    accessed_at=now,
                    ttl_seconds=ttl or self.default_ttl
                )
    
    def invalidate(self, key: str = None, pattern: str = None):
        """
        使缓存失效
        
        Args:
            key: 精确匹配的键
            pattern: 模式匹配（前缀）
        """
        with self._lock:
            if key:
                if key in self._cache:
                    del self._cache[key]
            elif pattern:
                keys_to_delete = [k for k in self._cache if k.startswith(pattern)]
                for k in keys_to_delete:
                    del self._cache[k]
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
    
    def stats(self) -> Dict:
        """缓存统计"""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'keys': list(self._cache.keys())[:10]  # 只返回前10个键
            }


class RowKeyDesigner:
    """
    行键设计器
    
    优化策略：
    1. 时间倒序：便于查询最新数据
    2. 哈希前缀：避免热点Region
    3. 复合键：支持多维度查询
    """
    
    # 时间戳最大值（用于倒序）
    MAX_TIMESTAMP = 9999999999999  # 毫秒级，约2286年
    
    @classmethod
    def design_topic_rowkey(cls, topic_id: str, timestamp: datetime = None) -> str:
        """
        设计热点话题行键
        
        格式: {hash_prefix}_{reversed_timestamp}_{topic_hash}
        
        Args:
            topic_id: 话题ID或名称
            timestamp: 时间戳，默认当前时间
        
        Returns:
            行键字符串
        """
        ts = timestamp or datetime.now()
        ts_millis = int(ts.timestamp() * 1000)
        reversed_ts = cls.MAX_TIMESTAMP - ts_millis
        
        # 话题哈希（取前8位）
        topic_hash = hashlib.md5(topic_id.encode()).hexdigest()[:8]
        
        # 哈希前缀（用于预分区，取话题哈希前2位）
        hash_prefix = topic_hash[:2]
        
        return f"{hash_prefix}_{reversed_ts:013d}_{topic_hash}"
    
    @classmethod
    def design_weibo_rowkey(cls, weibo_id: str, user_id: str = None, 
                           timestamp: datetime = None) -> str:
        """
        设计微博数据行键
        
        格式: {hash_prefix}_{reversed_timestamp}_{weibo_id}
        """
        ts = timestamp or datetime.now()
        ts_millis = int(ts.timestamp() * 1000)
        reversed_ts = cls.MAX_TIMESTAMP - ts_millis
        
        # 哈希前缀
        hash_prefix = hashlib.md5(weibo_id.encode()).hexdigest()[:2]
        
        return f"{hash_prefix}_{reversed_ts:013d}_{weibo_id}"
    
    @classmethod
    def design_sentiment_rowkey(cls, text_hash: str, timestamp: datetime = None) -> str:
        """
        设计情感分析结果行键
        
        格式: {hash_prefix}_{text_hash}_{timestamp}
        """
        ts = timestamp or datetime.now()
        ts_str = ts.strftime('%Y%m%d%H%M%S')
        
        hash_prefix = text_hash[:2]
        
        return f"{hash_prefix}_{text_hash}_{ts_str}"
    
    @classmethod
    def parse_rowkey(cls, rowkey: str) -> Dict:
        """解析行键"""
        parts = rowkey.split('_')
        
        if len(parts) >= 3:
            hash_prefix = parts[0]
            reversed_ts = int(parts[1])
            original_ts = cls.MAX_TIMESTAMP - reversed_ts
            timestamp = datetime.fromtimestamp(original_ts / 1000)
            
            return {
                'hash_prefix': hash_prefix,
                'timestamp': timestamp.isoformat(),
                'id': '_'.join(parts[2:])
            }
        
        return {'raw': rowkey}
    
    @classmethod
    def get_scan_range(cls, start_time: datetime, end_time: datetime, 
                      prefix: str = None) -> Tuple[str, str]:
        """
        获取扫描范围
        
        由于使用倒序时间戳，start和stop需要反转
        """
        # 结束时间对应的行键是扫描起点
        end_ts = int(end_time.timestamp() * 1000)
        start_reversed = cls.MAX_TIMESTAMP - end_ts
        
        # 开始时间对应的行键是扫描终点
        start_ts = int(start_time.timestamp() * 1000)
        end_reversed = cls.MAX_TIMESTAMP - start_ts
        
        if prefix:
            start_row = f"{prefix}_{start_reversed:013d}"
            stop_row = f"{prefix}_{end_reversed:013d}"
        else:
            start_row = f"{start_reversed:013d}"
            stop_row = f"{end_reversed:013d}"
        
        return start_row, stop_row


class HBaseOptimizer:
    """
    HBase 查询优化器
    
    提供优化的HBase操作接口
    """
    
    # 默认配置
    DEFAULT_CONFIG = {
        'batch_size': 1000,           # 批量操作大小
        'cache_size': 100,            # 缓存大小
        'cache_ttl': 300,             # 缓存TTL（秒）
        'scan_caching': 100,          # Scan缓存行数
        'write_buffer_size': 2097152, # 写缓冲区大小（2MB）
    }
    
    def __init__(self, config: Dict = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        
        # 查询缓存
        self._cache = QueryCache(
            max_size=self.config['cache_size'],
            default_ttl=self.config['cache_ttl']
        )
        
        # 性能指标
        self._metrics: List[QueryMetrics] = []
        self._metrics_lock = threading.Lock()
        
        # HBase连接（延迟初始化）
        self._connection = None
        
        # 行键设计器
        self.rowkey = RowKeyDesigner
        
        logger.info(f"HBase优化器初始化: {self.config}")
    
    def _get_connection(self):
        """获取HBase连接"""
        if self._connection is None:
            try:
                import happybase
                self._connection = happybase.Connection(
                    host=os.getenv('HBASE_HOST', 'localhost'),
                    port=int(os.getenv('HBASE_PORT', 9090))
                )
                logger.info("HBase连接成功")
            except ImportError:
                logger.warning("happybase未安装，使用模拟模式")
            except Exception as e:
                logger.warning(f"HBase连接失败: {e}，使用模拟模式")
        
        return self._connection
    
    def _record_metrics(self, query_type: str, table_name: str, 
                       row_count: int, response_time_ms: float, cache_hit: bool):
        """记录查询指标"""
        metrics = QueryMetrics(
            query_type=query_type,
            table_name=table_name,
            row_count=row_count,
            response_time_ms=response_time_ms,
            cache_hit=cache_hit,
            timestamp=datetime.now().isoformat()
        )
        
        with self._metrics_lock:
            self._metrics.append(metrics)
            # 只保留最近1000条
            if len(self._metrics) > 1000:
                self._metrics = self._metrics[-1000:]
    
    # ==================== 查询操作 ====================
    
    def get_top_topics(self, limit: int = 20, use_cache: bool = True) -> List[Dict]:
        """
        获取热门话题（带缓存）
        
        Args:
            limit: 返回数量
            use_cache: 是否使用缓存
        
        Returns:
            话题列表
        """
        cache_key = f"top_topics_{limit}"
        start_time = time.time()
        
        # 查缓存
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                self._record_metrics('get_top_topics', 'topics', len(cached), 
                                    (time.time() - start_time) * 1000, True)
                return cached
        
        # 查询HBase
        conn = self._get_connection()
        results = []
        
        if conn:
            try:
                table = conn.table('weibo_topics')
                
                # 使用Scan获取最新数据（行键倒序，直接扫描前N条）
                for key, data in table.scan(limit=limit):
                    results.append({
                        'rowkey': key.decode() if isinstance(key, bytes) else key,
                        **{k.decode(): v.decode() for k, v in data.items()}
                    })
            except Exception as e:
                logger.error(f"查询热门话题失败: {e}")
        else:
            # 模拟数据
            results = self._mock_top_topics(limit)
        
        # 缓存结果
        if use_cache and results:
            self._cache.put(cache_key, results, ttl=60)  # 1分钟TTL
        
        self._record_metrics('get_top_topics', 'topics', len(results),
                            (time.time() - start_time) * 1000, False)
        
        return results
    
    def get_topic_by_id(self, topic_id: str, use_cache: bool = True) -> Optional[Dict]:
        """获取单个话题详情"""
        cache_key = f"topic_{topic_id}"
        start_time = time.time()
        
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                self._record_metrics('get_topic', 'topics', 1,
                                    (time.time() - start_time) * 1000, True)
                return cached
        
        conn = self._get_connection()
        result = None
        
        if conn:
            try:
                table = conn.table('weibo_topics')
                # 使用前缀扫描
                prefix = hashlib.md5(topic_id.encode()).hexdigest()[:2]
                
                for key, data in table.scan(row_prefix=prefix.encode(), limit=1):
                    result = {
                        'rowkey': key.decode() if isinstance(key, bytes) else key,
                        **{k.decode(): v.decode() for k, v in data.items()}
                    }
                    break
            except Exception as e:
                logger.error(f"查询话题失败: {e}")
        else:
            result = self._mock_topic(topic_id)
        
        if use_cache and result:
            self._cache.put(cache_key, result)
        
        self._record_metrics('get_topic', 'topics', 1 if result else 0,
                            (time.time() - start_time) * 1000, False)
        
        return result
    
    def scan_by_time_range(self, table_name: str, start_time: datetime, 
                          end_time: datetime, limit: int = 1000) -> List[Dict]:
        """
        按时间范围扫描
        
        利用倒序时间戳行键优化
        """
        query_start = time.time()
        
        start_row, stop_row = self.rowkey.get_scan_range(start_time, end_time)
        
        conn = self._get_connection()
        results = []
        
        if conn:
            try:
                table = conn.table(table_name)
                
                for key, data in table.scan(
                    row_start=start_row.encode(),
                    row_stop=stop_row.encode(),
                    limit=limit
                ):
                    results.append({
                        'rowkey': key.decode() if isinstance(key, bytes) else key,
                        **{k.decode(): v.decode() for k, v in data.items()}
                    })
            except Exception as e:
                logger.error(f"时间范围扫描失败: {e}")
        
        self._record_metrics('scan_time_range', table_name, len(results),
                            (time.time() - query_start) * 1000, False)
        
        return results
    
    # ==================== 写入操作 ====================
    
    def batch_put(self, table_name: str, rows: List[Tuple[str, Dict]]) -> int:
        """
        批量写入
        
        Args:
            table_name: 表名
            rows: [(rowkey, {column: value}), ...]
        
        Returns:
            写入成功的行数
        """
        if not rows:
            return 0
        
        start_time = time.time()
        success_count = 0
        
        conn = self._get_connection()
        
        if conn:
            try:
                table = conn.table(table_name)
                batch = table.batch()
                
                for i, (rowkey, data) in enumerate(rows):
                    # 转换数据格式
                    hbase_data = {}
                    for col, val in data.items():
                        if ':' not in col:
                            col = f"cf:{col}"  # 默认列族
                        hbase_data[col.encode()] = str(val).encode()
                    
                    batch.put(rowkey.encode(), hbase_data)
                    
                    # 分批提交
                    if (i + 1) % self.config['batch_size'] == 0:
                        batch.send()
                        success_count += self.config['batch_size']
                
                # 提交剩余
                batch.send()
                success_count = len(rows)
                
            except Exception as e:
                logger.error(f"批量写入失败: {e}")
        else:
            # 模拟写入
            success_count = len(rows)
            logger.info(f"模拟批量写入: {success_count} 行")
        
        # 使相关缓存失效
        self._cache.invalidate(pattern=table_name)
        
        self._record_metrics('batch_put', table_name, success_count,
                            (time.time() - start_time) * 1000, False)
        
        return success_count
    
    def put_topic(self, topic_id: str, data: Dict, timestamp: datetime = None) -> str:
        """
        写入话题数据
        
        使用优化的行键设计
        """
        rowkey = self.rowkey.design_topic_rowkey(topic_id, timestamp)
        
        conn = self._get_connection()
        
        if conn:
            try:
                table = conn.table('weibo_topics')
                hbase_data = {f"cf:{k}".encode(): str(v).encode() for k, v in data.items()}
                table.put(rowkey.encode(), hbase_data)
            except Exception as e:
                logger.error(f"写入话题失败: {e}")
        
        # 使缓存失效
        self._cache.invalidate(pattern='topic')
        self._cache.invalidate(pattern='top_topics')
        
        return rowkey
    
    # ==================== 缓存管理 ====================
    
    def refresh_cache(self, key: str = None):
        """
        刷新缓存
        
        Args:
            key: 指定键，None则刷新所有
        """
        if key:
            self._cache.invalidate(key=key)
        else:
            self._cache.clear()
        
        logger.info(f"缓存已刷新: {key or 'all'}")
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        return self._cache.stats()
    
    # ==================== 性能监控 ====================
    
    def get_performance_stats(self) -> Dict:
        """获取性能统计"""
        with self._metrics_lock:
            if not self._metrics:
                return {
                    'total_queries': 0,
                    'avg_response_time_ms': 0,
                    'cache_hit_rate': 0
                }
            
            total = len(self._metrics)
            cache_hits = sum(1 for m in self._metrics if m.cache_hit)
            avg_time = sum(m.response_time_ms for m in self._metrics) / total
            
            # 按查询类型统计
            by_type = {}
            for m in self._metrics:
                if m.query_type not in by_type:
                    by_type[m.query_type] = {'count': 0, 'total_time': 0}
                by_type[m.query_type]['count'] += 1
                by_type[m.query_type]['total_time'] += m.response_time_ms
            
            for qt in by_type:
                by_type[qt]['avg_time'] = by_type[qt]['total_time'] / by_type[qt]['count']
            
            return {
                'total_queries': total,
                'avg_response_time_ms': round(avg_time, 2),
                'cache_hit_rate': round(cache_hits / total * 100, 2),
                'by_query_type': by_type
            }
    
    def get_recent_metrics(self, limit: int = 100) -> List[Dict]:
        """获取最近的查询指标"""
        with self._metrics_lock:
            return [m.to_dict() for m in self._metrics[-limit:]]
    
    # ==================== 参数调优 ====================
    
    def auto_tune(self) -> Dict:
        """
        自动调优参数
        
        基于历史性能数据调整配置
        """
        stats = self.get_performance_stats()
        suggestions = []
        changes = {}
        
        # 根据缓存命中率调整缓存大小
        if stats['cache_hit_rate'] < 50 and self.config['cache_size'] < 500:
            new_size = min(self.config['cache_size'] * 2, 500)
            changes['cache_size'] = new_size
            suggestions.append(f"缓存命中率低，增加缓存大小到 {new_size}")
        
        # 根据响应时间调整批量大小
        if stats['avg_response_time_ms'] > 100:
            if self.config['batch_size'] > 500:
                new_batch = self.config['batch_size'] // 2
                changes['batch_size'] = new_batch
                suggestions.append(f"响应时间较长，减少批量大小到 {new_batch}")
        
        # 应用更改
        for key, value in changes.items():
            self.config[key] = value
        
        if changes:
            # 重新初始化缓存
            self._cache = QueryCache(
                max_size=self.config['cache_size'],
                default_ttl=self.config['cache_ttl']
            )
        
        return {
            'changes': changes,
            'suggestions': suggestions,
            'current_config': self.config
        }
    
    # ==================== 模拟数据 ====================
    
    def _mock_top_topics(self, limit: int) -> List[Dict]:
        """生成模拟热门话题"""
        topics = [
            ('人工智能', 0.85, 95000),
            ('新能源汽车', 0.72, 82000),
            ('房价走势', -0.45, 78000),
            ('教育改革', 0.35, 65000),
            ('医疗保障', 0.28, 58000),
            ('环境保护', 0.65, 52000),
            ('科技创新', 0.78, 48000),
            ('就业形势', -0.22, 45000),
            ('消费升级', 0.42, 42000),
            ('数字经济', 0.68, 38000),
        ]
        
        results = []
        for i, (name, sentiment, heat) in enumerate(topics[:limit]):
            rowkey = self.rowkey.design_topic_rowkey(name)
            results.append({
                'rowkey': rowkey,
                'cf:name': name,
                'cf:sentiment': str(sentiment),
                'cf:heat': str(heat),
                'cf:rank': str(i + 1),
                'cf:dual_score': str(0.6 * abs(sentiment) + 0.4 * (heat / 100000))
            })
        
        return results
    
    def _mock_topic(self, topic_id: str) -> Dict:
        """生成模拟话题详情"""
        import random
        
        rowkey = self.rowkey.design_topic_rowkey(topic_id)
        return {
            'rowkey': rowkey,
            'cf:name': topic_id,
            'cf:sentiment': str(random.uniform(-1, 1)),
            'cf:heat': str(random.randint(10000, 100000)),
            'cf:weibo_count': str(random.randint(100, 10000)),
            'cf:user_count': str(random.randint(50, 5000)),
            'cf:created_at': datetime.now().isoformat()
        }


# 全局单例
_optimizer: Optional[HBaseOptimizer] = None


def get_optimizer() -> HBaseOptimizer:
    """获取优化器单例"""
    global _optimizer
    if _optimizer is None:
        _optimizer = HBaseOptimizer()
    return _optimizer


# ==================== 装饰器 ====================

def hbase_cached(ttl: int = 300):
    """
    HBase查询缓存装饰器
    
    用法:
        @hbase_cached(ttl=60)
        def get_data(key):
            return query_hbase(key)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            optimizer = get_optimizer()
            
            # 生成缓存键
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            # 查缓存
            cached = optimizer._cache.get(cache_key)
            if cached is not None:
                return cached
            
            # 执行查询
            result = func(*args, **kwargs)
            
            # 缓存结果
            if result is not None:
                optimizer._cache.put(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


if __name__ == '__main__':
    # 测试优化器
    optimizer = HBaseOptimizer()
    
    # 测试行键设计
    print("行键设计测试:")
    rowkey = optimizer.rowkey.design_topic_rowkey("人工智能")
    print(f"  话题行键: {rowkey}")
    parsed = optimizer.rowkey.parse_rowkey(rowkey)
    print(f"  解析结果: {parsed}")
    
    # 测试查询
    print("\n查询测试:")
    topics = optimizer.get_top_topics(5)
    for t in topics:
        print(f"  {t.get('cf:name', 'N/A')}: 热度={t.get('cf:heat', 'N/A')}")
    
    # 再次查询（应该命中缓存）
    topics2 = optimizer.get_top_topics(5)
    
    # 性能统计
    print("\n性能统计:")
    stats = optimizer.get_performance_stats()
    print(f"  总查询: {stats['total_queries']}")
    print(f"  平均响应: {stats['avg_response_time_ms']}ms")
    print(f"  缓存命中率: {stats['cache_hit_rate']}%")
    
    # 缓存统计
    print("\n缓存统计:")
    cache_stats = optimizer.get_cache_stats()
    print(f"  缓存大小: {cache_stats['size']}/{cache_stats['max_size']}")
