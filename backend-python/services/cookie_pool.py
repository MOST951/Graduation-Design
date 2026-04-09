"""
Enhanced Cookie Pool Management Module
================

Features:
- Multi-account Cookie rotation with round-robin strategy
- Automatic Cookie validity detection and health monitoring
- Smart Cookie rotation based on success/failure rates
- Cookie persistent storage with backup
- Real-time Cookie health scoring
- Automatic cleanup of invalid cookies
- Cookie performance metrics and statistics
"""

import os
import json
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import requests
from .ua_pool import UserAgentPool
from utils.logger import get_logger, log_operation

logger = get_logger(__name__)


class CookieStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INVALID = "invalid"
    EXPIRED = "expired"


@dataclass
class CookieInfo:
    cookie: Dict[str, str]
    status: CookieStatus
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    created_at: datetime = None
    health_score: float = 1.0  # 0.0 to 1.0
    response_time_avg: float = 0.0  # milliseconds
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total
    
    @property
    def is_healthy(self) -> bool:
        """Check if cookie is healthy for use"""
        return (
            self.status == CookieStatus.ACTIVE and
            self.health_score >= 0.3 and
            self.success_rate >= 0.2
        )
    
    def update_health_score(self):
        """Update health score based on performance"""
        # Weight recent performance more heavily
        recent_weight = 0.7
        historical_weight = 0.3
        
        recent_success_rate = self.success_rate
        historical_health = self.health_score
        
        self.health_score = (
            recent_weight * recent_success_rate +
            historical_weight * historical_health
        )
        
        # Boost score for recent successes
        if self.last_success and (datetime.now() - self.last_success).total_seconds() / 60 < 30:
            self.health_score = min(1.0, self.health_score + 0.1)
        
        # Penalize for recent failures
        if self.last_failure and (datetime.now() - self.last_failure).total_seconds() / 60 < 10:
            self.health_score = max(0.0, self.health_score - 0.2)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['status'] = self.status.value
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CookieInfo':
        """Create from dictionary"""
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = CookieStatus(data['status'])
        
        for key in ['last_used', 'last_success', 'last_failure', 'created_at']:
            if key in data and data[key]:
                data[key] = datetime.fromisoformat(data[key])
        
        return cls(**data)


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


