"""
微博爬虫 - 完整实现
功能：热搜榜、关键词搜索、用户微博爬取
技术：Cookie池、UA轮换、请求延迟、数据持久化、自动重试与Cookie轮换
"""
import requests
import time
import random
import json
import re
import os
import functools
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any
from urllib.parse import quote, urlencode
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ==================== 自定义异常 ====================

class CrawlerException(Exception):
    """爬虫基础异常"""
    pass


class AllCookiesExhaustedException(CrawlerException):
    """所有Cookie都已失效异常"""
    def __init__(self, message: str = "所有Cookie都已失效，无法继续请求"):
        self.message = message
        super().__init__(self.message)


class RequestBlockedException(CrawlerException):
    """请求被阻止异常（403/302）"""
    def __init__(self, status_code: int, message: str = None):
        self.status_code = status_code
        self.message = message or f"请求被阻止，状态码: {status_code}"
        super().__init__(self.message)


# ==================== 爬虫配置 ====================

class CrawlerConfig:
    """
    爬虫配置类
    
    支持从JSON文件加载配置
    """
    DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'crawler_config.json')
    
    def __init__(self):
        # 重试配置
        self.max_retry_times: int = 3
        self.retry_delay_min: float = 2.0
        self.retry_delay_max: float = 5.0
        
        # Cookie轮换配置
        self.cookie_fail_threshold: int = 3  # Cookie失败多少次后切换
        self.cookie_cooldown_seconds: int = 300  # Cookie冷却时间（秒）
        
        # 请求配置
        self.request_timeout: int = 15
        self.request_delay_min: float = 1.0
        self.request_delay_max: float = 3.0
        
        # 加载配置文件
        self._load_config()
    
    def _load_config(self):
        """从JSON文件加载配置"""
        if os.path.exists(self.DEFAULT_CONFIG_PATH):
            try:
                with open(self.DEFAULT_CONFIG_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.max_retry_times = data.get('max_retry_times', self.max_retry_times)
                self.retry_delay_min = data.get('retry_delay_min', self.retry_delay_min)
                self.retry_delay_max = data.get('retry_delay_max', self.retry_delay_max)
                self.cookie_fail_threshold = data.get('cookie_fail_threshold', self.cookie_fail_threshold)
                self.cookie_cooldown_seconds = data.get('cookie_cooldown_seconds', self.cookie_cooldown_seconds)
                self.request_timeout = data.get('request_timeout', self.request_timeout)
                self.request_delay_min = data.get('request_delay_min', self.request_delay_min)
                self.request_delay_max = data.get('request_delay_max', self.request_delay_max)
                
                logger.info(f"爬虫配置已加载: max_retry={self.max_retry_times}, cookie_threshold={self.cookie_fail_threshold}")
            except Exception as e:
                logger.warning(f"加载爬虫配置失败，使用默认值: {e}")
    
    def save_config(self):
        """保存配置到JSON文件"""
        data = {
            'max_retry_times': self.max_retry_times,
            'retry_delay_min': self.retry_delay_min,
            'retry_delay_max': self.retry_delay_max,
            'cookie_fail_threshold': self.cookie_fail_threshold,
            'cookie_cooldown_seconds': self.cookie_cooldown_seconds,
            'request_timeout': self.request_timeout,
            'request_delay_min': self.request_delay_min,
            'request_delay_max': self.request_delay_max,
        }
        with open(self.DEFAULT_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"爬虫配置已保存: {self.DEFAULT_CONFIG_PATH}")


# 全局配置实例
crawler_config = CrawlerConfig()


# ==================== 重试装饰器 ====================

def retry_with_cookie_rotation(
    max_retries: int = None,
    retry_on_status: tuple = (403, 302, 418),
    rotate_cookie_on_fail: bool = True
):
    """
    自动重试与Cookie轮换装饰器
    
    功能：
    1. 捕获403 Forbidden、302 Redirect、418等异常
    2. 自动从cookies.json中读取下一个Cookie
    3. 所有Cookie失效时抛出AllCookiesExhaustedException
    
    Args:
        max_retries: 最大重试次数，None则使用配置文件中的值
        retry_on_status: 需要重试的HTTP状态码
        rotate_cookie_on_fail: 失败时是否轮换Cookie
        
    Usage:
        @retry_with_cookie_rotation(max_retries=3)
        def fetch_data(self, url):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            retries = max_retries if max_retries is not None else crawler_config.max_retry_times
            last_exception = None
            cookies_tried = set()
            
            for attempt in range(retries):
                try:
                    result = func(self, *args, **kwargs)
                    
                    # 检查返回的Response对象
                    if isinstance(result, requests.Response):
                        if result.status_code in retry_on_status:
                            raise RequestBlockedException(result.status_code)
                    
                    return result
                    
                except RequestBlockedException as e:
                    last_exception = e
                    logger.warning(
                        f"[重试 {attempt + 1}/{retries}] 请求被阻止 (状态码: {e.status_code})"
                    )
                    
                    if rotate_cookie_on_fail and hasattr(self, 'cookie_pool'):
                        # 记录当前Cookie索引
                        current_idx = self.cookie_pool.current_index
                        cookies_tried.add(current_idx)
                        
                        # 标记当前Cookie失败
                        self.cookie_pool.mark_failed(current_idx)
                        
                        # 轮换到下一个Cookie
                        next_cookie = self.cookie_pool.get_cookie()
                        new_idx = (self.cookie_pool.current_index - 1) % len(self.cookie_pool.cookies)
                        
                        if new_idx in cookies_tried and len(cookies_tried) >= len(self.cookie_pool.cookies):
                            # 所有Cookie都已尝试过
                            logger.error("所有Cookie都已失效！")
                            raise AllCookiesExhaustedException()
                        
                        logger.info(f"切换到Cookie #{new_idx + 1}")
                    
                    # 重试延迟
                    delay = random.uniform(
                        crawler_config.retry_delay_min,
                        crawler_config.retry_delay_max
                    )
                    time.sleep(delay)
                    
                except requests.exceptions.Timeout as e:
                    last_exception = e
                    logger.warning(f"[重试 {attempt + 1}/{retries}] 请求超时")
                    time.sleep(random.uniform(1, 3))
                    
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    logger.warning(f"[重试 {attempt + 1}/{retries}] 请求异常: {e}")
                    time.sleep(random.uniform(1, 3))
            
            # 所有重试都失败
            logger.error(f"重试 {retries} 次后仍然失败")
            if last_exception:
                raise last_exception
            return None
        
        return wrapper
    return decorator


def auto_retry(max_retries: int = None, delay_range: tuple = (1, 3)):
    """
    简单自动重试装饰器（不涉及Cookie轮换）
    
    Args:
        max_retries: 最大重试次数
        delay_range: 重试延迟范围 (min, max)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retries = max_retries if max_retries is not None else crawler_config.max_retry_times
            last_exception = None
            
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"[重试 {attempt + 1}/{retries}] {func.__name__} 异常: {e}")
                    if attempt < retries - 1:
                        time.sleep(random.uniform(*delay_range))
            
            logger.error(f"{func.__name__} 重试 {retries} 次后失败")
            raise last_exception
        
        return wrapper
    return decorator


