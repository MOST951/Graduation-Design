"""
微博API客户端模块
=================

支持：
- 移动端API (m.weibo.cn)
- Web端Ajax API (weibo.com/ajax)
- 搜索API (s.weibo.com)
"""

import re
import time
import random
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .ua_pool import UserAgentPool
from .cookie_pool import CookiePool
from .proxy_pool import ProxyPool

logger = logging.getLogger('WeiboAPIClient')


class WeiboAPIClient:
    """
    微博API客户端
    
    支持：
    - 移动端API (m.weibo.cn)
    - Web端Ajax API (weibo.com/ajax)
    - 搜索API (s.weibo.com)
    """
    
    MOBILE_API = "https://m.weibo.cn"
    WEB_API = "https://weibo.com"
    SEARCH_API = "https://s.weibo.com"
    
    def __init__(self, cookie_pool: CookiePool, proxy_pool: ProxyPool = None):
        self.cookie_pool = cookie_pool
        self.proxy_pool = proxy_pool
        self.session = self._create_session()
        self.request_count = 0
        self.last_request_time = 0
    
    def _create_session(self) -> requests.Session:
        """创建带重试机制的Session"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def _get_headers(self, mobile: bool = True) -> Dict[str, str]:
        """获取请求头"""
        if mobile:
            return {
                'User-Agent': UserAgentPool.get_weibo_mobile(),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://m.weibo.cn/',
                'X-Requested-With': 'XMLHttpRequest',
                'MWeibo-Pwa': '1',
            }
        else:
            return {
                'User-Agent': UserAgentPool.get_desktop(),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://weibo.com/',
                'X-Requested-With': 'XMLHttpRequest',
            }
    
    def _delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """随机延迟（反爬）"""
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(min_sec, max_sec)
        if elapsed < delay:
            time.sleep(delay - elapsed)
    
    def request(self, url: str, params: dict = None, method: str = 'GET',
                mobile: bool = True, retry: int = 3, 
                delay_range: Tuple[float, float] = (1.0, 3.0)) -> Optional[Dict]:
        """
        发送API请求
        
        Args:
            url: 请求URL
            params: 请求参数
            method: 请求方法
            mobile: 是否使用移动端UA
            retry: 重试次数
            delay_range: 延迟范围(秒)
            
        Returns:
            JSON响应数据或None
        """
        self._delay(*delay_range)
        
        headers = self._get_headers(mobile)
        cookies = self.cookie_pool.get_cookie()
        proxies = self.proxy_pool.get_proxy() if self.proxy_pool else None
        
        for attempt in range(retry):
            try:
                self.request_count += 1
                self.last_request_time = time.time()
                
                if method.upper() == 'GET':
                    response = self.session.get(
                        url, params=params, headers=headers,
                        cookies=cookies, proxies=proxies, timeout=15
                    )
                else:
                    response = self.session.post(
                        url, data=params, headers=headers,
                        cookies=cookies, proxies=proxies, timeout=15
                    )
                
                if response.status_code == 200:
                    if proxies and self.proxy_pool:
                        self.proxy_pool.mark_success(proxies)
                    self.cookie_pool.mark_success()
                    return response.json()
                elif response.status_code == 418:
                    logger.warning("触发反爬机制，切换Cookie和代理...")
                    self.cookie_pool.mark_failed()
                    if proxies and self.proxy_pool:
                        self.proxy_pool.mark_failed(proxies)
                    time.sleep(random.uniform(5, 10))
                elif response.status_code == 403:
                    logger.warning("访问被禁止，可能需要登录")
                    self.cookie_pool.mark_failed()
                else:
                    logger.warning(f"请求失败: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{retry})")
                if proxies and self.proxy_pool:
                    self.proxy_pool.mark_failed(proxies)
            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常: {e}")
                if proxies and self.proxy_pool:
                    self.proxy_pool.mark_failed(proxies)
            except Exception as e:
                logger.error(f"未知异常: {e}")
            
            if attempt < retry - 1:
                # 更换代理重试
                proxies = self.proxy_pool.get_proxy() if self.proxy_pool else None
                time.sleep(random.uniform(2, 5))
        
        return None
    
    # ==================== 热搜榜API ====================
    
    def get_hot_search(self, limit: int = 50) -> List[Dict]:
        """获取热搜榜"""
        # 方法1: Web Ajax API
        hot_list = self._get_hot_search_ajax()
        if hot_list:
            return hot_list[:limit]
        
        # 方法2: 移动端API
        hot_list = self._get_hot_search_mobile()
        if hot_list:
            return hot_list[:limit]
        
        logger.warning("无法获取热搜数据")
        return []
    
    def _get_hot_search_ajax(self) -> List[Dict]:
        """通过Ajax API获取热搜"""
        url = f"{self.WEB_API}/ajax/side/hotSearch"
        
        try:
            headers = {
                'User-Agent': UserAgentPool.get_desktop(),
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://weibo.com/',
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return []
            
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
                    'is_fei': item.get('is_fei', 0) == 1,
                    'url': f"https://s.weibo.com/weibo?q=%23{quote(item.get('word', ''), safe='')}%23",
                    'crawl_time': datetime.now().isoformat(),
                })
            
            logger.info(f"Ajax API获取到 {len(hot_list)} 条热搜")
            return hot_list
            
        except Exception as e:
            logger.error(f"Ajax热搜API失败: {e}")
            return []
    
    def _get_hot_search_mobile(self) -> List[Dict]:
        """通过移动端API获取热搜"""
        url = f"{self.MOBILE_API}/api/container/getIndex"
        params = {'containerid': '106003type=25&t=3&disable_hot=1&filter_type=realtimehot'}
        
        data = self.request(url, params=params, mobile=True)
        if not data or data.get('ok') != 1:
            return []
        
        hot_list = []
        cards = data.get('data', {}).get('cards', [])
        
        for card in cards:
            card_group = card.get('card_group', [])
            for item in card_group:
                if item.get('card_type') == 4:
                    desc = item.get('desc', '')
                    hot_list.append({
                        'rank': len(hot_list) + 1,
                        'title': desc,
                        'hot_value': self._extract_number(item.get('desc_extr', '')),
                        'category': '',
                        'url': item.get('scheme', ''),
                        'crawl_time': datetime.now().isoformat(),
                    })
        
        logger.info(f"移动端API获取到 {len(hot_list)} 条热搜")
        return hot_list
    
    # ==================== 搜索API ====================
    
    def search_weibo(self, keyword: str, page: int = 1, 
                     search_type: str = 'all') -> List[Dict]:
        """
        搜索微博
        
        Args:
            keyword: 搜索关键词
            page: 页码
            search_type: 搜索类型 (all/hot/ori/pic/video)
            
        Returns:
            微博列表
        """
        type_map = {'all': '1', 'hot': '60', 'ori': '61', 'pic': '62', 'video': '64'}
        type_code = type_map.get(search_type, '1')
        
        encoded_keyword = quote(keyword, safe='')
        url = f"{self.MOBILE_API}/api/container/getIndex?containerid=100103type%3D{type_code}%26q%3D{encoded_keyword}&page_type=searchall&page={page}"
        
        data = self.request(url, params=None, mobile=True)
        if not data or data.get('ok') != 1:
            return []
        
        weibos = []
        cards = data.get('data', {}).get('cards', [])
        
        for card in cards:
            if card.get('card_type') == 9:
                mblog = card.get('mblog', {})
                if mblog:
                    weibos.append(self._parse_weibo(mblog, keyword=keyword))
            elif card.get('card_type') == 11:
                for item in card.get('card_group', []):
                    if item.get('card_type') == 9:
                        mblog = item.get('mblog', {})
                        if mblog:
                            weibos.append(self._parse_weibo(mblog, keyword=keyword))
        
        return weibos
    
    # ==================== 话题API ====================
    
    def get_topic_weibo(self, topic: str, page: int = 1) -> List[Dict]:
        """
        获取话题下的微博
        
        Args:
            topic: 话题名称（不含#）
            page: 页码
            
        Returns:
            微博列表
        """
        encoded_topic = quote(topic, safe='')
        url = f"{self.MOBILE_API}/api/container/getIndex"
        params = {
            'containerid': f"100808{encoded_topic}_-_feed",
            'page': page
        }
        
        data = self.request(url, params=params, mobile=True)
        if not data or data.get('ok') != 1:
            # 备用：使用搜索
            return self.search_weibo(f"#{topic}#", page)
        
        weibos = []
        cards = data.get('data', {}).get('cards', [])
        
        for card in cards:
            if card.get('card_type') == 9:
                mblog = card.get('mblog', {})
                if mblog:
                    weibos.append(self._parse_weibo(mblog, topic=topic))
        
        return weibos
    
    # ==================== 用户时间线API ====================
    
    def get_user_timeline(self, user_id: str, page: int = 1, 
                          since_id: str = '') -> Tuple[List[Dict], str]:
        """
        获取用户时间线
        
        Args:
            user_id: 用户ID
            page: 页码
            since_id: 分页标识
            
        Returns:
            (微博列表, 下一页since_id)
        """
        url = f"{self.MOBILE_API}/api/container/getIndex"
        params = {
            'containerid': f"107603{user_id}",
            'page_type': 'profile',
        }
        if since_id:
            params['since_id'] = since_id
        
        data = self.request(url, params=params, mobile=True)
        if not data or data.get('ok') != 1:
            return [], ''
        
        weibos = []
        cards = data.get('data', {}).get('cards', [])
        
        for card in cards:
            if card.get('card_type') == 9:
                mblog = card.get('mblog', {})
                if mblog:
                    weibos.append(self._parse_weibo(mblog))
        
        # 获取下一页标识
        card_list_info = data.get('data', {}).get('cardlistInfo', {})
        next_since_id = str(card_list_info.get('since_id', ''))
        
        return weibos, next_since_id
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        url = f"{self.MOBILE_API}/api/container/getIndex"
        params = {
            'containerid': f"100505{user_id}",
            'type': 'uid',
            'value': user_id,
        }
        
        data = self.request(url, params=params, mobile=True)
        if not data or data.get('ok') != 1:
            return None
        
        user_info = data.get('data', {}).get('userInfo', {})
        return {
            'id': str(user_info.get('id', '')),
            'screen_name': user_info.get('screen_name', ''),
            'description': user_info.get('description', ''),
            'followers_count': user_info.get('followers_count', 0),
            'follow_count': user_info.get('follow_count', 0),
            'statuses_count': user_info.get('statuses_count', 0),
            'verified': user_info.get('verified', False),
            'verified_type': user_info.get('verified_type', -1),
            'verified_reason': user_info.get('verified_reason', ''),
            'avatar_hd': user_info.get('avatar_hd', ''),
            'gender': user_info.get('gender', ''),
            'location': user_info.get('location', ''),
            'crawl_time': datetime.now().isoformat(),
        }
    
    # ==================== 评论API ====================
    
    def get_comments(self, weibo_id: str, page: int = 1) -> List[Dict]:
        """获取微博评论"""
        url = f"{self.MOBILE_API}/api/comments/show"
        params = {'id': weibo_id, 'page': page}
        
        data = self.request(url, params=params, mobile=True)
        if not data or data.get('ok') != 1:
            return []
        
        comments = []
        for item in data.get('data', {}).get('data', []):
            user = item.get('user', {}) or {}
            comments.append({
                'id': str(item.get('id', '')),
                'text': self._clean_html(item.get('text', '')),
                'created_at': item.get('created_at', ''),
                'user_id': str(user.get('id', '')),
                'user_name': user.get('screen_name', ''),
                'like_count': item.get('like_count', 0),
                'weibo_id': weibo_id,
                'crawl_time': datetime.now().isoformat(),
            })
        
        return comments
    
    # ==================== 数据解析 ====================
    
    def _parse_weibo(self, mblog: dict, keyword: str = None, 
                     topic: str = None) -> Dict:
        """解析微博数据"""
        text = self._clean_html(mblog.get('text', ''))
        user = mblog.get('user', {}) or {}
        
        # 图片
        pics = []
        for pic in mblog.get('pics', []) or []:
            pic_url = pic.get('large', {}).get('url', '') or pic.get('url', '')
            if pic_url:
                pics.append(pic_url)
        
        # 视频
        video_url = None
        page_info = mblog.get('page_info', {})
        if page_info and page_info.get('type') == 'video':
            media_info = page_info.get('media_info', {}) or page_info.get('urls', {})
            video_url = (media_info.get('mp4_720p_mp4', '') or 
                        media_info.get('mp4_hd_url', '') or 
                        media_info.get('stream_url', ''))
        
        # 生成内容哈希
        content_hash = hashlib.md5(
            f"{mblog.get('id', '')}{text}".encode('utf-8')
        ).hexdigest()
        
        return {
            'id': str(mblog.get('id', '')),
            'mid': str(mblog.get('mid', '')),
            'bid': mblog.get('bid', ''),
            'text': text,
            'text_raw': mblog.get('text', ''),
            'source': self._clean_html(mblog.get('source', '')),
            'created_at': mblog.get('created_at', ''),
            'region_name': mblog.get('region_name', ''),
            'user_id': str(user.get('id', '')),
            'user_name': user.get('screen_name', ''),
            'user_verified': user.get('verified', False),
            'user_followers': user.get('followers_count', 0),
            'reposts_count': mblog.get('reposts_count', 0),
            'comments_count': mblog.get('comments_count', 0),
            'attitudes_count': mblog.get('attitudes_count', 0),
            'pics': pics,
            'video_url': video_url,
            'is_long_text': mblog.get('isLongText', False),
            'keyword': keyword,
            'topic': topic,
            'content_hash': content_hash,
            'crawl_time': datetime.now().isoformat(),
        }
    
    def _clean_html(self, text: str) -> str:
        """清理HTML标签"""
        if not text:
            return ''
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _extract_number(self, text: str) -> int:
        """提取数字"""
        if not text:
            return 0
        match = re.search(r'(\d+)', text.replace(',', ''))
        return int(match.group(1)) if match else 0
    
    def get_stats(self) -> Dict:
        """获取API客户端统计信息"""
        return {
            'request_count': self.request_count,
            'cookie_pool_size': self.cookie_pool.size,
            'proxy_pool_size': self.proxy_pool.size if self.proxy_pool else 0
        }
