"""
本地缓存模块（Redis替代方案）
============================

功能：
- 去重检查（MD5哈希）
- 断点续传状态
- 临时数据存储
"""

import os
import json
import time
import pickle
import threading
import logging
from typing import Dict, Any, Optional, Set

logger = logging.getLogger('LocalCache')


class LocalCache:
    """
    本地缓存（Redis替代方案）
    
    用于：
    - 去重检查
    - 断点续传状态
    - 临时数据存储
    """
    
    def __init__(self, cache_dir: str = None, max_size: int = 100000):
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(__file__), '..', 'data', 'cache'
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.max_size = max_size
        self._memory_cache: Dict[str, Any] = {}
        self._hash_set: Set[str] = set()
        self.lock = threading.Lock()
        
        # 加载持久化的哈希集
        self._load_hash_set()
    
    def _load_hash_set(self):
        """加载持久化的哈希集"""
        hash_file = os.path.join(self.cache_dir, 'content_hashes.pkl')
        if os.path.exists(hash_file):
            try:
                with open(hash_file, 'rb') as f:
                    self._hash_set = pickle.load(f)
                logger.info(f"加载了 {len(self._hash_set)} 个内容哈希")
            except Exception as e:
                logger.warning(f"加载哈希集失败: {e}")
                self._hash_set = set()
    
    def _save_hash_set(self):
        """保存哈希集"""
        hash_file = os.path.join(self.cache_dir, 'content_hashes.pkl')
        try:
            with open(hash_file, 'wb') as f:
                pickle.dump(self._hash_set, f)
        except Exception as e:
            logger.error(f"保存哈希集失败: {e}")
    
    def set(self, key: str, value: Any, expire: int = None):
        """设置缓存"""
        with self.lock:
            self._memory_cache[key] = {
                'value': value,
                'expire': time.time() + expire if expire else None
            }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self.lock:
            if key in self._memory_cache:
                item = self._memory_cache[key]
                if item['expire'] is None or item['expire'] > time.time():
                    return item['value']
                else:
                    del self._memory_cache[key]
            return None
    
    def delete(self, key: str):
        """删除缓存"""
        with self.lock:
            self._memory_cache.pop(key, None)
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return self.get(key) is not None
    
    def add_hash(self, content_hash: str) -> bool:
        """
        添加内容哈希（用于去重）
        
        Returns:
            True 如果是新哈希，False 如果已存在
        """
        with self.lock:
            if content_hash in self._hash_set:
                return False
            self._hash_set.add(content_hash)
            
            # 定期保存
            if len(self._hash_set) % 1000 == 0:
                self._save_hash_set()
            
            return True
    
    def has_hash(self, content_hash: str) -> bool:
        """检查哈希是否存在"""
        return content_hash in self._hash_set
    
    def clear_hashes(self):
        """清空哈希集"""
        with self.lock:
            self._hash_set.clear()
            self._save_hash_set()
    
    def save_checkpoint(self, task_id: str, checkpoint: Dict):
        """保存断点"""
        checkpoint_file = os.path.join(self.cache_dir, f'checkpoint_{task_id}.json')
        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, ensure_ascii=False, indent=2)
            logger.debug(f"保存断点: {task_id}")
        except Exception as e:
            logger.error(f"保存断点失败: {e}")
    
    def load_checkpoint(self, task_id: str) -> Optional[Dict]:
        """加载断点"""
        checkpoint_file = os.path.join(self.cache_dir, f'checkpoint_{task_id}.json')
        if os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载断点失败: {e}")
        return None
    
    def delete_checkpoint(self, task_id: str):
        """删除断点"""
        checkpoint_file = os.path.join(self.cache_dir, f'checkpoint_{task_id}.json')
        if os.path.exists(checkpoint_file):
            try:
                os.remove(checkpoint_file)
            except Exception as e:
                logger.warning(f"删除断点失败: {e}")
    
    def list_checkpoints(self) -> list:
        """列出所有断点"""
        checkpoints = []
        for f in os.listdir(self.cache_dir):
            if f.startswith('checkpoint_') and f.endswith('.json'):
                task_id = f[11:-5]  # 去掉 'checkpoint_' 和 '.json'
                checkpoints.append(task_id)
        return checkpoints
    
    def cleanup_expired(self):
        """清理过期缓存"""
        with self.lock:
            current_time = time.time()
            expired_keys = [
                k for k, v in self._memory_cache.items()
                if v['expire'] is not None and v['expire'] < current_time
            ]
            for key in expired_keys:
                del self._memory_cache[key]
            logger.debug(f"清理了 {len(expired_keys)} 个过期缓存")
    
    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        return {
            'memory_cache_size': len(self._memory_cache),
            'hash_set_size': len(self._hash_set),
            'cache_dir': self.cache_dir
        }
    
    def save_all(self):
        """保存所有数据"""
        self._save_hash_set()
        logger.info("缓存数据已保存")
