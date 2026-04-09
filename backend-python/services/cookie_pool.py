"""
Cookie池管理模块
================

功能：
- 多账号Cookie轮换
- Cookie有效性检测
- 失败自动切换
- Cookie持久化存储
"""

import os
import json
import threading
import logging
from typing import List, Dict, Optional

import requests
from .ua_pool import UserAgentPool

logger = logging.getLogger('CookiePool')


class CookiePool:
    """
    Cookie池管理器
    
    功能：
    - 多账号Cookie轮换
    - Cookie有效性检测
    - 失败自动切换
    - Cookie持久化存储
    """
    
    def __init__(self, config_path: str = None):
        self.cookies: List[Dict[str, str]] = []
        self.current_index = 0
        self.fail_count: Dict[int, int] = {}
        self.lock = threading.Lock()
        
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), '..', 'crawler', 'cookies.json'
        )
        self._load_cookies()
    
    def _load_cookies(self):
        """加载Cookie配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.cookies = json.load(f)
                logger.info(f"加载了 {len(self.cookies)} 个Cookie")
            except Exception as e:
                logger.warning(f"加载Cookie失败: {e}")
        
        # 如果没有Cookie，添加空Cookie（游客模式）
        if not self.cookies:
            self.cookies = [{'SUB': '', 'SUBP': ''}]
            logger.warning("使用空Cookie，部分功能可能受限")
    
    def get_cookie(self) -> Dict[str, str]:
        """获取下一个可用Cookie（轮换策略）"""
        with self.lock:
            if not self.cookies:
                return {}
            
            # 跳过失败次数过多的Cookie
            attempts = 0
            while attempts < len(self.cookies):
                cookie = self.cookies[self.current_index]
                if self.fail_count.get(self.current_index, 0) < 5:
                    self.current_index = (self.current_index + 1) % len(self.cookies)
                    # 过滤空值
                    return {k: v for k, v in cookie.items() if v and not k.startswith('_')}
                self.current_index = (self.current_index + 1) % len(self.cookies)
                attempts += 1
            
            # 所有Cookie都失败，重置计数
            self.fail_count.clear()
            return {k: v for k, v in self.cookies[0].items() if v and not k.startswith('_')}
    
    def get_cookie_string(self) -> str:
        """获取Cookie字符串格式"""
        cookie = self.get_cookie()
        return '; '.join([f"{k}={v}" for k, v in cookie.items()])
    
    def mark_failed(self, index: int = None):
        """标记Cookie失败"""
        with self.lock:
            idx = index if index is not None else (self.current_index - 1) % len(self.cookies)
            self.fail_count[idx] = self.fail_count.get(idx, 0) + 1
            logger.debug(f"Cookie {idx} 失败次数: {self.fail_count[idx]}")
    
    def mark_success(self, index: int = None):
        """标记Cookie成功"""
        with self.lock:
            idx = index if index is not None else (self.current_index - 1) % len(self.cookies)
            self.fail_count[idx] = 0
    
    def add_cookie(self, cookie: Dict[str, str]):
        """添加新Cookie"""
        with self.lock:
            self.cookies.append(cookie)
            self._save_cookies()
            logger.info(f"添加Cookie，当前共 {len(self.cookies)} 个")
    
    def remove_cookie(self, index: int):
        """移除Cookie"""
        with self.lock:
            if 0 <= index < len(self.cookies):
                self.cookies.pop(index)
                self._save_cookies()
    
    def _save_cookies(self):
        """保存Cookie到文件"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.cookies, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
    
    def validate_cookie(self, cookie: Dict[str, str]) -> bool:
        """验证Cookie是否有效"""
        test_url = "https://m.weibo.cn/api/config"
        try:
            response = requests.get(
                test_url,
                cookies=cookie,
                headers={'User-Agent': UserAgentPool.get_weibo_mobile()},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {}).get('login', False)
        except:
            pass
        return False
    
    def validate_all(self) -> Dict[int, bool]:
        """验证所有Cookie"""
        results = {}
        for i, cookie in enumerate(self.cookies):
            results[i] = self.validate_cookie(cookie)
        return results
    
    def remove_invalid(self):
        """移除无效Cookie"""
        results = self.validate_all()
        with self.lock:
            self.cookies = [c for i, c in enumerate(self.cookies) if results.get(i, False)]
            self._save_cookies()
        logger.info(f"移除无效Cookie后剩余 {len(self.cookies)} 个")
    
    @property
    def size(self) -> int:
        return len(self.cookies)
    
    def get_stats(self) -> Dict:
        """获取Cookie池统计信息"""
        return {
            'total': len(self.cookies),
            'failed_counts': dict(self.fail_count),
            'current_index': self.current_index
        }