class EnhancedCookiePool:
    """
    Enhanced Cookie Pool Manager with intelligent rotation and health monitoring
    """
    
    def __init__(self, config_path: str = None, max_cookies: int = 50):
        self.cookie_infos: List[CookieInfo] = []
        self.current_index = 0
        self.lock = threading.Lock()
        self.max_cookies = max_cookies
        self.validation_thread: Optional[threading.Thread] = None
        self.validation_interval = 300  # 5 minutes
        self.shutdown_event = threading.Event()
        
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), '..', 'crawler', 'cookies.json'
        )
        self.backup_path = self.config_path + '.backup'
        
        self._load_cookies()
        self._start_validation_thread()
    
    def _load_cookies(self):
        """Load cookies from file"""
        for path in [self.backup_path, self.config_path]:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if isinstance(data, list) and data and isinstance(data[0], dict):
                        if 'cookie' in data[0]:
                            self.cookie_infos = [CookieInfo.from_dict(item) for item in data]
                        else:
                            self.cookie_infos = [
                                CookieInfo(cookie=item, status=CookieStatus.ACTIVE)
                                for item in data
                            ]
                    
                    logger.info(f"Loaded {len(self.cookie_infos)} cookies from {path}")
                    break
                    
                except Exception as e:
                    logger.warning(f"Failed to load cookies from {path}: {e}")
                    continue
        
        if not self.cookie_infos:
            self.cookie_infos = [
                CookieInfo(cookie={'SUB': '', 'SUBP': ''}, status=CookieStatus.ACTIVE)
            ]
            logger.warning("Using empty cookies, some features may be limited")
    
    def _save_cookies(self):
        """Save cookies to file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            data = [info.to_dict() for info in self.cookie_infos]
            with open(self.backup_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
    
    def _start_validation_thread(self):
        """Start validation thread"""
        self.validation_thread = threading.Thread(
            target=self._validation_loop,
            name="CookieValidator",
            daemon=True
        )
        self.validation_thread.start()
        logger.info("Started cookie validation thread")
    
    def _validation_loop(self):
        """Validation loop"""
        while not self.shutdown_event.is_set():
            try:
                self._validate_all_cookies()
                self._cleanup_invalid_cookies()
                time.sleep(self.validation_interval)
            except Exception as e:
                logger.error(f"Cookie validation error: {e}")
                time.sleep(60)
    
    def _validate_all_cookies(self):
        """Validate all cookies"""
        with self.lock:
            cookie_infos = self.cookie_infos.copy()
        
        for i, cookie_info in enumerate(cookie_infos):
            if self.shutdown_event.is_set():
                break
                
            try:
                is_valid = self._validate_single_cookie(cookie_info.cookie)
                
                with self.lock:
                    if i < len(self.cookie_infos):
                        current_info = self.cookie_infos[i]
                        if is_valid:
                            current_info.status = CookieStatus.ACTIVE
                            current_info.last_success = datetime.now()
                        else:
                            current_info.status = CookieStatus.INVALID
                            current_info.last_failure = datetime.now()
                        
                        current_info.update_health_score()
                        
            except Exception as e:
                logger.error(f"Error validating cookie {i}: {e}")
    
    def _validate_single_cookie(self, cookie: Dict[str, str]) -> bool:
        """Validate single cookie"""
        test_url = "https://m.weibo.cn/api/config"
        try:
            start_time = time.time()
            response = requests.get(
                test_url,
                cookies=cookie,
                headers={'User-Agent': UserAgentPool.get_weibo_mobile()},
                timeout=10
            )
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                is_valid = data.get('data', {}).get('login', False)
                
                if is_valid:
                    with self.lock:
                        for info in self.cookie_infos:
                            if info.cookie == cookie:
                                if info.response_time_avg == 0:
                                    info.response_time_avg = response_time
                                else:
                                    info.response_time_avg = info.response_time_avg * 0.8 + response_time * 0.2
                                break
                
                return is_valid
        except Exception as e:
            logger.debug(f"Cookie validation error: {e}")
        
        return False
    
    def _cleanup_invalid_cookies(self):
        """Cleanup invalid cookies"""
        with self.lock:
            original_count = len(self.cookie_infos)
            
            valid_cookies = [
                info for info in self.cookie_infos
                if info.status != CookieStatus.INVALID or len(self.cookie_infos) == 1
            ]
            
            cutoff_time = datetime.now() - timedelta(days=7)
            valid_cookies = [
                info for info in valid_cookies
                if info.status == CookieStatus.ACTIVE or info.created_at > cutoff_time
            ]
            
            if len(valid_cookies) > self.max_cookies:
                valid_cookies.sort(key=lambda x: x.health_score, reverse=True)
                valid_cookies = valid_cookies[:self.max_cookies]
            
            self.cookie_infos = valid_cookies
            
            if len(self.cookie_infos) != original_count:
                self._save_cookies()
                logger.info(f"Cleaned up cookies: {original_count} -> {len(self.cookie_infos)}")
    
    def get_best_cookie(self) -> Tuple[Dict[str, str], int]:
        """Get best cookie"""
        with self.lock:
            if not self.cookie_infos:
                return {}, -1
            
            healthy_cookies = [
                (i, info) for i, info in enumerate(self.cookie_infos)
                if info.is_healthy
            ]
            
            if not healthy_cookies:
                healthy_cookies = [
                    (i, info) for i, info in enumerate(self.cookie_infos)
                    if info.status != CookieStatus.INVALID
                ]
            
            if not healthy_cookies:
                return self.cookie_infos[0].cookie, 0
            
            healthy_cookies.sort(key=lambda x: x[1].health_score, reverse=True)
            best_index, best_info = healthy_cookies[0]
            
            best_info.last_used = datetime.now()
            
            filtered_cookie = {k: v for k, v in best_info.cookie.items() if v and not k.startswith('_')}
            
            return filtered_cookie, best_index
    
    def get_cookie(self) -> Dict[str, str]:
        """Get cookie"""
        cookie, index = self.get_best_cookie()
        return cookie
    
    def get_cookie_string(self) -> str:
        """Get cookie string"""
        cookie = self.get_cookie()
        return '; '.join([f"{k}={v}" for k, v in cookie.items()])
    
    def mark_success(self, cookie_index: int = None, response_time: float = None):
        """Mark success"""
        with self.lock:
            if cookie_index is None:
                for i, info in enumerate(self.cookie_infos):
                    if info.last_used:
                        cookie_index = i
                        break
                
                if cookie_index is None:
                    return
            
            if 0 <= cookie_index < len(self.cookie_infos):
                info = self.cookie_infos[cookie_index]
                info.success_count += 1
                info.last_success = datetime.now()
                info.status = CookieStatus.ACTIVE
                
                if response_time:
                    if info.response_time_avg == 0:
                        info.response_time_avg = response_time
                    else:
                        info.response_time_avg = info.response_time_avg * 0.8 + response_time * 0.2
                
                info.update_health_score()
                logger.debug(f"Cookie {cookie_index} marked as successful")
    
    def mark_failed(self, cookie_index: int = None, error_msg: str = None):
        """Mark failed"""
        with self.lock:
            if cookie_index is None:
                for i, info in enumerate(self.cookie_infos):
                    if info.last_used:
                        cookie_index = i
                        break
                
                if cookie_index is None:
                    return
            
            if 0 <= cookie_index < len(self.cookie_infos):
                info = self.cookie_infos[cookie_index]
                info.failure_count += 1
                info.last_failure = datetime.now()
                
                if info.failure_count >= 5:
                    info.status = CookieStatus.SUSPENDED
                
                info.update_health_score()
                logger.debug(f"Cookie {cookie_index} marked as failed (count: {info.failure_count})")
    
    def add_cookie(self, cookie: Dict[str, str]) -> bool:
        """Add cookie"""
        with self.lock:
            if len(self.cookie_infos) >= self.max_cookies:
                logger.warning(f"Cookie pool full ({self.max_cookies}), cannot add more")
                return False
            
            for info in self.cookie_infos:
                if info.cookie == cookie:
                    logger.warning("Cookie already exists in pool")
                    return False
            
            is_valid = self._validate_single_cookie(cookie)
            status = CookieStatus.ACTIVE if is_valid else CookieStatus.INVALID
            
            cookie_info = CookieInfo(
                cookie=cookie,
                status=status,
                last_success=datetime.now() if is_valid else None,
                last_failure=None if is_valid else datetime.now()
            )
            
            self.cookie_infos.append(cookie_info)
            self._save_cookies()
            
            logger.info(f"Added cookie (valid: {is_valid}), total: {len(self.cookie_infos)}")
            return True
    
    def remove_cookie(self, index: int) -> bool:
        """Remove cookie"""
        with self.lock:
            if 0 <= index < len(self.cookie_infos):
                self.cookie_infos.pop(index)
                self._save_cookies()
                logger.info(f"Removed cookie at index {index}")
                return True
            return False
    
    def update_cookies(self, new_cookies: List[Dict[str, str]]) -> Dict[str, int]:
        """Update cookies"""
        results = {'added': 0, 'updated': 0, 'removed': 0}
        
        with self.lock:
            existing_cookies = {i: info.cookie for i, info in enumerate(self.cookie_infos)}
            matched_indices = set()
            
            for new_cookie in new_cookies:
                found = False
                for i, info in enumerate(self.cookie_infos):
                    if info.cookie == new_cookie:
                        info.status = CookieStatus.ACTIVE
                        info.last_success = datetime.now()
                        matched_indices.add(i)
                        results['updated'] += 1
                        found = True
                        break
                
                if not found:
                    if self.add_cookie(new_cookie):
                        results['added'] += 1
            
            indices_to_remove = []
            for i in existing_cookies:
                if i not in matched_indices and len(self.cookie_infos) > 1:
                    indices_to_remove.append(i)
            
            for i in sorted(indices_to_remove, reverse=True):
                if i < len(self.cookie_infos):
                    self.cookie_infos.pop(i)
                    results['removed'] += 1
            
            if results['added'] + results['updated'] + results['removed'] > 0:
                self._save_cookies()
        
        return results
    
    def get_stats(self) -> Dict:
        """Get stats"""
        with self.lock:
            active_count = sum(1 for info in self.cookie_infos if info.status == CookieStatus.ACTIVE)
            suspended_count = sum(1 for info in self.cookie_infos if info.status == CookieStatus.SUSPENDED)
            invalid_count = sum(1 for info in self.cookie_infos if info.status == CookieStatus.INVALID)
            
            avg_health = sum(info.health_score for info in self.cookie_infos) / len(self.cookie_infos) if self.cookie_infos else 0
            avg_response_time = sum(info.response_time_avg for info in self.cookie_infos if info.response_time_avg > 0) / len([info for info in self.cookie_infos if info.response_time_avg > 0]) if self.cookie_infos else 0
            
            return {
                'total': len(self.cookie_infos),
                'active': active_count,
                'suspended': suspended_count,
                'invalid': invalid_count,
                'avg_health_score': round(avg_health, 3),
                'avg_response_time_ms': round(avg_response_time, 2),
                'max_cookies': self.max_cookies,
                'validation_interval': self.validation_interval,
                'cookies': [
                    {
                        'index': i,
                        'status': info.status.value,
                        'health_score': round(info.health_score, 3),
                        'success_rate': round(info.success_rate, 3),
                        'success_count': info.success_count,
                        'failure_count': info.failure_count,
                        'last_used': info.last_used.isoformat() if info.last_used else None,
                        'response_time_avg': round(info.response_time_avg, 2)
                    }
                    for i, info in enumerate(self.cookie_infos)
                ]
            }
    
    def shutdown(self):
        """Shutdown"""
        logger.info("Shutting down cookie pool...")
        self.shutdown_event.set()
        
        if self.validation_thread:
            self.validation_thread.join(timeout=5.0)
        
        self._save_cookies()
        logger.info("Cookie pool shutdown complete")


# Global cookie pool instance
cookie_pool = EnhancedCookiePool()