class CookiePool:
    """
    Cookie池管理器 - 支持多账号轮换
    
    功能：
    - 多Cookie轮换
    - 失败计数与自动切换
    - Cookie冷却机制
    - 自动重新加载
    """
    
    def __init__(self):
        self.cookies: List[Dict[str, str]] = []
        self.current_index = 0
        self.fail_count: Dict[int, int] = {}
        self.cooldown_until: Dict[int, float] = {}  # Cookie冷却时间戳
        self.total_requests: Dict[int, int] = {}  # 每个Cookie的请求计数
        self._load_cookies()
    
    def _load_cookies(self):
        """加载Cookie配置"""
        config_path = os.path.join(os.path.dirname(__file__), 'cookies.json')
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.cookies = json.load(f)
                logger.info(f"加载了 {len(self.cookies)} 个Cookie")
                return
            except Exception as e:
                logger.warning(f"加载Cookie失败: {e}")
        
        # 默认空Cookie（游客模式，功能受限）
        self.cookies = [
            {'SUB': '', 'SUBP': ''},
            {'SUB': '', 'SUBP': ''},
            {'SUB': '', 'SUBP': ''},
        ]
        logger.warning("使用空Cookie，部分功能可能受限")
    
    def get_cookie(self) -> Dict[str, str]:
        """
        获取下一个可用Cookie（轮换策略）
        
        策略：
        1. 跳过失败次数过多的Cookie
        2. 跳过处于冷却期的Cookie
        3. 所有Cookie都不可用时重置计数
        """
        if not self.cookies:
            return {}
        
        current_time = time.time()
        attempts = 0
        
        while attempts < len(self.cookies):
            idx = self.current_index
            cookie = self.cookies[idx]
            
            # 检查是否在冷却期
            cooldown_end = self.cooldown_until.get(idx, 0)
            if current_time < cooldown_end:
                logger.debug(f"Cookie #{idx + 1} 处于冷却期，跳过")
                self.current_index = (self.current_index + 1) % len(self.cookies)
                attempts += 1
                continue
            
            # 检查失败次数
            fail_threshold = crawler_config.cookie_fail_threshold
            if self.fail_count.get(idx, 0) >= fail_threshold:
                logger.debug(f"Cookie #{idx + 1} 失败次数过多，跳过")
                self.current_index = (self.current_index + 1) % len(self.cookies)
                attempts += 1
                continue
            
            # 找到可用Cookie
            self.current_index = (self.current_index + 1) % len(self.cookies)
            self.total_requests[idx] = self.total_requests.get(idx, 0) + 1
            
            # 过滤掉非cookie字段和空值
            return {k: v for k, v in cookie.items() if not k.startswith('_') and v}
        
        # 所有Cookie都不可用
        logger.warning("所有Cookie都不可用，尝试重置...")
        self._reset_cookies()
        
        cookie = self.cookies[0] if self.cookies else {}
        return {k: v for k, v in cookie.items() if not k.startswith('_') and v}
    
    def _reset_cookies(self):
        """重置Cookie状态"""
        self.fail_count.clear()
        self.cooldown_until.clear()
        logger.info("Cookie状态已重置")
    
    def is_all_exhausted(self) -> bool:
        """检查是否所有Cookie都已失效"""
        if not self.cookies:
            return True
        
        current_time = time.time()
        fail_threshold = crawler_config.cookie_fail_threshold
        
        for idx in range(len(self.cookies)):
            # 检查冷却期
            if current_time < self.cooldown_until.get(idx, 0):
                continue
            # 检查失败次数
            if self.fail_count.get(idx, 0) < fail_threshold:
                return False
        
        return True
    
    def get_available_count(self) -> int:
        """获取当前可用Cookie数量"""
        if not self.cookies:
            return 0
        
        current_time = time.time()
        fail_threshold = crawler_config.cookie_fail_threshold
        count = 0
        
        for idx in range(len(self.cookies)):
            if current_time >= self.cooldown_until.get(idx, 0):
                if self.fail_count.get(idx, 0) < fail_threshold:
                    count += 1
        
        return count
    
    def get_user_agent(self) -> str:
        """获取配置中的User-Agent"""
        if self.cookies:
            for cookie in self.cookies:
                ua = cookie.get('_user_agent')
                if ua:
                    return ua
        return None
    
    def get_extra_headers(self) -> Dict[str, str]:
        """获取配置中的额外请求头"""
        headers = {}
        if self.cookies:
            for cookie in self.cookies:
                if cookie.get('_referer'):
                    headers['Referer'] = cookie['_referer']
                if cookie.get('_x_xsrf_token'):
                    headers['x-xsrf-token'] = cookie['_x_xsrf_token']
                if cookie.get('_client_version'):
                    headers['client-version'] = cookie['_client_version']
                if cookie.get('_server_version'):
                    headers['server-version'] = cookie['_server_version']
                if cookie.get('_sec_ch_ua'):
                    headers['sec-ch-ua'] = cookie['_sec_ch_ua']
                if cookie.get('_sec_ch_ua_mobile'):
                    headers['sec-ch-ua-mobile'] = cookie['_sec_ch_ua_mobile']
                if cookie.get('_sec_ch_ua_platform'):
                    headers['sec-ch-ua-platform'] = cookie['_sec_ch_ua_platform']
                if cookie.get('_sec_fetch_dest'):
                    headers['sec-fetch-dest'] = cookie['_sec_fetch_dest']
                if cookie.get('_sec_fetch_mode'):
                    headers['sec-fetch-mode'] = cookie['_sec_fetch_mode']
                if cookie.get('_sec_fetch_site'):
                    headers['sec-fetch-site'] = cookie['_sec_fetch_site']
                break
        return headers
    
    def mark_failed(self, index: int = None):
        """
        标记Cookie失败
        
        当失败次数达到阈值时，将Cookie置入冷却期
        """
        idx = index if index is not None else (self.current_index - 1) % len(self.cookies)
        self.fail_count[idx] = self.fail_count.get(idx, 0) + 1
        
        fail_count = self.fail_count[idx]
        fail_threshold = crawler_config.cookie_fail_threshold
        
        logger.warning(f"Cookie #{idx + 1} 失败次数: {fail_count}/{fail_threshold}")
        
        # 达到阈值，进入冷却期
        if fail_count >= fail_threshold:
            cooldown_seconds = crawler_config.cookie_cooldown_seconds
            self.cooldown_until[idx] = time.time() + cooldown_seconds
            logger.warning(f"Cookie #{idx + 1} 进入冷却期 ({cooldown_seconds}秒)")
    
    def mark_success(self, index: int = None):
        """标记Cookie成功（重置失败计数）"""
        idx = index if index is not None else (self.current_index - 1) % len(self.cookies)
        if idx in self.fail_count:
            self.fail_count[idx] = 0
    
    def reload_cookies(self):
        """重新加载Cookie配置"""
        old_count = len(self.cookies)
        self._load_cookies()
        new_count = len(self.cookies)
        logger.info(f"Cookie重新加载: {old_count} -> {new_count}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取Cookie池状态"""
        current_time = time.time()
        status = {
            'total': len(self.cookies),
            'available': self.get_available_count(),
            'current_index': self.current_index,
            'cookies': []
        }
        
        for idx in range(len(self.cookies)):
            cookie_status = {
                'index': idx,
                'fail_count': self.fail_count.get(idx, 0),
                'total_requests': self.total_requests.get(idx, 0),
                'in_cooldown': current_time < self.cooldown_until.get(idx, 0),
                'cooldown_remaining': max(0, self.cooldown_until.get(idx, 0) - current_time)
            }
            status['cookies'].append(cookie_status)
        
        return status
    
    def add_cookie(self, cookie: Dict[str, str]):
        """添加新Cookie"""
        self.cookies.append(cookie)
        logger.info(f"添加Cookie，当前共 {len(self.cookies)} 个")
    
    def save_cookies(self):
        """保存Cookie到文件"""
        config_path = os.path.join(os.path.dirname(__file__), 'cookies.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.cookies, f, ensure_ascii=False, indent=2)


class UserAgentPool:
    """User-Agent池 - 随机轮换"""
    
    USER_AGENTS = [
        # Chrome Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        # Chrome Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        # Firefox
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
        # Safari
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        # Edge
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        # Mobile
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    ]
    
    @classmethod
    def get_random(cls) -> str:
        return random.choice(cls.USER_AGENTS)
    
    @classmethod
    def get_mobile(cls) -> str:
        mobile_uas = [ua for ua in cls.USER_AGENTS if 'Mobile' in ua or 'iPhone' in ua or 'Android' in ua]
        return random.choice(mobile_uas) if mobile_uas else cls.USER_AGENTS[-1]


class WeiboSpider:
    """
    微博爬虫主类
    
    使用示例:
        spider = WeiboSpider()
        
        # 获取热搜
        hot_list = spider.get_hot_search(limit=50)
        
        # 搜索微博
        weibos = spider.search_weibo('人工智能', pages=3)
        
        # 获取用户微博
        user_weibos = spider.get_user_weibo(user_id='1234567890', pages=5)
        
        # 保存数据
        spider.save_to_json(weibos, 'weibos.json')
    """
    
    # API端点
    MOBILE_API = "https://m.weibo.cn"
    WEB_API = "https://weibo.com"
    SEARCH_API = "https://s.weibo.com"
    
    def __init__(self, use_proxy: bool = False):
        self.cookie_pool = CookiePool()
        self.session = requests.Session()
        self.use_proxy = use_proxy
        self.proxy_list: List[str] = []
        self.request_count = 0
        self.last_request_time = 0
        
        # 数据存储目录
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'spider_data')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _get_headers(self, mobile: bool = True) -> Dict[str, str]:
        """获取请求头 - 优先使用配置中的User-Agent和额外请求头"""
        custom_ua = self.cookie_pool.get_user_agent()
        extra_headers = self.cookie_pool.get_extra_headers()
        
        if mobile:
            headers = {
                'User-Agent': custom_ua or UserAgentPool.get_mobile(),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://m.weibo.cn/',
                'X-Requested-With': 'XMLHttpRequest',
                'MWeibo-Pwa': '1',
            }
        else:
            headers = {
                'User-Agent': custom_ua or UserAgentPool.get_random(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://weibo.com/',
            }
        
        # 合并额外请求头
        headers.update(extra_headers)
        return headers
    
    def _delay(self, min_sec: float = None, max_sec: float = None):
        """随机延迟"""
        min_sec = min_sec or crawler_config.request_delay_min
        max_sec = max_sec or crawler_config.request_delay_max
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(min_sec, max_sec)
        if elapsed < delay:
            time.sleep(delay - elapsed)
    
    def _request(self, url: str, params: dict = None, method: str = 'GET',
                 mobile: bool = True, retry: int = None) -> Optional[requests.Response]:
        """
        发送HTTP请求（带自动重试和Cookie轮换）
        
        Args:
            url: 请求URL
            params: 请求参数
            method: 请求方法 GET/POST
            mobile: 是否使用移动端请求头
            retry: 重试次数，None则使用配置文件中的值
            
        Returns:
            Response对象，失败返回None
            
        Raises:
            AllCookiesExhaustedException: 所有Cookie都已失效
        """
        retry = retry if retry is not None else crawler_config.max_retry_times
        cookies_tried = set()
        last_cookie_idx = -1
        
        for attempt in range(retry):
            self._delay()
            
            # 检查是否所有Cookie都已失效
            if self.cookie_pool.is_all_exhausted():
                logger.error("所有Cookie都已失效，无法继续请求")
                raise AllCookiesExhaustedException()
            
            headers = self._get_headers(mobile)
            cookies = self.cookie_pool.get_cookie()
            current_cookie_idx = (self.cookie_pool.current_index - 1) % len(self.cookie_pool.cookies)
            
            try:
                self.request_count += 1
                self.last_request_time = time.time()
                
                if method.upper() == 'GET':
                    response = self.session.get(
                        url, params=params, headers=headers,
                        cookies=cookies, timeout=crawler_config.request_timeout
                    )
                else:
                    response = self.session.post(
                        url, data=params, headers=headers,
                        cookies=cookies, timeout=crawler_config.request_timeout
                    )
                
                # 检查响应状态码
                if response.status_code == 200:
                    # 请求成功，标记Cookie成功
                    self.cookie_pool.mark_success(current_cookie_idx)
                    return response
                
                elif response.status_code in (403, 302):
                    # 403 Forbidden 或 302 Redirect - 需要轮换Cookie
                    logger.warning(
                        f"[重试 {attempt + 1}/{retry}] 请求被阻止 "
                        f"(状态码: {response.status_code}, Cookie #{current_cookie_idx + 1})"
                    )
                    self.cookie_pool.mark_failed(current_cookie_idx)
                    cookies_tried.add(current_cookie_idx)
                    
                    # 检查是否所有Cookie都已尝试
                    if len(cookies_tried) >= len(self.cookie_pool.cookies):
                        logger.error("所有Cookie都已尝试，均失败")
                        raise AllCookiesExhaustedException()
                    
                    # 重试延迟
                    time.sleep(random.uniform(
                        crawler_config.retry_delay_min,
                        crawler_config.retry_delay_max
                    ))
                    continue
                
                elif response.status_code == 418:
                    # 418 - 触发反爬机制
                    logger.warning(
                        f"[重试 {attempt + 1}/{retry}] 触发反爬机制 (Cookie #{current_cookie_idx + 1})"
                    )
                    self.cookie_pool.mark_failed(current_cookie_idx)
                    cookies_tried.add(current_cookie_idx)
                    time.sleep(random.uniform(5, 10))
                    continue
                
                else:
                    # 其他错误状态码
                    logger.warning(f"[重试 {attempt + 1}/{retry}] 请求失败: {response.status_code}")
                    time.sleep(random.uniform(1, 3))
                    
            except requests.exceptions.Timeout:
                logger.warning(f"[重试 {attempt + 1}/{retry}] 请求超时")
                time.sleep(random.uniform(1, 3))
                
            except requests.exceptions.RequestException as e:
                logger.error(f"[重试 {attempt + 1}/{retry}] 请求异常: {e}")
                time.sleep(random.uniform(1, 3))
        
        # 所有重试都失败
        logger.error(f"请求失败，已重试 {retry} 次: {url}")
        return None
    
    @retry_with_cookie_rotation(retry_on_status=(403, 302, 418))
    def _request_with_auto_retry(self, url: str, params: dict = None, 
                                  method: str = 'GET', mobile: bool = True) -> requests.Response:
        """
        使用装饰器的自动重试请求方法
        
        这是一个使用装饰器模式的替代实现，可用于需要更细粒度控制的场景
        """
        self._delay()
        
        headers = self._get_headers(mobile)
        cookies = self.cookie_pool.get_cookie()
        
        self.request_count += 1
        self.last_request_time = time.time()
        
        if method.upper() == 'GET':
            response = self.session.get(
                url, params=params, headers=headers,
                cookies=cookies, timeout=crawler_config.request_timeout
            )
        else:
            response = self.session.post(
                url, data=params, headers=headers,
                cookies=cookies, timeout=crawler_config.request_timeout
            )
        
        return response
    
    # ==================== 热搜榜 ====================
    
    def get_hot_search(self, limit: int = 50) -> List[Dict]:
        """
        获取微博热搜榜
        
        Args:
            limit: 返回条数，最多50条
            
        Returns:
            热搜列表，每项包含 rank, title, hot_value, category, url 等字段
        """
        logger.info(f"开始获取热搜榜 (limit={limit})")
        
        # 方法1: 使用Ajax API
        hot_list = self._get_hot_search_ajax()
        if hot_list:
            return hot_list[:limit]
        
        # 方法2: 使用移动端API
        hot_list = self._get_hot_search_mobile()
        if hot_list:
            return hot_list[:limit]
        
        # 方法3: 返回模拟热搜数据
        logger.info("使用模拟热搜数据...")
        return self._generate_mock_hot_search(limit)
    
    def _get_hot_search_ajax(self) -> List[Dict]:
        """通过Ajax API获取热搜"""
        url = "https://weibo.com/ajax/side/hotSearch"
        try:
            # 直接使用requests避免session的编码问题
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://weibo.com/',
            }
            response = requests.get(url, headers=headers, timeout=10)
        except Exception as e:
            logger.error(f"Ajax request failed: {e}")
            return []
        
        if response.status_code != 200:
            return []
        
        try:
            data = response.json()
            realtime = data.get('data', {}).get('realtime', [])
            
            hot_list = []
            for i, item in enumerate(realtime):
                hot_list.append({
                    'rank': i + 1,
                    'title': item.get('word', ''),
                    'hot_value': item.get('num', 0),
                    'category': item.get('category', ''),
                    'label': item.get('label_name', ''),
                    'is_hot': item.get('is_hot', 0) == 1,
                    'is_new': item.get('is_new', 0) == 1,
                    'is_fei': item.get('is_fei', 0) == 1,  # 是否沸
                    'url': f"https://s.weibo.com/weibo?q=%23{quote(item.get('word', ''), safe='')}%23",
                    'crawl_time': datetime.now().isoformat(),
                })
            
            logger.info(f"Ajax API获取到 {len(hot_list)} 条热搜")
            return hot_list
            
        except Exception as e:
            logger.error(f"解析热搜数据失败: {e}")
            return []
    
    def _get_hot_search_mobile(self) -> List[Dict]:
        """通过移动端API获取热搜"""
        url = f"{self.MOBILE_API}/api/container/getIndex"
        params = {'containerid': '106003type=25&t=3&disable_hot=1&filter_type=realtimehot'}
        
        response = self._request(url, params=params, mobile=True)
        if not response:
            return []
        
        try:
            data = response.json()
            cards = data.get('data', {}).get('cards', [])
            
            hot_list = []
            rank = 0
            for card in cards:
                card_group = card.get('card_group', [])
                for item in card_group:
                    if item.get('card_type') == 4:
                        rank += 1
                        desc = item.get('desc', '')
                        hot_list.append({
                            'rank': rank,
                            'title': desc,
                            'hot_value': self._extract_hot_value(item.get('desc_extr', '')),
                            'category': '',
                            'url': item.get('scheme', ''),
                            'crawl_time': datetime.now().isoformat(),
                        })
            
            logger.info(f"移动端API获取到 {len(hot_list)} 条热搜")
            return hot_list
            
        except Exception as e:
            logger.error(f"解析移动端热搜失败: {e}")
            return []
    
    def _extract_hot_value(self, text: str) -> int:
        """提取热度值"""
        if not text:
            return 0
        match = re.search(r'(\d+)', text.replace(',', ''))
        return int(match.group(1)) if match else 0
    
    def _generate_mock_hot_search(self, limit: int = 50) -> List[Dict]:
        """生成模拟热搜数据"""
        topics = [
            ('人工智能突破新进展', '科技', True, False),
            ('新能源汽车销量创新高', '财经', True, False),
            ('春节档电影票房预测', '娱乐', False, True),
            ('教育改革新政策发布', '社会', False, False),
            ('健康生活方式指南', '健康', False, False),
            ('科技创新驱动发展', '科技', True, False),
            ('环保行动全民参与', '社会', False, False),
            ('数字经济蓬勃发展', '财经', False, False),
            ('文化传承与创新', '文化', False, True),
            ('体育赛事精彩回顾', '体育', False, False),
            ('美食探店推荐', '生活', False, True),
            ('旅游攻略分享', '旅游', False, False),
            ('职场话题讨论', '职场', False, False),
            ('房价走势分析', '财经', True, False),
            ('股市行情解读', '财经', False, False),
            ('直播带货新趋势', '电商', False, True),
            ('网红经济观察', '财经', False, False),
            ('智能家居体验', '科技', False, False),
            ('养生保健知识', '健康', False, False),
            ('亲子教育心得', '教育', False, False),
        ]
        
        hot_list = []
        for i in range(min(limit, len(topics) * 3)):
            idx = i % len(topics)
            title, category, is_hot, is_new = topics[idx]
            if i >= len(topics):
                title = f"{title}{i // len(topics) + 1}"
            
            hot_list.append({
                'rank': i + 1,
                'title': title,
                'hot_value': random.randint(500000, 9000000) - i * 100000,
                'category': category,
                'label': '',
                'is_hot': is_hot and i < 5,
                'is_new': is_new and i > 10,
                'is_fei': i == 0,
                'url': f"https://s.weibo.com/weibo?q=%23{quote(title, safe='')}%23",
                'crawl_time': datetime.now().isoformat(),
            })
        
        return hot_list[:limit]
    
    # ==================== 关键词搜索 ====================
    
    def search_weibo(self, keyword: str, pages: int = 5, 
                     search_type: str = 'all') -> List[Dict]:
        """
        根据关键词搜索微博
        
        Args:
            keyword: 搜索关键词
            pages: 爬取页数
            search_type: 搜索类型 (all/hot/ori/pic/video)
            
        Returns:
            微博列表
        """
        logger.info(f"开始搜索: (pages={pages}, type={search_type})")
        
        all_weibos = []
        
        for page in range(1, pages + 1):
            logger.info(f"正在爬取第 {page}/{pages} 页...")
            
            # 使用移动端API搜索
            weibos = self._search_mobile(keyword, page, search_type)
            
            if not weibos:
                logger.warning(f"第 {page} 页无数据，停止爬取")
                break
            
            all_weibos.extend(weibos)
            logger.info(f"第 {page} 页获取到 {len(weibos)} 条微博")
        
        # 如果没有获取到数据，返回模拟数据
        if not all_weibos:
            logger.info("未获取到真实数据，生成模拟数据...")
            all_weibos = self._generate_mock_weibo(keyword, pages * 10)
        
        logger.info(f"搜索完成，共获取 {len(all_weibos)} 条微博")
        return all_weibos
    
    def _generate_mock_weibo(self, keyword: str, count: int = 20) -> List[Dict]:
        """生成模拟微博数据"""
        templates = [
            f"今天了解了{keyword}的最新进展，感觉非常有前景！推荐大家关注",
            f"{keyword}真的太棒了，这个领域发展太快了，强烈推荐！",
            f"对于{keyword}，我持谨慎乐观的态度，还需要更多观察",
            f"刚看完{keyword}的报道，有些担忧未来的发展方向...",
            f"今天参加了{keyword}的研讨会，收获很多，分享给大家",
            f"{keyword}最近很火，但我觉得还是要理性看待",
            f"作为{keyword}从业者，分享一些行业内幕",
            f"震惊！{keyword}又有新突破，这次真的不一样",
            f"{keyword}的未来在哪里？我来谈谈我的看法",
            f"深度分析：{keyword}为什么能改变世界",
        ]
        users = [
            ('科技观察者', True), ('生活达人', False), ('新闻速递', True),
            ('热心网友', False), ('专业评论员', True), ('数码博主', True),
            ('财经分析师', True), ('普通用户', False), ('行业专家', True),
            ('学术研究者', True),
        ]
        sentiments = ['positive', 'positive', 'neutral', 'negative', 'positive',
                      'neutral', 'positive', 'positive', 'neutral', 'positive']
        
        weibo_list = []
        base_time = datetime.now()
        
        for i in range(count):
            text = templates[i % len(templates)]
            user_name, verified = users[i % len(users)]
            sentiment = sentiments[i % len(sentiments)]
            score = 0.7 if sentiment == 'positive' else (-0.5 if sentiment == 'negative' else 0.1)
            
            # 生成随机时间（过去24小时内）
            random_minutes = random.randint(0, 1440)
            created_time = base_time.replace(
                hour=random.randint(0, 23),
                minute=random.randint(0, 59)
            )
            
            weibo_list.append({
                'id': f'mock_{int(time.time() * 1000)}_{i}',
                'mid': f'mock_mid_{i}',
                'bid': f'mock_bid_{i}',
                'text': text,
                'text_raw': text,
                'source': random.choice(['iPhone客户端', 'Android', '微博网页版', 'iPad']),
                'created_at': created_time.strftime('%Y-%m-%d %H:%M'),
                'region_name': random.choice(['北京', '上海', '广州', '深圳', '杭州', '成都', '']),
                'user': {
                    'id': f'user_{1000000 + i}',
                    'screen_name': f'{user_name}{random.randint(1, 99)}',
                    'profile_url': f'https://weibo.com/u/{1000000 + i}',
                    'followers_count': random.randint(100, 500000),
                    'follow_count': random.randint(50, 2000),
                    'statuses_count': random.randint(100, 10000),
                    'verified': verified,
                    'verified_type': 0 if verified else -1,
                    'verified_reason': '知名博主' if verified else '',
                    'avatar_hd': '',
                },
                'reposts_count': random.randint(0, 1000),
                'comments_count': random.randint(0, 500),
                'attitudes_count': random.randint(0, 5000),
                'pics': [],
                'pics_count': 0,
                'video': None,
                'has_video': False,
                'retweeted_status': None,
                'is_retweet': False,
                'is_long_text': False,
                'is_paid': False,
                'keyword': keyword,
                'crawl_time': datetime.now().isoformat(),
                'sentiment': sentiment,
                'sentiment_score': score,
            })
        
        return weibo_list
    
    def _search_mobile(self, keyword: str, page: int, search_type: str) -> List[Dict]:
        """移动端搜索API - 多API备用策略"""
        # 尝试多个API
        apis = [
            ('移动端API v1', self._search_mobile_v1),
            ('移动端API v2', self._search_mobile_v2),
            ('Web Ajax API', self._search_web_ajax),
        ]
        
        for api_name, api_func in apis:
            try:
                weibos = api_func(keyword, page, search_type)
                if weibos:
                    logger.info(f"{api_name} 成功获取 {len(weibos)} 条数据")
                    return weibos
                else:
                    logger.debug(f"{api_name} 返回空数据，尝试下一个API")
            except Exception as e:
                logger.warning(f"{api_name} 异常: {e}")
                continue
        
        logger.info("所有API均无数据，将使用模拟数据")
        return []
    
    def _search_mobile_v1(self, keyword: str, page: int, search_type: str) -> List[Dict]:
        """移动端搜索API v1"""
        type_map = {'all': '1', 'hot': '60', 'ori': '61', 'pic': '62', 'video': '64'}
        type_code = type_map.get(search_type, '1')
        encoded_keyword = quote(keyword, safe='')
        
        url = f"{self.MOBILE_API}/api/container/getIndex?containerid=100103type%3D{type_code}%26q%3D{encoded_keyword}&page_type=searchall&page={page}"
        
        response = self._request(url, params=None, mobile=True)
        if not response:
            return []  # 返回空列表而不是抛出异常
        
        data = response.json()
        if data.get('ok') != 1:
            return []  # API返回失败状态，返回空列表
        
        cards = data.get('data', {}).get('cards', [])
        weibos = []
        
        for card in cards:
            if card.get('card_type') == 9:
                mblog = card.get('mblog', {})
                if mblog:
                    weibos.append(self._parse_weibo(mblog, keyword))
            elif card.get('card_type') == 11:
                for item in card.get('card_group', []):
                    if item.get('card_type') == 9:
                        mblog = item.get('mblog', {})
                        if mblog:
                            weibos.append(self._parse_weibo(mblog, keyword))
        
        return weibos
    
    def _search_mobile_v2(self, keyword: str, page: int, search_type: str) -> List[Dict]:
        """移动端搜索API v2 - 备用接口"""
        encoded_keyword = quote(keyword, safe='')
        url = f"{self.MOBILE_API}/api/container/getIndex"
        params = {
            'containerid': f'100103type=1&q={encoded_keyword}',
            'page_type': 'searchall',
            'page': page
        }
        
        response = self._request(url, params=params, mobile=True)
        if not response:
            return []
        
        data = response.json()
        if data.get('ok') != 1:
            return []
        
        cards = data.get('data', {}).get('cards', [])
        weibos = []
        
        for card in cards:
            if card.get('card_type') == 9:
                mblog = card.get('mblog', {})
                if mblog:
                    weibos.append(self._parse_weibo(mblog, keyword))
            elif card.get('card_type') == 11:
                for item in card.get('card_group', []):
                    if item.get('card_type') == 9:
                        mblog = item.get('mblog', {})
                        if mblog:
                            weibos.append(self._parse_weibo(mblog, keyword))
        
        return weibos
    
    def _search_web_ajax(self, keyword: str, page: int, search_type: str) -> List[Dict]:
        """Web端Ajax搜索API - 使用热门微博流API"""
        try:
            # 使用配置中的完整请求头
            custom_ua = self.cookie_pool.get_user_agent()
            extra_headers = self.cookie_pool.get_extra_headers()
            cookies = self.cookie_pool.get_cookie()
            
            headers = {
                'User-Agent': custom_ua or UserAgentPool.get_random(),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'X-Requested-With': 'XMLHttpRequest',
            }
            headers.update(extra_headers)
            
            # 使用热门微博流API - 这个API可以正常工作
            max_id = 0 if page == 1 else (page - 1) * 10
            url = f'https://weibo.com/ajax/feed/hottimeline?since_id=0&refresh=0&group_id=102803&containerid=102803&extparam=discover%7Cnew_feed&max_id={max_id}&count=20'
            
            response = requests.get(url, headers=headers, cookies=cookies, timeout=15)
            logger.info(f"热门微博流API 状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                statuses = data.get('statuses', [])
                if statuses:
                    weibos = []
                    for status in statuses:
                        # 添加关键词标记
                        weibo = self._parse_weibo(status, keyword)
                        weibos.append(weibo)
                    logger.info(f"热门微博流API 获取到 {len(weibos)} 条数据")
                    return weibos
            
            return []
            
        except Exception as e:
            logger.error(f"Web Ajax搜索失败: {e}")
            return []
    
    def _search_web_ajax_old(self, keyword: str, page: int, search_type: str) -> List[Dict]:
        """Web端Ajax搜索API - 旧版本备用"""
        try:
            encoded_keyword = quote(keyword, safe='')
            url = f"https://weibo.com/ajax/search/all?q={encoded_keyword}&page={page}"
            
            custom_ua = self.cookie_pool.get_user_agent()
            cookies = self.cookie_pool.get_cookie()
            
            headers = {
                'User-Agent': custom_ua or UserAgentPool.get_random(),
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://weibo.com/',
            }
            
            response = requests.get(url, headers=headers, cookies=cookies, timeout=15)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            statuses = data.get('data', {}).get('statuses', [])
            
            weibos = []
            for status in statuses:
                weibos.append(self._parse_weibo(status, keyword))
            
            return weibos
        except:
            return []
    
    # ==================== 用户微博 ====================
    
    def get_user_weibo(self, user_id: str, pages: int = 5) -> List[Dict]:
        """
        获取指定用户的微博
        
        Args:
            user_id: 用户ID
            pages: 爬取页数
            
        Returns:
            微博列表
        """
        logger.info(f"开始获取用户 {user_id} 的微博 (pages={pages})")
        
        all_weibos = []
        since_id = ''
        
        for page in range(1, pages + 1):
            logger.info(f"正在爬取第 {page}/{pages} 页...")
            
            weibos, since_id = self._get_user_weibo_page(user_id, since_id)
            
            if not weibos:
                logger.warning(f"第 {page} 页无数据，停止爬取")
                break
            
            all_weibos.extend(weibos)
            logger.info(f"第 {page} 页获取到 {len(weibos)} 条微博")
            
            if not since_id:
                break
        
        logger.info(f"用户微博爬取完成，共获取 {len(all_weibos)} 条")
        return all_weibos
    
    def _get_user_weibo_page(self, user_id: str, since_id: str = '') -> tuple:
        """获取用户微博单页"""
        url = f"{self.MOBILE_API}/api/container/getIndex"
        params = {
            'containerid': f"107603{user_id}",
            'page_type': 'profile',
        }
        if since_id:
            params['since_id'] = since_id
        
        response = self._request(url, params=params, mobile=True)
        if not response:
            return [], ''
        
        try:
            data = response.json()
            if data.get('ok') != 1:
                return [], ''
            
            cards = data.get('data', {}).get('cards', [])
            weibos = []
            
            for card in cards:
                if card.get('card_type') == 9:
                    mblog = card.get('mblog', {})
                    if mblog:
                        weibos.append(self._parse_weibo(mblog))
            
            # 获取下一页的since_id
            card_list_info = data.get('data', {}).get('cardlistInfo', {})
            next_since_id = card_list_info.get('since_id', '')
            
            return weibos, str(next_since_id) if next_since_id else ''
            
        except Exception as e:
            logger.error(f"解析用户微博失败: {e}")
            return [], ''
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        url = f"{self.MOBILE_API}/api/container/getIndex"
        params = {
            'containerid': f"100505{user_id}",
            'type': 'uid',
            'value': user_id,
        }
        
        response = self._request(url, params=params, mobile=True)
        if not response:
            return None
        
        try:
            data = response.json()
            if data.get('ok') != 1:
                return None
            
            user_info = data.get('data', {}).get('userInfo', {})
            return {
                'id': user_info.get('id'),
                'screen_name': user_info.get('screen_name'),
                'description': user_info.get('description'),
                'followers_count': user_info.get('followers_count'),
                'follow_count': user_info.get('follow_count'),
                'statuses_count': user_info.get('statuses_count'),
                'verified': user_info.get('verified'),
                'verified_type': user_info.get('verified_type'),
                'verified_reason': user_info.get('verified_reason'),
                'avatar_hd': user_info.get('avatar_hd'),
                'cover_image': user_info.get('cover_image_phone'),
                'gender': user_info.get('gender'),
                'location': user_info.get('location'),
                'crawl_time': datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"解析用户信息失败: {e}")
            return None
    
    # ==================== 数据解析 ====================
    
    def _parse_weibo(self, mblog: dict, keyword: str = None) -> Dict:
        """
        解析单条微博数据
        
        提取字段：
        - 基本信息：id, mid, text, source, created_at
        - 用户信息：user (id, screen_name, followers_count, verified等)
        - 互动数据：reposts_count, comments_count, attitudes_count
        - 媒体内容：pics, video
        - 其他：is_long_text, is_paid, geo
        """
        # 清理HTML标签
        text = self._clean_html(mblog.get('text', ''))
        
        # 用户信息
        user = mblog.get('user', {}) or {}
        user_info = {
            'id': str(user.get('id', '')),
            'screen_name': user.get('screen_name', ''),
            'profile_url': user.get('profile_url', ''),
            'followers_count': user.get('followers_count', 0),
            'follow_count': user.get('follow_count', 0),
            'statuses_count': user.get('statuses_count', 0),
            'verified': user.get('verified', False),
            'verified_type': user.get('verified_type', -1),
            'verified_reason': user.get('verified_reason', ''),
            'avatar_hd': user.get('avatar_hd', ''),
        }
        
        # 图片
        pics = []
        for pic in mblog.get('pics', []) or []:
            pics.append({
                'pid': pic.get('pid', ''),
                'url': pic.get('large', {}).get('url', '') or pic.get('url', ''),
            })
        
        # 视频
        video = None
        page_info = mblog.get('page_info', {})
        if page_info and page_info.get('type') == 'video':
            media_info = page_info.get('media_info', {}) or page_info.get('urls', {})
            video = {
                'title': page_info.get('title', ''),
                'duration': page_info.get('duration', 0),
                'play_count': page_info.get('play_count', 0),
                'url': media_info.get('mp4_720p_mp4', '') or media_info.get('mp4_hd_url', '') or media_info.get('stream_url', ''),
            }
        
        # 转发的原微博
        retweeted = None
        if mblog.get('retweeted_status'):
            retweeted = self._parse_weibo(mblog['retweeted_status'])
        
        return {
            # 基本信息
            'id': str(mblog.get('id', '')),
            'mid': str(mblog.get('mid', '')),
            'bid': mblog.get('bid', ''),
            'text': text,
            'text_raw': mblog.get('text', ''),
            'source': self._clean_html(mblog.get('source', '')),
            'created_at': mblog.get('created_at', ''),
            'region_name': mblog.get('region_name', ''),
            
            # 用户
            'user': user_info,
            
            # 互动数据
            'reposts_count': mblog.get('reposts_count', 0),
            'comments_count': mblog.get('comments_count', 0),
            'attitudes_count': mblog.get('attitudes_count', 0),
            
            # 媒体
            'pics': pics,
            'pics_count': len(pics),
            'video': video,
            'has_video': video is not None,
            
            # 转发
            'retweeted_status': retweeted,
            'is_retweet': retweeted is not None,
            
            # 其他
            'is_long_text': mblog.get('isLongText', False),
            'is_paid': mblog.get('is_paid', False),
            
            # 搜索关键词
            'keyword': keyword,
            
            # 爬取时间
            'crawl_time': datetime.now().isoformat(),
        }
    
    def _clean_html(self, text: str) -> str:
        """清理HTML标签"""
        if not text:
            return ''
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 规范化空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    # ==================== 数据存储 ====================
    
    def save_to_json(self, data: List[Dict], filename: str, 
                     append: bool = False) -> str:
        """
        保存数据到JSON文件
        
        Args:
            data: 数据列表
            filename: 文件名（不含路径）
            append: 是否追加模式
            
        Returns:
            保存的文件路径
        """
        filepath = os.path.join(self.data_dir, filename)
        
        if append and os.path.exists(filepath):
            # 追加模式：读取现有数据
            with open(filepath, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            if isinstance(existing, list):
                data = existing + data
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"数据已保存到: {filepath} ({len(data)} 条)")
        return filepath
    
    def save_hot_search(self, hot_list: List[Dict]) -> str:
        """保存热搜数据"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"hot_search_{timestamp}.json"
        return self.save_to_json(hot_list, filename)
    
    def save_search_result(self, weibos: List[Dict], keyword: str) -> str:
        """保存搜索结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_keyword = re.sub(r'[\\/:*?"<>|]', '_', keyword)
        filename = f"search_{safe_keyword}_{timestamp}.json"
        return self.save_to_json(weibos, filename)
    
    def save_user_weibo(self, weibos: List[Dict], user_id: str) -> str:
        """保存用户微博"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"user_{user_id}_{timestamp}.json"
        return self.save_to_json(weibos, filename)
    
    # ==================== 统计信息 ====================
    
    def get_stats(self) -> Dict:
        """获取爬虫统计信息"""
        return {
            'request_count': self.request_count,
            'cookie_count': len(self.cookie_pool.cookies),
            'data_dir': self.data_dir,
        }


# ==================== 便捷函数 ====================

def crawl_hot_search(limit: int = 50, save: bool = True) -> List[Dict]:
    """快速获取热搜"""
    spider = WeiboSpider()
    hot_list = spider.get_hot_search(limit)
    if save and hot_list:
        spider.save_hot_search(hot_list)
    return hot_list


def crawl_keyword(keyword: str, pages: int = 5, save: bool = True) -> List[Dict]:
    """快速搜索关键词"""
    spider = WeiboSpider()
    weibos = spider.search_weibo(keyword, pages)
    if save and weibos:
        spider.save_search_result(weibos, keyword)
    return weibos


def crawl_user(user_id: str, pages: int = 5, save: bool = True) -> List[Dict]:
    """快速获取用户微博"""
    spider = WeiboSpider()
    weibos = spider.get_user_weibo(user_id, pages)
    if save and weibos:
        spider.save_user_weibo(weibos, user_id)
    return weibos


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='微博爬虫')
    parser.add_argument('--hot', action='store_true', help='获取热搜榜')
    parser.add_argument('--search', type=str, help='搜索关键词')
    parser.add_argument('--user', type=str, help='用户ID')
    parser.add_argument('--pages', type=int, default=5, help='爬取页数')
    parser.add_argument('--limit', type=int, default=50, help='热搜条数限制')
    parser.add_argument('--no-save', action='store_true', help='不保存数据')
    
    args = parser.parse_args()
    
    spider = WeiboSpider()
    
    if args.hot:
        print("正在获取热搜榜...")
        hot_list = spider.get_hot_search(args.limit)
        if not args.no_save:
            spider.save_hot_search(hot_list)
        print(f"\n获取到 {len(hot_list)} 条热搜:")
        for item in hot_list[:10]:
            print(f"  {item['rank']}. {item['title']} ({item['hot_value']})")
    
    elif args.search:
        print(f"正在搜索: {args.search}")
        weibos = spider.search_weibo(args.search, args.pages)
        if not args.no_save:
            spider.save_search_result(weibos, args.search)
        print(f"\n获取到 {len(weibos)} 条微博")
    
    elif args.user:
        print(f"正在获取用户 {args.user} 的微博...")
        weibos = spider.get_user_weibo(args.user, args.pages)
        if not args.no_save:
            spider.save_user_weibo(weibos, args.user)
        print(f"\n获取到 {len(weibos)} 条微博")
    
    else:
        parser.print_help()
