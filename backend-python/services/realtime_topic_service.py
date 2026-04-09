"""
实时热点话题服务
================

基于微博爬虫数据实时刷新热点话题分析

功能特性：
1. 实时数据监听 - 监听爬虫采集的新数据
2. 增量分析 - 只处理新增数据
3. 滑动窗口 - 支持时间窗口内的热点统计
4. 自动刷新 - 定时更新热点榜单
5. 推送通知 - 新热点出现时通知

使用示例:
    from backend.services.realtime_topic_service import RealtimeTopicService
    
    service = RealtimeTopicService()
    service.start()
    
    # 获取实时热点
    hotspots = service.get_current_hotspots()
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Callable, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from queue import Queue, Empty
import hashlib

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('RealtimeTopicService')

# 导入话题分析器
try:
    from .topic_analyzer import TopicAnalyzer, TopicConfig
except ImportError:
    from backend.services.topic_analyzer import TopicAnalyzer, TopicConfig

# 导入情感分析器
try:
    from .hybrid_analyzer import HybridSentimentAnalyzer
except ImportError:
    try:
        from backend.services.hybrid_analyzer import HybridSentimentAnalyzer
    except ImportError:
        HybridSentimentAnalyzer = None


# ==================== 配置类 ====================

@dataclass
class RealtimeConfig:
    """实时服务配置"""
    # 刷新间隔
    refresh_interval: int = 60  # 秒
    
    # 滑动窗口
    window_size: int = 3600  # 1小时窗口
    slide_interval: int = 300  # 5分钟滑动
    
    # 热点配置
    top_k_keywords: int = 50
    top_k_topics: int = 10
    min_keyword_count: int = 3  # 最小出现次数
    
    # 热点检测
    hotspot_threshold: float = 2.0  # 热度阈值（相对平均值）
    burst_threshold: float = 3.0    # 爆发阈值
    
    # 数据源
    data_dir: str = "./data/collected"
    watch_pattern: str = "*.json"
    
    # 缓存
    max_cache_size: int = 100000
    cache_ttl: int = 7200  # 2小时


@dataclass
class HotTopic:
    """热点话题"""
    keyword: str
    count: int
    trend: str  # rising, falling, stable, new, burst
    score: float
    sentiment: str  # positive, negative, neutral, mixed
    sentiment_score: float
    first_seen: str
    last_seen: str
    sample_texts: List[str] = field(default_factory=list)
    related_keywords: List[str] = field(default_factory=list)


@dataclass
class TopicSnapshot:
    """话题快照"""
    timestamp: str
    keywords: List[Dict]
    topics: List[Dict]
    sentiment_distribution: Dict
    total_count: int
    window_start: str
    window_end: str


# ==================== 数据缓冲区 ====================

class DataBuffer:
    """数据缓冲区 - 存储滑动窗口内的数据"""
    
    def __init__(self, window_size: int = 3600, max_size: int = 100000):
        self.window_size = window_size
        self.max_size = max_size
        self.data: deque = deque(maxlen=max_size)
        self.keyword_counts: Dict[str, int] = defaultdict(int)
        self.keyword_history: Dict[str, List[Tuple[float, int]]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def add(self, item: Dict):
        """添加数据项"""
        with self._lock:
            timestamp = time.time()
            item['_timestamp'] = timestamp
            self.data.append(item)
            
            # 更新关键词计数
            keywords = item.get('_keywords', [])
            for kw in keywords:
                self.keyword_counts[kw] += 1
            
            # 清理过期数据
            self._cleanup_expired()
    
    def add_batch(self, items: List[Dict]):
        """批量添加"""
        for item in items:
            self.add(item)
    
    def _cleanup_expired(self):
        """清理过期数据"""
        cutoff = time.time() - self.window_size
        
        while self.data and self.data[0].get('_timestamp', 0) < cutoff:
            old_item = self.data.popleft()
            # 减少关键词计数
            keywords = old_item.get('_keywords', [])
            for kw in keywords:
                self.keyword_counts[kw] -= 1
                if self.keyword_counts[kw] <= 0:
                    del self.keyword_counts[kw]
    
    def get_window_data(self, window_seconds: int = None) -> List[Dict]:
        """获取窗口内数据"""
        window_seconds = window_seconds or self.window_size
        cutoff = time.time() - window_seconds
        
        with self._lock:
            return [item for item in self.data if item.get('_timestamp', 0) >= cutoff]
    
    def get_keyword_counts(self) -> Dict[str, int]:
        """获取关键词计数"""
        with self._lock:
            return dict(self.keyword_counts)
    
    def get_top_keywords(self, top_k: int = 50) -> List[Tuple[str, int]]:
        """获取热门关键词"""
        with self._lock:
            sorted_keywords = sorted(
                self.keyword_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_keywords[:top_k]
    
    def record_keyword_history(self):
        """记录关键词历史（用于趋势分析）"""
        timestamp = time.time()
        with self._lock:
            for kw, count in self.keyword_counts.items():
                self.keyword_history[kw].append((timestamp, count))
                # 只保留最近1小时的历史
                cutoff = timestamp - 3600
                self.keyword_history[kw] = [
                    (t, c) for t, c in self.keyword_history[kw] if t >= cutoff
                ]
    
    def get_keyword_trend(self, keyword: str) -> str:
        """获取关键词趋势"""
        history = self.keyword_history.get(keyword, [])
        
        if len(history) < 2:
            return 'new'
        
        # 计算趋势
        recent = history[-1][1] if history else 0
        previous = history[-2][1] if len(history) >= 2 else 0
        
        if recent == 0:
            return 'falling'
        
        change_ratio = (recent - previous) / max(1, previous)
        
        if change_ratio > 0.5:
            return 'burst' if change_ratio > 1.0 else 'rising'
        elif change_ratio < -0.3:
            return 'falling'
        else:
            return 'stable'
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            return {
                'total_items': len(self.data),
                'unique_keywords': len(self.keyword_counts),
                'window_size': self.window_size,
                'oldest_timestamp': self.data[0].get('_timestamp') if self.data else None,
                'newest_timestamp': self.data[-1].get('_timestamp') if self.data else None
            }


# ==================== 文件监听器 ====================

class FileWatcher:
    """文件监听器 - 监听新数据文件"""
    
    def __init__(self, watch_dir: str, callback: Callable):
        self.watch_dir = watch_dir
        self.callback = callback
        self.processed_files: set = set()
        self._running = False
        self._thread = None
    
    def start(self):
        """开始监听"""
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logger.info(f"文件监听器已启动: {self.watch_dir}")
    
    def stop(self):
        """停止监听"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("文件监听器已停止")
    
    def _watch_loop(self):
        """监听循环"""
        while self._running:
            try:
                self._check_new_files()
            except Exception as e:
                logger.error(f"文件监听错误: {e}")
            time.sleep(5)  # 每5秒检查一次
    
    def _check_new_files(self):
        """检查新文件"""
        if not os.path.exists(self.watch_dir):
            return
        
        for filename in os.listdir(self.watch_dir):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(self.watch_dir, filename)
            file_key = f"{filename}_{os.path.getmtime(filepath)}"
            
            if file_key not in self.processed_files:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if isinstance(data, list):
                        self.callback(data)
                    elif isinstance(data, dict) and 'data' in data:
                        self.callback(data['data'])
                    
                    self.processed_files.add(file_key)
                    logger.info(f"处理新文件: {filename}")
                    
                except Exception as e:
                    logger.error(f"处理文件失败 {filename}: {e}")


