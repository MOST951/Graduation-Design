"""
微博数据采集系统 - 主模块
=========================

功能特性：
1. 双采集模式：API模式 + Selenium爬虫模式
2. 反爬策略：动态代理IP池、UA轮换、请求频率控制、Cookie池管理
3. 增量采集：时间戳增量更新、断点续传、MD5去重
4. 多数据源：热搜榜、话题/超话、用户主页、关键词搜索
5. 数据质量：实时验证、异常过滤、完整性检查、日志记录

使用示例:
    collector = WeiboDataCollector()
    
    # 关键词采集
    weibos = collector.collect_by_keyword('人工智能', limit=100)
    
    # 热搜采集
    hot_search = collector.collect_hot_search()
    
    # 用户时间线采集
    user_weibos = collector.collect_user_timeline('1234567890', limit=50)
    
    # 增量采集
    collector.incremental_collection(task_id='task_001')
"""

import os
import json
import time
import random
import hashlib
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Generator, Callable, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from .proxy_pool import ProxyPool
from .ua_pool import UserAgentPool
from .cookie_pool import CookiePool
from .local_cache import LocalCache
from .weibo_api_client import WeiboAPIClient

# 配置日志
log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(log_dir, 'collector.log'),
            encoding='utf-8',
            mode='a'
        )
    ]
)
logger = logging.getLogger('WeiboCollector')


# ==================== 数据模型 ====================

class CollectionMode(Enum):
    """采集模式"""
    API = "api"
    SPIDER = "spider"
    SELENIUM = "selenium"
    AUTO = "auto"


class DataSource(Enum):
    """数据源类型"""
    HOT_SEARCH = "hot_search"
    TOPIC = "topic"
    SUPER_TOPIC = "super_topic"
    USER_TIMELINE = "user_timeline"
    KEYWORD_SEARCH = "keyword_search"
    COMMENT = "comment"


@dataclass
class CollectionTask:
    """采集任务"""
    task_id: str
    source: DataSource
    params: Dict[str, Any]
    status: str = "pending"  # pending, running, paused, completed, failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    progress: Dict = field(default_factory=dict)
    result_count: int = 0
    error_message: str = ""
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['source'] = self.source.value
        return result


# ==================== 数据验证器 ====================

class DataValidator:
    """数据质量验证器"""
    
    @staticmethod
    def validate_weibo(weibo: Dict) -> tuple:
        """
        验证微博数据
        
        Returns:
            (is_valid, error_message)
        """
        # 必需字段检查
        required_fields = ['id', 'text', 'user_id']
        for field in required_fields:
            if not weibo.get(field):
                return False, f"缺少必需字段: {field}"
        
        # 文本长度检查
        text = weibo.get('text', '')
        if len(text) < 2:
            return False, "文本内容过短"
        
        # 过滤广告/垃圾内容
        spam_keywords = ['加微信', '加V信', '私信我', '点击链接', '免费领取']
        for keyword in spam_keywords:
            if keyword in text:
                return False, f"疑似垃圾内容: {keyword}"
        
        return True, ""
    
    @staticmethod
    def validate_hot_search(item: Dict) -> tuple:
        """验证热搜数据"""
        if not item.get('title'):
            return False, "缺少标题"
        if not item.get('rank'):
            return False, "缺少排名"
        return True, ""
    
    @staticmethod
    def check_completeness(weibo: Dict) -> float:
        """
        检查数据完整性
        
        Returns:
            完整性分数 (0-1)
        """
        fields = ['id', 'mid', 'text', 'source', 'created_at', 
                  'user_id', 'user_name', 'reposts_count', 
                  'comments_count', 'attitudes_count']
        
        filled = sum(1 for f in fields if weibo.get(f) not in [None, '', 0])
        return filled / len(fields)


# ==================== 主采集器类 ====================

