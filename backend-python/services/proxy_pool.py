"""
代理IP池管理模块
================

功能：
- 动态代理IP池管理
- 代理有效性验证
- 失败代理自动剔除
- 代理评分机制
"""

import os
import json
import time
import random
import threading
import logging
from typing import List, Dict, Optional

import requests

logger = logging.getLogger('ProxyPool')


class ProxyPool:
    """
    动态代理IP池
    
    功能：
    - 自动获取免费代理
    - 代理有效性验证
    - 失败代理自动剔除
    - 代理评分机制
    """
    
    # 免费代理API列表
    PROXY_APIS = [
        "https://www.proxy-list.download/api/v1/get?type=http",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all",
    ]
    
    def __init__(self, min_pool_size: int = 10, validate_timeout: int = 5):
        self.proxies: List[Dict] = []
        self.min_pool_size = min_pool_size
        self.validate_timeout = validate_timeout
        self.lock = threading.Lock()
        self._failed_proxies: Dict[str, int] = {}
        self._proxy_scores: Dict[str, float] = {}
        
        # 加载本地代理配置
        self._load_local_proxies()
    
    def _load_local_proxies(self):
        """加载本地代理配置"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'proxies.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    local_proxies = json.load(f)
                for proxy in local_proxies:
                    self.add_proxy(proxy.get('http') or proxy.get('https'))
                logger.info(f"加载了 {len(local_proxies)} 个本地代理")
            except Exception as e:
                logger.warning(f"加载本地代理失败: {e}")
    
    def add_proxy(self, proxy_url: str, score: float = 1.0):
        """添加代理"""
        if not proxy_url:
            return
        with self.lock:
            proxy_dict = {'http': proxy_url, 'https': proxy_url}
            if proxy_dict not in self.proxies:
                self.proxies.append(proxy_dict)
                self._proxy_scores[proxy_url] = score
    
    def get_proxy(self) -> Optional[Dict]:
        """获取一个可用代理（基于评分的加权随机）"""
        with self.lock:
            if not self.proxies:
                return None
            
            # 过滤失败次数过多的代理
            valid_proxies = [
                p for p in self.proxies 
                if self._failed_proxies.get(p.get('http', ''), 0) < 3
            ]
            
            if not valid_proxies:
                # 重置失败计数
                self._failed_proxies.clear()
                valid_proxies = self.proxies
            
            # 基于评分的加权随机选择
            scores = [self._proxy_scores.get(p.get('http', ''), 1.0) for p in valid_proxies]
            total = sum(scores)
            if total == 0:
                return random.choice(valid_proxies)
            
            r = random.uniform(0, total)
            cumsum = 0
            for proxy, score in zip(valid_proxies, scores):
                cumsum += score
                if r <= cumsum:
                    return proxy
            
            return valid_proxies[-1]
    
    def mark_failed(self, proxy: Dict):
        """标记代理失败"""
        proxy_url = proxy.get('http', '')
        with self.lock:
            self._failed_proxies[proxy_url] = self._failed_proxies.get(proxy_url, 0) + 1
            # 降低评分
            if proxy_url in self._proxy_scores:
                self._proxy_scores[proxy_url] *= 0.5
    
    def mark_success(self, proxy: Dict):
        """标记代理成功"""
        proxy_url = proxy.get('http', '')
        with self.lock:
            self._failed_proxies[proxy_url] = 0
            # 提升评分
            if proxy_url in self._proxy_scores:
                self._proxy_scores[proxy_url] = min(2.0, self._proxy_scores[proxy_url] * 1.1)
    
    def validate_proxy(self, proxy: Dict) -> bool:
        """验证代理是否可用"""
        test_url = "https://m.weibo.cn/"
        try:
            response = requests.get(
                test_url, 
                proxies=proxy, 
                timeout=self.validate_timeout,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            return response.status_code == 200
        except:
            return False
    
    def refresh_pool(self):
        """刷新代理池（从免费API获取）"""
        for api_url in self.PROXY_APIS:
            try:
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    proxy_list = response.text.strip().split('\n')
                    for proxy in proxy_list[:20]:  # 限制数量
                        proxy = proxy.strip()
                        if proxy and ':' in proxy:
                            proxy_url = f"http://{proxy}"
                            if self.validate_proxy({'http': proxy_url, 'https': proxy_url}):
                                self.add_proxy(proxy_url)
            except Exception as e:
                logger.debug(f"获取代理失败: {e}")
        
        logger.info(f"代理池刷新完成，当前 {len(self.proxies)} 个代理")
    
    def remove_proxy(self, proxy: Dict):
        """移除代理"""
        with self.lock:
            if proxy in self.proxies:
                self.proxies.remove(proxy)
                proxy_url = proxy.get('http', '')
                self._proxy_scores.pop(proxy_url, None)
                self._failed_proxies.pop(proxy_url, None)
    
    def clear(self):
        """清空代理池"""
        with self.lock:
            self.proxies.clear()
            self._proxy_scores.clear()
            self._failed_proxies.clear()
    
    @property
    def size(self) -> int:
        return len(self.proxies)
    
    def get_stats(self) -> Dict:
        """获取代理池统计信息"""
        return {
            'total': len(self.proxies),
            'failed_count': len(self._failed_proxies),
            'avg_score': sum(self._proxy_scores.values()) / max(len(self._proxy_scores), 1)
        }
