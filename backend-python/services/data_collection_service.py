"""
统一数据采集服务
================

整合多种数据采集方式，提供统一的API接口：
1. 微博API采集
2. 网页爬虫采集
3. 热搜榜单采集

作者：毕业设计
日期：2026-01
"""

import os
import json
import time
import random
import logging
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CollectionMethod(Enum):
    """采集方式枚举"""
    API = "api"           # 微博API
    CRAWLER = "crawler"   # 网页爬虫
    HOT_SEARCH = "hot_search"  # 热搜榜单


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CollectionConfig:
    """采集配置"""
    keywords: List[str] = field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_count: int = 100
    method: CollectionMethod = CollectionMethod.CRAWLER
    use_proxy: bool = False
    request_interval: float = 1.0  # 请求间隔（秒）


@dataclass
class CollectionTask:
    """采集任务"""
    task_id: str
    config: CollectionConfig
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    collected_count: int = 0
    failed_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class WeiboItem:
    """微博数据项"""
    id: str
    mid: str
    text: str
    user_id: str
    user_name: str
    created_at: str
    reposts_count: int = 0
    comments_count: int = 0
    attitudes_count: int = 0
    source: str = ""
    raw_data: Optional[Dict] = None


class BaseCollector(ABC):
    """采集器基类"""
    
    @abstractmethod
    def collect(self, config: CollectionConfig, callback: Optional[Callable] = None) -> List[WeiboItem]:
        """执行采集"""
        pass
    
    @abstractmethod
    def stop(self):
        """停止采集"""
        pass