class WeiboDataCollector:
    """
    微博数据采集器
    
    整合所有采集功能的主类，提供：
    - 多模式采集（API/Spider/Selenium）
    - 反爬策略
    - 增量采集
    - 数据质量保证
    """
    
    def __init__(self, 
                 use_proxy: bool = False,
                 use_selenium: bool = False,
                 data_dir: str = None):
        """
        初始化采集器
        
        Args:
            use_proxy: 是否使用代理池
            use_selenium: 是否启用Selenium模式
            data_dir: 数据存储目录
        """
        # 初始化组件
        self.proxy_pool = ProxyPool() if use_proxy else None
        self.cookie_pool = CookiePool()
        self.cache = LocalCache()
        self.api_client = WeiboAPIClient(self.cookie_pool, self.proxy_pool)
        
        # Selenium爬虫（延迟初始化）
        self.use_selenium = use_selenium
        self._selenium_spider = None
        
        # 数据存储目录
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(__file__), '..', 'data', 'collected'
        )
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 任务管理
        self._tasks: Dict[str, CollectionTask] = {}
        self._running = False
        
        # 统计信息
        self.stats = {
            'total_collected': 0,
            'duplicates_skipped': 0,
            'invalid_filtered': 0,
            'api_requests': 0,
            'start_time': None
        }
        
        logger.info(f"WeiboDataCollector初始化完成 (proxy={use_proxy}, selenium={use_selenium})")
    
    # ==================== 关键词采集 ====================
    
    def collect_by_keyword(self, keyword: str, 
                           start_date: datetime = None,
                           end_date: datetime = None,
                           limit: int = 1000,
                           search_type: str = 'all',
                           deduplicate: bool = True,
                           validate: bool = True) -> List[Dict]:
        """
        关键词采集
        
        Args:
            keyword: 搜索关键词
            start_date: 开始日期（用于过滤）
            end_date: 结束日期（用于过滤）
            limit: 最大采集数量
            search_type: 搜索类型 (all/hot/ori/pic/video)
            deduplicate: 是否去重
            validate: 是否验证数据
            
        Returns:
            微博数据列表
        """
        logger.info(f"开始关键词采集: '{keyword}' (limit={limit}, type={search_type})")
        
        all_weibos = []
        page = 1
        max_pages = (limit // 10) + 5  # 预估页数
        
        while len(all_weibos) < limit and page <= max_pages:
            logger.debug(f"采集第 {page} 页...")
            
            # API采集
            weibos = self.api_client.search_weibo(keyword, page, search_type)
            
            if not weibos:
                logger.info(f"第 {page} 页无数据，停止采集")
                break
            
            # 处理每条微博
            for weibo in weibos:
                # 去重检查
                if deduplicate:
                    content_hash = weibo.get('content_hash', '')
                    if self.cache.has_hash(content_hash):
                        self.stats['duplicates_skipped'] += 1
                        continue
                    self.cache.add_hash(content_hash)
                
                # 数据验证
                if validate:
                    is_valid, error = DataValidator.validate_weibo(weibo)
                    if not is_valid:
                        self.stats['invalid_filtered'] += 1
                        logger.debug(f"过滤无效数据: {error}")
                        continue
                
                # 日期过滤
                if start_date or end_date:
                    created_at = self._parse_weibo_time(weibo.get('created_at', ''))
                    if start_date and created_at < start_date:
                        continue
                    if end_date and created_at > end_date:
                        continue
                
                all_weibos.append(weibo)
                self.stats['total_collected'] += 1
                
                if len(all_weibos) >= limit:
                    break
            
            page += 1
            self.stats['api_requests'] += 1
        
        logger.info(f"关键词采集完成: '{keyword}' 共 {len(all_weibos)} 条")
        return all_weibos
    
    # ==================== 热搜采集 ====================
    
    def collect_hot_search(self, 
                           collect_weibos: bool = False,
                           weibos_per_topic: int = 20) -> Dict:
        """
        热搜榜采集
        
        Args:
            collect_weibos: 是否同时采集热搜话题的微博
            weibos_per_topic: 每个话题采集的微博数量
            
        Returns:
            {
                'hot_search': [...],  # 热搜列表
                'weibos': [...],      # 相关微博（如果collect_weibos=True）
                'crawl_time': '...'
            }
        """
        logger.info("开始热搜榜采集...")
        
        result = {
            'hot_search': [],
            'weibos': [],
            'crawl_time': datetime.now().isoformat()
        }
        
        # 获取热搜榜
        hot_list = self.api_client.get_hot_search()
        
        # 验证热搜数据
        for item in hot_list:
            is_valid, error = DataValidator.validate_hot_search(item)
            if is_valid:
                result['hot_search'].append(item)
            else:
                logger.debug(f"过滤无效热搜: {error}")
        
        logger.info(f"获取到 {len(result['hot_search'])} 条热搜")
        
        # 采集热搜话题的微博
        if collect_weibos and result['hot_search']:
            logger.info(f"开始采集热搜话题微博 (每个话题 {weibos_per_topic} 条)...")
            
            for hot in result['hot_search'][:10]:  # 只采集前10个热搜
                topic = hot.get('title', '')
                if not topic:
                    continue
                
                weibos = self.collect_by_keyword(
                    topic, 
                    limit=weibos_per_topic,
                    deduplicate=True,
                    validate=True
                )
                
                for weibo in weibos:
                    weibo['hot_search_rank'] = hot.get('rank')
                    weibo['hot_search_title'] = topic
                
                result['weibos'].extend(weibos)
            
            logger.info(f"热搜话题微博采集完成，共 {len(result['weibos'])} 条")
        
        return result
    
    # ==================== 用户时间线采集 ====================
    
    def collect_user_timeline(self, user_id: str, 
                              limit: int = 500,
                              since_date: datetime = None) -> List[Dict]:
        """
        用户时间线采集
        
        Args:
            user_id: 用户ID
            limit: 最大采集数量
            since_date: 只采集此日期之后的微博
            
        Returns:
            微博列表
        """
        logger.info(f"开始用户时间线采集: user_id={user_id} (limit={limit})")
        
        all_weibos = []
        since_id = ''
        page = 1
        max_pages = (limit // 10) + 5
        
        while len(all_weibos) < limit and page <= max_pages:
            weibos, next_since_id = self.api_client.get_user_timeline(
                user_id, page, since_id
            )
            
            if not weibos:
                break
            
            for weibo in weibos:
                # 去重
                content_hash = weibo.get('content_hash', '')
                if self.cache.has_hash(content_hash):
                    self.stats['duplicates_skipped'] += 1
                    continue
                self.cache.add_hash(content_hash)
                
                # 日期过滤
                if since_date:
                    created_at = self._parse_weibo_time(weibo.get('created_at', ''))
                    if created_at < since_date:
                        logger.info(f"达到日期限制，停止采集")
                        return all_weibos
                
                # 验证
                is_valid, _ = DataValidator.validate_weibo(weibo)
                if is_valid:
                    all_weibos.append(weibo)
                    self.stats['total_collected'] += 1
                
                if len(all_weibos) >= limit:
                    break
            
            since_id = next_since_id
            if not since_id:
                break
            
            page += 1
            self.stats['api_requests'] += 1
        
        logger.info(f"用户时间线采集完成: {len(all_weibos)} 条")
        return all_weibos
    
    # ==================== 话题采集 ====================
    
    def collect_topic(self, topic: str, 
                      limit: int = 200,
                      pages: int = 10) -> List[Dict]:
        """
        话题/超话采集
        
        Args:
            topic: 话题名称（不含#）
            limit: 最大采集数量
            pages: 最大页数
            
        Returns:
            微博列表
        """
        logger.info(f"开始话题采集: #{topic}# (limit={limit})")
        
        all_weibos = []
        
        for page in range(1, pages + 1):
            if len(all_weibos) >= limit:
                break
            
            weibos = self.api_client.get_topic_weibo(topic, page)
            
            if not weibos:
                break
            
            for weibo in weibos:
                # 去重
                content_hash = weibo.get('content_hash', '')
                if self.cache.has_hash(content_hash):
                    continue
                self.cache.add_hash(content_hash)
                
                # 验证
                is_valid, _ = DataValidator.validate_weibo(weibo)
                if is_valid:
                    all_weibos.append(weibo)
                    self.stats['total_collected'] += 1
                
                if len(all_weibos) >= limit:
                    break
            
            self.stats['api_requests'] += 1
        
        logger.info(f"话题采集完成: #{topic}# 共 {len(all_weibos)} 条")
        return all_weibos
    
    # ==================== 增量采集 ====================
    
    def incremental_collection(self, task_id: str,
                               source: DataSource = DataSource.KEYWORD_SEARCH,
                               params: Dict = None,
                               resume: bool = True) -> List[Dict]:
        """
        增量采集（支持断点续传）
        
        Args:
            task_id: 任务ID
            source: 数据源类型
            params: 采集参数
            resume: 是否从断点恢复
            
        Returns:
            采集的数据列表
        """
        logger.info(f"开始增量采集: task_id={task_id}")
        
        # 尝试恢复断点
        checkpoint = None
        if resume:
            checkpoint = self.cache.load_checkpoint(task_id)
            if checkpoint:
                logger.info(f"从断点恢复: page={checkpoint.get('page')}, count={checkpoint.get('count')}")
        
        # 创建/更新任务
        task = CollectionTask(
            task_id=task_id,
            source=source,
            params=params or {},
            status="running",
            progress=checkpoint or {'page': 1, 'count': 0}
        )
        self._tasks[task_id] = task
        
        all_weibos = []
        start_page = task.progress.get('page', 1)
        
        try:
            if source == DataSource.KEYWORD_SEARCH:
                keyword = params.get('keyword', '')
                limit = params.get('limit', 1000)
                
                page = start_page
                while len(all_weibos) < limit:
                    weibos = self.api_client.search_weibo(keyword, page)
                    
                    if not weibos:
                        break
                    
                    for weibo in weibos:
                        # 增量检查：跳过已采集的
                        content_hash = weibo.get('content_hash', '')
                        if self.cache.has_hash(content_hash):
                            continue
                        self.cache.add_hash(content_hash)
                        
                        is_valid, _ = DataValidator.validate_weibo(weibo)
                        if is_valid:
                            all_weibos.append(weibo)
                        
                        if len(all_weibos) >= limit:
                            break
                    
                    # 保存断点
                    task.progress = {'page': page + 1, 'count': len(all_weibos)}
                    self.cache.save_checkpoint(task_id, task.progress)
                    
                    page += 1
            
            elif source == DataSource.HOT_SEARCH:
                result = self.collect_hot_search(
                    collect_weibos=params.get('collect_weibos', False),
                    weibos_per_topic=params.get('weibos_per_topic', 20)
                )
                all_weibos = result.get('weibos', [])
            
            elif source == DataSource.USER_TIMELINE:
                all_weibos = self.collect_user_timeline(
                    user_id=params.get('user_id', ''),
                    limit=params.get('limit', 500)
                )
            
            # 任务完成
            task.status = "completed"
            task.result_count = len(all_weibos)
            task.updated_at = datetime.now().isoformat()
            
            # 删除断点
            self.cache.delete_checkpoint(task_id)
            
            logger.info(f"增量采集完成: task_id={task_id}, count={len(all_weibos)}")
            
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            logger.error(f"增量采集失败: {e}")
            raise
        
        return all_weibos
    
    # ==================== 反爬策略 ====================
    
    def anti_anti_spider(self):
        """
        反反爬策略
        
        执行：
        - 刷新代理池
        - 验证Cookie
        - 重置请求计数
        """
        logger.info("执行反反爬策略...")
        
        # 刷新代理池
        if self.proxy_pool:
            self.proxy_pool.refresh_pool()
            logger.info(f"代理池刷新完成: {self.proxy_pool.size} 个代理")
        
        # 验证Cookie
        valid_count = 0
        for i, cookie in enumerate(self.cookie_pool.cookies):
            if self.cookie_pool.validate_cookie(cookie):
                valid_count += 1
            else:
                self.cookie_pool.mark_failed(i)
        
        logger.info(f"Cookie验证完成: {valid_count}/{self.cookie_pool.size} 有效")
        
        # 重置统计
        self.api_client.request_count = 0
        
        # 随机延迟
        time.sleep(random.uniform(5, 10))
        
        logger.info("反反爬策略执行完成")
    
    # ==================== 数据存储 ====================
    
    def save_data(self, data: List[Dict], filename: str = None,
                  format: str = 'json') -> str:
        """
        保存采集数据
        
        Args:
            data: 数据列表
            filename: 文件名（不含扩展名）
            format: 保存格式 (json/csv)
            
        Returns:
            保存的文件路径
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"weibo_data_{timestamp}"
        
        if format == 'json':
            filepath = os.path.join(self.data_dir, f"{filename}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        elif format == 'csv':
            import csv
            filepath = os.path.join(self.data_dir, f"{filename}.csv")
            if data:
                with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        else:
            raise ValueError(f"不支持的格式: {format}")
        
        logger.info(f"数据已保存: {filepath} ({len(data)} 条)")
        return filepath
    
    # ==================== 辅助方法 ====================
    
    def _parse_weibo_time(self, time_str: str) -> datetime:
        """解析微博时间格式"""
        if not time_str:
            return datetime.now()
        
        try:
            # 处理 "刚刚"
            if '刚刚' in time_str:
                return datetime.now()
            # 处理 "x分钟前"
            if '分钟前' in time_str:
                import re
                minutes = int(re.search(r'(\d+)', time_str).group(1))
                return datetime.now() - timedelta(minutes=minutes)
            # 处理 "x小时前"
            if '小时前' in time_str:
                import re
                hours = int(re.search(r'(\d+)', time_str).group(1))
                return datetime.now() - timedelta(hours=hours)
            # 处理 "昨天 HH:MM"
            if '昨天' in time_str:
                return datetime.now() - timedelta(days=1)
            # 处理标准格式
            if 'T' in time_str:
                return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            # 处理 "Wed Dec 10 ..." 格式
            try:
                return datetime.strptime(time_str, '%a %b %d %H:%M:%S %z %Y')
            except:
                pass
        except:
            pass
        
        return datetime.now()
    
    def get_stats(self) -> Dict:
        """获取采集统计信息"""
        return {
            **self.stats,
            'api_stats': self.api_client.get_stats(),
            'cache_stats': self.cache.get_stats(),
            'cookie_pool_size': self.cookie_pool.size,
            'proxy_pool_size': self.proxy_pool.size if self.proxy_pool else 0,
            'ua_pool_size': UserAgentPool.count(),
            'tasks': {k: v.to_dict() for k, v in self._tasks.items()}
        }
    
    def get_task(self, task_id: str) -> Optional[CollectionTask]:
        """获取任务信息"""
        return self._tasks.get(task_id)
    
    def list_tasks(self) -> List[Dict]:
        """列出所有任务"""
        return [t.to_dict() for t in self._tasks.values()]
    
    def cleanup(self):
        """清理资源"""
        self.cache.save_all()
        logger.info("资源清理完成")


# ==================== 便捷函数 ====================

def quick_collect_keyword(keyword: str, limit: int = 100) -> List[Dict]:
    """快速关键词采集"""
    collector = WeiboDataCollector()
    return collector.collect_by_keyword(keyword, limit=limit)


def quick_collect_hot_search(with_weibos: bool = False) -> Dict:
    """快速热搜采集"""
    collector = WeiboDataCollector()
    return collector.collect_hot_search(collect_weibos=with_weibos)


def quick_collect_user(user_id: str, limit: int = 100) -> List[Dict]:
    """快速用户采集"""
    collector = WeiboDataCollector()
    return collector.collect_user_timeline(user_id, limit=limit)


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='微博数据采集器')
    parser.add_argument('--keyword', type=str, help='搜索关键词')
    parser.add_argument('--hot', action='store_true', help='采集热搜')
    parser.add_argument('--user', type=str, help='用户ID')
    parser.add_argument('--topic', type=str, help='话题名称')
    parser.add_argument('--limit', type=int, default=100, help='采集数量限制')
    parser.add_argument('--output', type=str, help='输出文件名')
    parser.add_argument('--proxy', action='store_true', help='使用代理')
    
    args = parser.parse_args()
    
    collector = WeiboDataCollector(use_proxy=args.proxy)
    
    try:
        if args.keyword:
            data = collector.collect_by_keyword(args.keyword, limit=args.limit)
            collector.save_data(data, args.output or f"keyword_{args.keyword}")
            
        elif args.hot:
            result = collector.collect_hot_search(collect_weibos=True)
            collector.save_data(result['hot_search'], args.output or 'hot_search')
            if result['weibos']:
                collector.save_data(result['weibos'], f"{args.output or 'hot_search'}_weibos")
            
        elif args.user:
            data = collector.collect_user_timeline(args.user, limit=args.limit)
            collector.save_data(data, args.output or f"user_{args.user}")
            
        elif args.topic:
            data = collector.collect_topic(args.topic, limit=args.limit)
            collector.save_data(data, args.output or f"topic_{args.topic}")
            
        else:
            parser.print_help()
        
        # 打印统计信息
        print("\n采集统计:")
        stats = collector.get_stats()
        print(f"  总采集数: {stats['total_collected']}")
        print(f"  去重跳过: {stats['duplicates_skipped']}")
        print(f"  无效过滤: {stats['invalid_filtered']}")
        print(f"  API请求数: {stats['api_requests']}")
        
    finally:
        collector.cleanup()