# ==================== 实时话题服务 ====================

class RealtimeTopicService:
    """
    实时热点话题服务
    
    监听微博爬虫数据，实时更新热点话题分析
    """
    
    def __init__(self, config: RealtimeConfig = None):
        self.config = config or RealtimeConfig()
        
        # 初始化组件
        self.topic_analyzer = TopicAnalyzer()
        self.sentiment_analyzer = HybridSentimentAnalyzer() if HybridSentimentAnalyzer else None
        
        # 数据缓冲区
        self.buffer = DataBuffer(
            window_size=self.config.window_size,
            max_size=self.config.max_cache_size
        )
        
        # 文件监听器
        self.file_watcher = FileWatcher(
            self.config.data_dir,
            self._on_new_data
        )
        
        # 当前热点
        self.current_hotspots: List[HotTopic] = []
        self.current_snapshot: TopicSnapshot = None
        self.snapshot_history: deque = deque(maxlen=100)
        
        # 回调函数
        self.callbacks: List[Callable] = []
        
        # 运行状态
        self._running = False
        self._refresh_thread = None
        self._lock = threading.Lock()
        
        # 统计
        self.stats = {
            'total_processed': 0,
            'last_refresh': None,
            'refresh_count': 0
        }
    
    def start(self):
        """启动服务"""
        if self._running:
            return
        
        self._running = True
        
        # 启动文件监听
        self.file_watcher.start()
        
        # 启动定时刷新
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()
        
        logger.info("实时话题服务已启动")
    
    def stop(self):
        """停止服务"""
        self._running = False
        self.file_watcher.stop()
        
        if self._refresh_thread:
            self._refresh_thread.join(timeout=5)
        
        logger.info("实时话题服务已停止")
    
    def add_callback(self, callback: Callable):
        """添加热点更新回调"""
        self.callbacks.append(callback)
    
    def _on_new_data(self, data: List[Dict]):
        """处理新数据"""
        if not data:
            return
        
        # 预处理数据
        processed = self._preprocess_data(data)
        
        # 添加到缓冲区
        self.buffer.add_batch(processed)
        
        # 更新统计
        self.stats['total_processed'] += len(data)
        
        logger.info(f"处理新数据: {len(data)} 条")
    
    def _preprocess_data(self, data: List[Dict]) -> List[Dict]:
        """预处理数据"""
        processed = []
        
        for item in data:
            text = item.get('text', '')
            if not text:
                continue
            
            # 提取关键词
            try:
                import jieba
                words = list(jieba.cut(text))
                # 过滤停用词和短词
                stopwords = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都',
                            '这', '那', '他', '她', '它', '们', '什么', '怎么', '可以', '没'}
                keywords = [w for w in words if len(w) >= 2 and w not in stopwords]
            except ImportError:
                keywords = []
            
            # 情感分析
            sentiment = 'neutral'
            sentiment_score = 0.0
            if self.sentiment_analyzer:
                try:
                    result = self.sentiment_analyzer.analyze(text)
                    sentiment = result.polarity
                    sentiment_score = result.score
                except:
                    pass
            
            processed.append({
                **item,
                '_keywords': keywords[:10],  # 最多10个关键词
                '_sentiment': sentiment,
                '_sentiment_score': sentiment_score
            })
        
        return processed
    
    def _refresh_loop(self):
        """定时刷新循环"""
        while self._running:
            try:
                self._refresh_hotspots()
                
                # 记录关键词历史
                self.buffer.record_keyword_history()
                
            except Exception as e:
                logger.error(f"刷新热点失败: {e}")
            
            time.sleep(self.config.refresh_interval)
    
    def _refresh_hotspots(self):
        """刷新热点"""
        # 获取窗口数据
        window_data = self.buffer.get_window_data()
        
        if not window_data:
            return
        
        # 获取热门关键词
        top_keywords = self.buffer.get_top_keywords(self.config.top_k_keywords)
        
        # 过滤低频词
        top_keywords = [
            (kw, count) for kw, count in top_keywords
            if count >= self.config.min_keyword_count
        ]
        
        # 构建热点列表
        hotspots = []
        
        for keyword, count in top_keywords[:self.config.top_k_topics]:
            # 获取趋势
            trend = self.buffer.get_keyword_trend(keyword)
            
            # 计算热度分数
            avg_count = sum(c for _, c in top_keywords) / max(1, len(top_keywords))
            score = count / max(1, avg_count)
            
            # 获取相关微博
            related_items = [
                item for item in window_data
                if keyword in item.get('_keywords', [])
            ]
            
            # 计算情感分布
            sentiments = [item.get('_sentiment', 'neutral') for item in related_items]
            sentiment_scores = [item.get('_sentiment_score', 0) for item in related_items]
            
            pos_count = sentiments.count('positive')
            neg_count = sentiments.count('negative')
            total = len(sentiments)
            
            if pos_count > neg_count * 1.5:
                sentiment = 'positive'
            elif neg_count > pos_count * 1.5:
                sentiment = 'negative'
            elif pos_count > 0 and neg_count > 0:
                sentiment = 'mixed'
            else:
                sentiment = 'neutral'
            
            avg_sentiment = sum(sentiment_scores) / max(1, len(sentiment_scores))
            
            # 获取样本文本
            sample_texts = [
                item.get('text', '')[:100]
                for item in sorted(
                    related_items,
                    key=lambda x: (x.get('reposts_count', 0) + x.get('likes_count', 0)),
                    reverse=True
                )[:5]
            ]
            
            # 获取相关关键词
            related_keywords = []
            keyword_cooccur = defaultdict(int)
            for item in related_items:
                for kw in item.get('_keywords', []):
                    if kw != keyword:
                        keyword_cooccur[kw] += 1
            related_keywords = [
                kw for kw, _ in sorted(keyword_cooccur.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
            
            # 获取时间范围
            timestamps = [item.get('_timestamp', 0) for item in related_items]
            first_seen = datetime.fromtimestamp(min(timestamps)).isoformat() if timestamps else ''
            last_seen = datetime.fromtimestamp(max(timestamps)).isoformat() if timestamps else ''
            
            hotspots.append(HotTopic(
                keyword=keyword,
                count=count,
                trend=trend,
                score=round(score, 2),
                sentiment=sentiment,
                sentiment_score=round(avg_sentiment, 4),
                first_seen=first_seen,
                last_seen=last_seen,
                sample_texts=sample_texts,
                related_keywords=related_keywords
            ))
        
        # 更新当前热点
        with self._lock:
            old_hotspots = {h.keyword for h in self.current_hotspots}
            new_hotspots = {h.keyword for h in hotspots}
            
            # 检测新热点
            new_keywords = new_hotspots - old_hotspots
            
            self.current_hotspots = hotspots
            
            # 创建快照
            now = datetime.now()
            window_start = now - timedelta(seconds=self.config.window_size)
            
            self.current_snapshot = TopicSnapshot(
                timestamp=now.isoformat(),
                keywords=[asdict(h) for h in hotspots],
                topics=self._extract_topics(window_data),
                sentiment_distribution=self._calculate_sentiment_distribution(window_data),
                total_count=len(window_data),
                window_start=window_start.isoformat(),
                window_end=now.isoformat()
            )
            
            self.snapshot_history.append(self.current_snapshot)
        
        # 更新统计
        self.stats['last_refresh'] = datetime.now().isoformat()
        self.stats['refresh_count'] += 1
        
        # 触发回调
        if new_keywords:
            for callback in self.callbacks:
                try:
                    callback('new_hotspot', list(new_keywords), hotspots)
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")
        
        logger.info(f"热点刷新完成: {len(hotspots)} 个热点, {len(new_keywords)} 个新热点")
    
    def _extract_topics(self, data: List[Dict]) -> List[Dict]:
        """提取主题"""
        texts = [item.get('text', '') for item in data if item.get('text')]
        
        if len(texts) < 10:
            return []
        
        try:
            topics = self.topic_analyzer.topic_modeling(texts, n_topics=5)
            return topics
        except:
            return []
    
    def _calculate_sentiment_distribution(self, data: List[Dict]) -> Dict:
        """计算情感分布"""
        sentiments = [item.get('_sentiment', 'neutral') for item in data]
        total = len(sentiments)
        
        if total == 0:
            return {'positive': 0, 'negative': 0, 'neutral': 0}
        
        return {
            'positive': round(sentiments.count('positive') / total * 100, 2),
            'negative': round(sentiments.count('negative') / total * 100, 2),
            'neutral': round(sentiments.count('neutral') / total * 100, 2)
        }
    
    # ==================== 公开接口 ====================
    
    def add_data(self, data: List[Dict]):
        """手动添加数据"""
        self._on_new_data(data)
    
    def get_current_hotspots(self) -> List[Dict]:
        """获取当前热点"""
        with self._lock:
            return [asdict(h) for h in self.current_hotspots]
    
    def get_current_snapshot(self) -> Dict:
        """获取当前快照"""
        with self._lock:
            if self.current_snapshot:
                return asdict(self.current_snapshot)
            return {}
    
    def get_snapshot_history(self, limit: int = 10) -> List[Dict]:
        """获取快照历史"""
        with self._lock:
            snapshots = list(self.snapshot_history)[-limit:]
            return [asdict(s) for s in snapshots]
    
    def get_keyword_trend(self, keyword: str) -> Dict:
        """获取关键词趋势"""
        history = self.buffer.keyword_history.get(keyword, [])
        
        return {
            'keyword': keyword,
            'current_count': self.buffer.keyword_counts.get(keyword, 0),
            'trend': self.buffer.get_keyword_trend(keyword),
            'history': [
                {'timestamp': datetime.fromtimestamp(t).isoformat(), 'count': c}
                for t, c in history
            ]
        }
    
    def get_wordcloud_data(self) -> List[Dict]:
        """获取词云数据"""
        top_keywords = self.buffer.get_top_keywords(100)
        
        if not top_keywords:
            return []
        
        max_count = max(c for _, c in top_keywords)
        
        return [
            {
                'name': kw,
                'value': count,
                'textStyle': {
                    'fontSize': int(12 + (count / max_count) * 48)
                }
            }
            for kw, count in top_keywords
        ]
    
    def get_stats(self) -> Dict:
        """获取服务统计"""
        buffer_stats = self.buffer.get_stats()
        
        return {
            **self.stats,
            'buffer': buffer_stats,
            'hotspots_count': len(self.current_hotspots),
            'running': self._running
        }
    
    def force_refresh(self):
        """强制刷新"""
        self._refresh_hotspots()


# ==================== API接口扩展 ====================

# 全局服务实例
_realtime_service: RealtimeTopicService = None

def get_realtime_topic_service() -> RealtimeTopicService:
    """获取实时话题服务单例"""
    global _realtime_service
    if _realtime_service is None:
        _realtime_service = RealtimeTopicService()
    return _realtime_service


def start_realtime_service(config: RealtimeConfig = None):
    """启动实时服务"""
    service = get_realtime_topic_service()
    if config:
        service.config = config
    service.start()
    return service


def stop_realtime_service():
    """停止实时服务"""
    global _realtime_service
    if _realtime_service:
        _realtime_service.stop()


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='实时热点话题服务')
    parser.add_argument('--data-dir', type=str, default='./data/collected',
                       help='数据目录')
    parser.add_argument('--refresh-interval', type=int, default=60,
                       help='刷新间隔（秒）')
    parser.add_argument('--window-size', type=int, default=3600,
                       help='窗口大小（秒）')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("实时热点话题服务")
    print("=" * 60)
    
    # 创建配置
    config = RealtimeConfig(
        data_dir=args.data_dir,
        refresh_interval=args.refresh_interval,
        window_size=args.window_size
    )
    
    # 创建服务
    service = RealtimeTopicService(config)
    
    # 添加回调
    def on_hotspot_update(event_type, new_keywords, hotspots):
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 新热点: {', '.join(new_keywords)}")
        print(f"当前热点TOP5:")
        for h in hotspots[:5]:
            print(f"  - {h.keyword}: {h.count}次 ({h.trend}) [{h.sentiment}]")
    
    service.add_callback(on_hotspot_update)
    
    # 添加测试数据
    print("\n添加测试数据...")
    test_data = [
        {'text': '今天天气真好，出去旅游心情很棒！', 'created_at': datetime.now().isoformat()},
        {'text': '这个产品太棒了，强烈推荐！', 'created_at': datetime.now().isoformat()},
        {'text': '服务态度很差，非常失望', 'created_at': datetime.now().isoformat()},
        {'text': '新能源汽车发展很快', 'created_at': datetime.now().isoformat()},
        {'text': '人工智能改变生活', 'created_at': datetime.now().isoformat()},
    ] * 20
    
    service.add_data(test_data)
    
    # 启动服务
    print("\n启动服务...")
    service.start()
    
    try:
        print("\n服务运行中，按 Ctrl+C 停止...")
        while True:
            time.sleep(10)
            
            # 打印状态
            stats = service.get_stats()
            print(f"\n[状态] 已处理: {stats['total_processed']} | "
                  f"热点数: {stats['hotspots_count']} | "
                  f"刷新次数: {stats['refresh_count']}")
            
            # 打印当前热点
            hotspots = service.get_current_hotspots()
            if hotspots:
                print("当前热点:")
                for h in hotspots[:5]:
                    print(f"  {h['keyword']}: {h['count']}次 "
                          f"[{h['trend']}] [{h['sentiment']}]")
            
    except KeyboardInterrupt:
        print("\n\n正在停止...")
        service.stop()
        print("✅ 服务已停止")