class CrawlerCollector(BaseCollector):
    """网页爬虫采集器"""
    
    def __init__(self):
        self._running = False
        self._ua_pool = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        ]
    
    def collect(self, config: CollectionConfig, callback: Optional[Callable] = None) -> List[WeiboItem]:
        """执行爬虫采集"""
        self._running = True
        results = []
        
        try:
            for i, keyword in enumerate(config.keywords):
                if not self._running:
                    break
                
                logger.info(f"采集关键词: {keyword}")
                
                # 模拟采集过程（实际项目中应调用真实爬虫）
                items = self._crawl_keyword(keyword, config.max_count // len(config.keywords))
                results.extend(items)
                
                if callback:
                    progress = (i + 1) / len(config.keywords) * 100
                    callback(progress, len(results))
                
                # 请求间隔
                if self._running and i < len(config.keywords) - 1:
                    time.sleep(config.request_interval)
        
        except Exception as e:
            logger.error(f"爬虫采集失败: {e}")
        
        self._running = False
        return results
    
    def _crawl_keyword(self, keyword: str, max_count: int) -> List[WeiboItem]:
        """采集单个关键词"""
        # 这里应该调用实际的爬虫逻辑
        # 为了演示，返回模拟数据
        items = []
        for i in range(min(max_count, 20)):
            items.append(WeiboItem(
                id=f"crawl_{keyword}_{i}_{random.randint(10000, 99999)}",
                mid=f"49{random.randint(10000000000, 99999999999)}",
                text=f"关于{keyword}的微博内容示例 #{keyword}#",
                user_id=f"user_{random.randint(1000, 9999)}",
                user_name=f"用户{random.randint(100, 999)}",
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                reposts_count=random.randint(0, 100),
                comments_count=random.randint(0, 50),
                attitudes_count=random.randint(0, 200),
                source="微博 weibo.com"
            ))
        return items
    
    def stop(self):
        """停止采集"""
        self._running = False


class HotSearchCollector(BaseCollector):
    """热搜榜单采集器"""
    
    def __init__(self):
        self._running = False
    
    def collect(self, config: CollectionConfig, callback: Optional[Callable] = None) -> List[WeiboItem]:
        """采集热搜榜单"""
        self._running = True
        results = []
        
        try:
            # 模拟热搜数据
            hot_topics = [
                "人工智能", "新能源汽车", "元宇宙", "碳中和",
                "数字经济", "乡村振兴", "健康生活", "科技创新"
            ]
            
            for i, topic in enumerate(hot_topics[:config.max_count]):
                if not self._running:
                    break
                
                results.append(WeiboItem(
                    id=f"hot_{i}_{random.randint(10000, 99999)}",
                    mid=f"49{random.randint(10000000000, 99999999999)}",
                    text=f"#{topic}# 热搜话题讨论",
                    user_id=f"user_{random.randint(1000, 9999)}",
                    user_name=f"热搜用户{i}",
                    created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    reposts_count=random.randint(1000, 10000),
                    comments_count=random.randint(500, 5000),
                    attitudes_count=random.randint(2000, 20000),
                    source="微博热搜"
                ))
                
                if callback:
                    callback((i + 1) / len(hot_topics) * 100, len(results))
        
        except Exception as e:
            logger.error(f"热搜采集失败: {e}")
        
        self._running = False
        return results
    
    def stop(self):
        """停止采集"""
        self._running = False


class DataCollectionService:
    """统一数据采集服务"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.collectors = {
            CollectionMethod.CRAWLER: CrawlerCollector(),
            CollectionMethod.HOT_SEARCH: HotSearchCollector(),
        }
        self.tasks: Dict[str, CollectionTask] = {}
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data'
        )
        os.makedirs(self.data_dir, exist_ok=True)
        self._initialized = True
        logger.info("统一数据采集服务初始化完成")
    
    def create_task(self, config: CollectionConfig) -> str:
        """创建采集任务"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"
        task = CollectionTask(task_id=task_id, config=config)
        self.tasks[task_id] = task
        logger.info(f"创建采集任务: {task_id}")
        return task_id
    
    def start_task(self, task_id: str, async_mode: bool = True) -> bool:
        """启动采集任务"""
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return False
        
        if task.status == TaskStatus.RUNNING:
            logger.warning(f"任务已在运行: {task_id}")
            return False
        
        task.status = TaskStatus.RUNNING
        task.start_time = datetime.now()
        
        if async_mode:
            thread = threading.Thread(target=self._run_task, args=(task_id,))
            thread.daemon = True
            thread.start()
        else:
            self._run_task(task_id)
        
        return True
    
    def _run_task(self, task_id: str):
        """执行采集任务"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        try:
            collector = self.collectors.get(task.config.method)
            if not collector:
                raise ValueError(f"不支持的采集方式: {task.config.method}")
            
            def progress_callback(progress: float, count: int):
                task.progress = progress
                task.collected_count = count
            
            results = collector.collect(task.config, progress_callback)
            
            # 保存结果
            self._save_results(task_id, results)
            
            task.status = TaskStatus.COMPLETED
            task.progress = 100.0
            task.collected_count = len(results)
            logger.info(f"任务完成: {task_id}, 采集{len(results)}条数据")
        
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            logger.error(f"任务失败: {task_id}, 错误: {e}")
        
        finally:
            task.end_time = datetime.now()
    
    def stop_task(self, task_id: str) -> bool:
        """停止采集任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        collector = self.collectors.get(task.config.method)
        if collector:
            collector.stop()
        
        task.status = TaskStatus.PAUSED
        return True
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            'task_id': task.task_id,
            'status': task.status.value,
            'progress': task.progress,
            'collected_count': task.collected_count,
            'failed_count': task.failed_count,
            'start_time': task.start_time.isoformat() if task.start_time else None,
            'end_time': task.end_time.isoformat() if task.end_time else None,
            'error_message': task.error_message
        }
    
    def _save_results(self, task_id: str, results: List[WeiboItem]):
        """保存采集结果"""
        filename = f"crawl_result_{task_id}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        data = [
            {
                'id': item.id,
                'mid': item.mid,
                'text': item.text,
                'user': {
                    'id': item.user_id,
                    'screen_name': item.user_name
                },
                'created_at': item.created_at,
                'reposts_count': item.reposts_count,
                'comments_count': item.comments_count,
                'attitudes_count': item.attitudes_count,
                'source': item.source,
                'crawl_time': datetime.now().isoformat()
            }
            for item in results
        ]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"保存采集结果: {filepath}")
    
    def list_tasks(self) -> List[Dict]:
        """列出所有任务"""
        return [self.get_task_status(tid) for tid in self.tasks.keys()]


# 便捷函数
def collect_weibo(
    keywords: List[str],
    max_count: int = 100,
    method: str = 'crawler'
) -> str:
    """快速采集微博数据（便捷函数）"""
    service = DataCollectionService()
    config = CollectionConfig(
        keywords=keywords,
        max_count=max_count,
        method=CollectionMethod(method) if method in [m.value for m in CollectionMethod] else CollectionMethod.CRAWLER
    )
    task_id = service.create_task(config)
    service.start_task(task_id, async_mode=False)
    return task_id
