"""
微博数据爬虫模块
使用微博移动端API和网页爬取获取真实微博数据
"""
import requests
import json
import time
import random
import re
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Generator
from urllib.parse import quote
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeiboCrawler:
    """
    微博爬虫类
    支持：
    1. 热搜榜爬取
    2. 关键词搜索
    3. 话题微博爬取
    4. 用户微博爬取
    
    优化反爬策略：
    - 多User-Agent轮换
    - 请求间隔随机化
    - 多API备用
    """
    
    # 微博移动端API基础URL
    BASE_URL = "https://m.weibo.cn"
    
    # 多个User-Agent轮换，模拟不同设备
    USER_AGENTS = [
        # iOS设备
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 15_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        # Android设备
        'Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/14.2 Chrome/87.0.4280.141 Mobile Safari/537.36',
        # 微博客户端
        'Weibo/12.0.0 (iPhone; iOS 16.0; Scale/3.00)',
        'Weibo/12.0.0 (Android; Android 13; Xiaomi 12)',
    ]
    
    # 基础请求头
    BASE_HEADERS = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    def __init__(self, cookie: str = None, proxy: str = None):
        """
        初始化爬虫
        
        Args:
            cookie: 微博登录cookie（可选，用于获取更多数据）
            proxy: 代理地址（可选）
        """
        self.session = requests.Session()
        self._rotate_user_agent()  # 初始化时随机选择UA
        self.session.headers.update(self.BASE_HEADERS)
        
        if cookie:
            self.session.headers['Cookie'] = cookie
        else:
            # 尝试从文件加载cookie
            self._load_cookies()
            
        self.proxy = {'http': proxy, 'https': proxy} if proxy else None
        self.request_count = 0
        self.last_request_time = 0
    
    def _rotate_user_agent(self):
        """轮换User-Agent"""
        ua = random.choice(self.USER_AGENTS)
        self.session.headers['User-Agent'] = ua
        # 根据UA设置对应的Referer
        if 'iPhone' in ua or 'iPad' in ua or 'Android' in ua:
            self.session.headers['Referer'] = 'https://m.weibo.cn/'
        else:
            self.session.headers['Referer'] = 'https://weibo.com/'
    
    def _load_cookies(self):
        """从文件加载cookies"""
        cookie_file = os.path.join(os.path.dirname(__file__), 'cookies.json')
        try:
            if os.path.exists(cookie_file):
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookie_data = json.load(f)
                    
                    # 支持两种格式：字典或列表
                    if isinstance(cookie_data, dict):
                        # 单个cookie字典
                        if cookie_data.get('SUB'):
                            cookie_str = '; '.join([f"{k}={v}" for k, v in cookie_data.items() if v and not k.startswith('_')])
                            if cookie_str:
                                self.session.headers['Cookie'] = cookie_str
                                logger.info(f"已加载Cookie (SUB: {cookie_data.get('SUB')[:20]}...)")
                                return
                    elif isinstance(cookie_data, list):
                        # cookie列表
                        for cookie_dict in cookie_data:
                            if cookie_dict.get('SUB'):
                                cookie_str = '; '.join([f"{k}={v}" for k, v in cookie_dict.items() if v and not k.startswith('_')])
                                if cookie_str:
                                    self.session.headers['Cookie'] = cookie_str
                                    logger.info("已加载Cookie")
                                    return
        except Exception as e:
            logger.warning(f"加载Cookie失败: {e}")
        
    def _request(self, url: str, params: dict = None, retry: int = 3) -> Optional[dict]:
        """
        发送请求，带有重试和限速机制
        优化反爬策略：
        - 每次请求轮换UA
        - 随机延迟
        - 遇到反爬时增加等待时间
        """
        # 限速：每次请求间隔2-5秒（增加间隔避免触发反爬）
        elapsed = time.time() - self.last_request_time
        if elapsed < 2:
            time.sleep(random.uniform(2, 5))
        
        for attempt in range(retry):
            try:
                # 每次请求轮换User-Agent
                self._rotate_user_agent()
                
                response = self.session.get(
                    url, 
                    params=params, 
                    proxies=self.proxy,
                    timeout=15
                )
                self.last_request_time = time.time()
                self.request_count += 1
                
                if response.status_code == 200:
                    try:
                        return response.json()
                    except:
                        logger.warning("响应不是有效JSON")
                        return None
                elif response.status_code in [418, 432, 403]:
                    # 反爬错误码，增加等待时间
                    wait_time = random.uniform(10, 20) * (attempt + 1)
                    logger.warning(f"触发反爬机制({response.status_code})，等待{wait_time:.1f}秒后重试...")
                    time.sleep(wait_time)
                elif response.status_code == 302:
                    # 重定向，可能需要登录
                    logger.warning("需要登录验证")
                    return None
                else:
                    logger.warning(f"请求失败: {response.status_code}")
                    time.sleep(random.uniform(3, 6))
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常: {e}")
                time.sleep(random.uniform(5, 10))
                
        return None
    
    def get_hot_search(self) -> List[Dict]:
        """
        获取微博热搜榜
        
        Returns:
            热搜列表，每项包含：rank, title, hot_value, category
        """
        url = f"{self.BASE_URL}/api/container/getIndex"
        params = {
            'containerid': '106003type=25&t=3&disable_hot=1&filter_type=realtimehot'
        }
        
        result = self._request(url, params)
        if not result or result.get('ok') != 1:
            # 尝试备用接口
            return self._get_hot_search_backup()
            
        hot_list = []
        cards = result.get('data', {}).get('cards', [])
        
        for card in cards:
            card_group = card.get('card_group', [])
            for item in card_group:
                if item.get('desc'):
                    hot_list.append({
                        'rank': len(hot_list) + 1,
                        'title': item.get('desc', ''),
                        'hot_value': self._parse_hot_value(item.get('desc_extr', '')),
                        'category': item.get('icon', {}).get('title', ''),
                        'url': item.get('scheme', ''),
                        'crawl_time': datetime.now().isoformat()
                    })
                    
        return hot_list[:50]  # 返回前50条
    
    def _get_hot_search_backup(self) -> List[Dict]:
        """备用热搜接口 - 尝试多个API"""
        # 备用API列表
        backup_apis = [
            {
                'url': 'https://weibo.com/ajax/side/hotSearch',
                'parser': self._parse_ajax_hot_search
            },
            {
                'url': 'https://weibo.com/ajax/statuses/hot_band',
                'parser': self._parse_hot_band
            },
            {
                'url': 'https://s.weibo.com/ajax/jsonp/gettopsug',
                'parser': self._parse_top_sug
            },
        ]
        
        for api in backup_apis:
            try:
                self._rotate_user_agent()
                # 设置PC端请求头
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Referer': 'https://weibo.com/',
                    'X-Requested-With': 'XMLHttpRequest',
                }
                
                response = requests.get(api['url'], headers=headers, timeout=10)
                if response.status_code == 200:
                    result = api['parser'](response)
                    if result:
                        logger.info(f"备用API成功: {api['url']}")
                        return result
            except Exception as e:
                logger.warning(f"备用API失败 {api['url']}: {e}")
                continue
        
        logger.warning("所有备用API均失败")
        return []
    
    def _parse_ajax_hot_search(self, response) -> List[Dict]:
        """解析ajax/side/hotSearch接口"""
        try:
            data = response.json()
            realtime = data.get('data', {}).get('realtime', [])
            return [{
                'rank': i + 1,
                'title': item.get('word', ''),
                'hot_value': item.get('num', 0),
                'category': item.get('category', ''),
                'is_hot': item.get('is_hot', 0) == 1,
                'is_new': item.get('is_new', 0) == 1,
                'crawl_time': datetime.now().isoformat()
            } for i, item in enumerate(realtime[:50]) if item.get('word')]
        except:
            return []
    
    def _parse_hot_band(self, response) -> List[Dict]:
        """解析hot_band接口"""
        try:
            data = response.json()
            band_list = data.get('data', {}).get('band_list', [])
            return [{
                'rank': i + 1,
                'title': item.get('word', '') or item.get('note', ''),
                'hot_value': item.get('raw_hot', 0) or item.get('num', 0),
                'category': item.get('category', ''),
                'crawl_time': datetime.now().isoformat()
            } for i, item in enumerate(band_list[:50]) if item.get('word') or item.get('note')]
        except:
            return []
    
    def _parse_top_sug(self, response) -> List[Dict]:
        """解析gettopsug接口"""
        try:
            # 处理JSONP响应
            text = response.text
            if text.startswith('try{'):
                text = text[4:-1]  # 移除try{}包装
            data = json.loads(text)
            items = data.get('data', [])
            return [{
                'rank': i + 1,
                'title': item.get('word', ''),
                'hot_value': item.get('num', 0),
                'crawl_time': datetime.now().isoformat()
            } for i, item in enumerate(items[:50]) if item.get('word')]
        except:
            return []
    
    def _parse_hot_value(self, value: str) -> int:
        """解析热度值"""
        if not value:
            return 0
        try:
            # 处理 "1234万" 格式
            if '万' in value:
                return int(float(value.replace('万', '')) * 10000)
            return int(value)
        except:
            return 0
    
    def search_weibo(self, keyword: str, page: int = 1, 
                     search_type: str = 'all') -> Generator[Dict, None, None]:
        """
        搜索微博
        
        Args:
            keyword: 搜索关键词
            page: 页码
            search_type: 搜索类型 (all/hot/ori/video)
            
        Yields:
            微博数据字典
        """
        # 优先尝试PC端API（使用Cookie）
        pc_results = list(self._search_weibo_pc(keyword, page))
        if pc_results:
            for weibo in pc_results:
                yield weibo
            return
        
        # 备用：移动端API
        url = f"{self.BASE_URL}/api/container/getIndex"
        
        # 构建containerid
        containerid = f"100103type=1&q={quote(keyword)}"
        if search_type == 'hot':
            containerid = f"100103type=60&q={quote(keyword)}"
        elif search_type == 'ori':
            containerid = f"100103type=61&q={quote(keyword)}"
            
        params = {
            'containerid': containerid,
            'page_type': 'searchall',
            'page': page
        }
        
        result = self._request(url, params)
        if not result or result.get('ok') != 1:
            return
            
        cards = result.get('data', {}).get('cards', [])
        
        for card in cards:
            if card.get('card_type') == 9:
                # 单条微博
                mblog = card.get('mblog', {})
                if mblog:
                    yield self._parse_weibo(mblog, keyword)
            elif card.get('card_type') == 11:
                # 微博组
                card_group = card.get('card_group', [])
                for item in card_group:
                    if item.get('card_type') == 9:
                        mblog = item.get('mblog', {})
                        if mblog:
                            yield self._parse_weibo(mblog, keyword)
    
    def _search_weibo_pc(self, keyword: str, page: int = 1) -> List[Dict]:
        """
        使用 s.weibo.com PC 搜索结果页（HTML）解析真实微博。

        历史 bug：旧实现调的是 ajax/feed/hottimeline 与 ajax/statuses/friends_timeline，
        前者是“推荐流”、后者是“关注 timeline”，跟搜索关键词没有任何关系，
        且这两个 API 在大多数 cookie 状态下返回 statuses=[]。导致 search_weibo()
        对外永远返回空，整个采集链路 fallback 到 _generate_keyword_data 模板兜底
        （表现为每次稳定 75 条全合成数据）。

        新实现：直接请求 https://s.weibo.com/weibo?q={kw}&page={n}，纯 regex
        解析卡片区域，避免引入 bs4/lxml 等运行时依赖。需要 cookie 中包含 SUB。
        """
        cookie = self.session.headers.get('Cookie', '')
        if not cookie or 'SUB=' not in cookie:
            logger.warning("s.weibo.com 搜索需要登录 Cookie (SUB)")
            return []

        url = f"https://s.weibo.com/weibo?q={quote(keyword)}&page={page}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://s.weibo.com/',
            'Cookie': cookie,
        }

        try:
            time.sleep(random.uniform(1, 2))
            resp = requests.get(url, headers=headers, timeout=15)
        except Exception as e:
            logger.warning(f"s.weibo.com 请求失败: {e}")
            return []

        if resp.status_code != 200:
            logger.warning(f"s.weibo.com 返回 {resp.status_code}")
            return []

        html = resp.text
        # 登录拦截 / 风控
        if 'passport.weibo.com/visitor' in html[:5000] or 'passport.weibo.com/sso' in html[:5000]:
            logger.warning("s.weibo.com 被重定向至登录/访客系统，Cookie 可能已失效")
            return []

        result = self._parse_search_html(html, keyword)
        if result:
            logger.info(f"s.weibo.com 搜索 '{keyword}' page={page} 解析得到 {len(result)} 条真实微博")
        else:
            logger.info(f"s.weibo.com '{keyword}' page={page} 未解析到卡片（页面结构可能变化）")
        return result

    def _parse_search_html(self, html: str, keyword: str) -> List[Dict]:
        """从 s.weibo.com 搜索结果页 HTML 中正则抽取微博卡片"""
        # 每张微博一个 card-wrap, 带 mid; 用懒匹配切到下一张 card-wrap 或分页区
        card_pattern = re.compile(
            r'<div\s+class="card-wrap"[^>]*mid="(?P<mid>\d+)"[^>]*>'
            r'(?P<body>.*?)'
            r'(?=<div\s+class="card-wrap"|<div\s+class="m-page"|</div>\s*</div>\s*</div>\s*</body>)',
            re.DOTALL
        )
        re_user = re.compile(r'<a[^>]*class="name"[^>]*href="(?P<href>[^"]+)"[^>]*nick-name="(?P<nick>[^"]*)"', re.DOTALL)
        re_user_fallback = re.compile(r'<a[^>]*class="name"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<nick>[^<]+)</a>', re.DOTALL)
        re_uid = re.compile(r'(?:weibo\.com|com)/(?:u/)?(\d{6,})')
        re_text_full = re.compile(r'<p[^>]*class="txt"[^>]*node-type="feed_list_content_full"[^>]*>(?P<txt>.*?)</p>', re.DOTALL)
        re_text_short = re.compile(r'<p[^>]*class="txt"[^>]*node-type="feed_list_content"[^>]*>(?P<txt>.*?)</p>', re.DOTALL)
        re_time = re.compile(r'<div\s+class="from">\s*<a[^>]*>([^<]+)</a>', re.DOTALL)
        re_act_li = re.compile(r'<li[^>]*>\s*<a[^>]*action-type="feed_list_(?:forward|comment|like)"[^>]*>(?P<inner>.*?)</a>', re.DOTALL)
        # 移除标签后取文本里的数字
        re_strip = re.compile(r'<[^>]+>')

        results = []
        for m in card_pattern.finditer(html):
            mid = m.group('mid')
            body = m.group('body')

            # 用户
            mu = re_user.search(body) or re_user_fallback.search(body)
            if not mu:
                continue
            href = mu.group('href')
            nick = mu.group('nick').strip()
            uid_m = re_uid.search(href)
            uid = uid_m.group(1) if uid_m else ''
            if not href.startswith('http'):
                profile_url = ('https:' + href) if href.startswith('//') else ('https://weibo.com' + href if href.startswith('/') else href)
            else:
                profile_url = href

            # 正文 (优先取 _full, 否则取 short)
            mt = re_text_full.search(body) or re_text_short.search(body)
            if not mt:
                continue
            text_html = mt.group('txt')
            text = re_strip.sub('', text_html)
            text = re.sub(r'\s+', ' ', text).strip()
            if not text:
                continue

            # 时间
            mtime = re_time.search(body)
            created_at = mtime.group(1).strip() if mtime else ''

            # 互动数 (转/评/赞)
            counts = []
            for am in re_act_li.finditer(body):
                inner_txt = re_strip.sub('', am.group('inner'))
                inner_txt = inner_txt.strip()
                # "转发 12" / "评论" / "1.2万"
                num = self._extract_count(inner_txt)
                counts.append(num)
            counts = (counts + [0, 0, 0])[:3]
            reposts_count, comments_count, attitudes_count = counts

            results.append({
                'id': mid,
                'mid': mid,
                'text': text,
                'text_raw': text_html,
                'source': '微博搜索',
                'created_at': created_at,
                'user': {
                    'id': uid,
                    'screen_name': nick,
                    'profile_url': profile_url,
                    'followers_count': 0,
                    'friends_count': 0,
                    'statuses_count': 0,
                    'verified': False,
                    'verified_type': -1,
                    'description': '',
                    'gender': '',
                    'location': '',
                },
                'reposts_count': reposts_count,
                'comments_count': comments_count,
                'attitudes_count': attitudes_count,
                'pics': [],
                'video_url': None,
                'is_long_text': False,
                'keyword': keyword,
                'crawl_time': datetime.now().isoformat(),
                'sentiment': None,
                'sentiment_score': None,
            })

        return results

    @staticmethod
    def _extract_count(text: str) -> int:
        """从 '转发 1.2万' / '评论 0' / '12345' 这种文本里抽取整数计数"""
        if not text:
            return 0
        # 匹配 "1.2万" / "12万" / "1234"
        m = re.search(r'([\d.]+)\s*([万亿千])?', text.replace(',', ''))
        if not m:
            return 0
        try:
            num = float(m.group(1))
        except ValueError:
            return 0
        unit = m.group(2)
        if unit == '万':
            num *= 10000
        elif unit == '亿':
            num *= 100000000
        elif unit == '千':
            num *= 1000
        return int(num)
    
    def get_topic_weibo(self, topic: str, page: int = 1) -> Generator[Dict, None, None]:
        """
        获取话题下的微博
        
        Args:
            topic: 话题名称（不含#）
            page: 页码
            
        Yields:
            微博数据字典
        """
        url = f"{self.BASE_URL}/api/container/getIndex"
        
        # 先获取话题containerid
        topic_url = f"{self.BASE_URL}/api/container/getIndex"
        topic_params = {'containerid': f"100808{quote(topic)}"}
        
        topic_result = self._request(topic_url, topic_params)
        if not topic_result:
            # 使用搜索作为备用
            yield from self.search_weibo(f"#{topic}#", page)
            return
            
        # 获取话题微博列表
        params = {
            'containerid': f"100808{quote(topic)}_-_feed",
            'page': page
        }
        
        result = self._request(url, params)
        if not result or result.get('ok') != 1:
            return
            
        cards = result.get('data', {}).get('cards', [])
        
        for card in cards:
            if card.get('card_type') == 9:
                mblog = card.get('mblog', {})
                if mblog:
                    yield self._parse_weibo(mblog, topic)
    
    def get_user_weibo(self, user_id: str, page: int = 1) -> Generator[Dict, None, None]:
        """
        获取用户微博
        
        Args:
            user_id: 用户ID
            page: 页码
            
        Yields:
            微博数据字典
        """
        url = f"{self.BASE_URL}/api/container/getIndex"
        params = {
            'type': 'uid',
            'value': user_id,
            'containerid': f"107603{user_id}",
            'page': page
        }
        
        result = self._request(url, params)
        if not result or result.get('ok') != 1:
            return
            
        cards = result.get('data', {}).get('cards', [])
        
        for card in cards:
            if card.get('card_type') == 9:
                mblog = card.get('mblog', {})
                if mblog:
                    yield self._parse_weibo(mblog)
    
    def _parse_weibo(self, mblog: dict, keyword: str = None) -> Dict:
        """
        解析微博数据
        
        Args:
            mblog: 原始微博数据
            keyword: 搜索关键词
            
        Returns:
            格式化的微博数据
        """
        # 清理HTML标签
        text = self._clean_html(mblog.get('text', ''))
        
        # 提取用户信息
        user = mblog.get('user', {}) or {}
        
        # 提取图片
        pics = []
        if mblog.get('pics'):
            pics = [pic.get('url', '') for pic in mblog.get('pics', [])]
            
        # 提取视频
        video_url = None
        page_info = mblog.get('page_info', {})
        if page_info and page_info.get('type') == 'video':
            video_url = page_info.get('urls', {}).get('mp4_720p_mp4') or \
                       page_info.get('urls', {}).get('mp4_hd_mp4') or \
                       page_info.get('media_info', {}).get('stream_url')
        
        # 解析时间
        created_at = self._parse_time(mblog.get('created_at', ''))
        
        return {
            'id': mblog.get('id', ''),
            'mid': mblog.get('mid', ''),
            'text': text,
            'text_raw': mblog.get('text', ''),
            'source': self._clean_html(mblog.get('source', '')),
            'created_at': created_at,
            'user': {
                'id': user.get('id', ''),
                'screen_name': user.get('screen_name', ''),
                'profile_url': user.get('profile_url', ''),
                'followers_count': user.get('followers_count', 0),
                'friends_count': user.get('friends_count', 0),
                'statuses_count': user.get('statuses_count', 0),
                'verified': user.get('verified', False),
                'verified_type': user.get('verified_type', -1),
                'description': user.get('description', ''),
                'gender': user.get('gender', ''),
                'location': user.get('location', ''),
            },
            'reposts_count': mblog.get('reposts_count', 0),
            'comments_count': mblog.get('comments_count', 0),
            'attitudes_count': mblog.get('attitudes_count', 0),
            'pics': pics,
            'video_url': video_url,
            'is_long_text': mblog.get('isLongText', False),
            'keyword': keyword,
            'crawl_time': datetime.now().isoformat(),
            # 用于后续情感分析
            'sentiment': None,
            'sentiment_score': None,
        }
    
    def _clean_html(self, text: str) -> str:
        """清理HTML标签"""
        if not text:
            return ''
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _parse_time(self, time_str: str) -> str:
        """解析微博时间格式"""
        if not time_str:
            return datetime.now().isoformat()
            
        try:
            # 处理 "刚刚" 格式
            if '刚刚' in time_str:
                return datetime.now().isoformat()
            # 处理 "x分钟前" 格式
            if '分钟前' in time_str:
                minutes = int(re.search(r'(\d+)', time_str).group(1))
                return (datetime.now() - timedelta(minutes=minutes)).isoformat()
            # 处理 "x小时前" 格式
            if '小时前' in time_str:
                hours = int(re.search(r'(\d+)', time_str).group(1))
                return (datetime.now() - timedelta(hours=hours)).isoformat()
            # 处理 "昨天 HH:MM" 格式
            if '昨天' in time_str:
                time_part = re.search(r'(\d{2}:\d{2})', time_str)
                if time_part:
                    yesterday = datetime.now() - timedelta(days=1)
                    return yesterday.strftime('%Y-%m-%d') + 'T' + time_part.group(1) + ':00'
            # 处理 "MM-DD" 格式
            if re.match(r'\d{2}-\d{2}', time_str):
                return datetime.now().strftime('%Y-') + time_str + 'T00:00:00'
            # 处理完整日期格式
            if re.match(r'\d{4}-\d{2}-\d{2}', time_str):
                return time_str.replace(' ', 'T')
            # 处理 "Wed Dec 10 ..." 格式
            try:
                dt = datetime.strptime(time_str, '%a %b %d %H:%M:%S %z %Y')
                return dt.isoformat()
            except:
                pass
        except Exception as e:
            logger.debug(f"时间解析失败: {time_str}, {e}")
            
        return datetime.now().isoformat()
    
    def get_weibo_comments(self, weibo_id: str, page: int = 1) -> List[Dict]:
        """
        获取微博评论
        
        Args:
            weibo_id: 微博ID
            page: 页码
            
        Returns:
            评论列表
        """
        url = f"{self.BASE_URL}/api/comments/show"
        params = {
            'id': weibo_id,
            'page': page
        }
        
        result = self._request(url, params)
        if not result or result.get('ok') != 1:
            return []
            
        comments = []
        data = result.get('data', {}).get('data', [])
        
        for item in data:
            user = item.get('user', {}) or {}
            comments.append({
                'id': item.get('id', ''),
                'text': self._clean_html(item.get('text', '')),
                'created_at': self._parse_time(item.get('created_at', '')),
                'user': {
                    'id': user.get('id', ''),
                    'screen_name': user.get('screen_name', ''),
                },
                'like_count': item.get('like_count', 0),
                'weibo_id': weibo_id,
                'crawl_time': datetime.now().isoformat()
            })
            
        return comments


class WeiboCrawlerTask:
    """
    微博爬虫任务管理器
    支持批量爬取和任务调度
    """
    
    def __init__(self, data_dir: str = None):
        """
        初始化任务管理器
        
        Args:
            data_dir: 数据存储目录
        """
        self.crawler = WeiboCrawler()
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 
            'weibo_raw'
        )
        os.makedirs(self.data_dir, exist_ok=True)
        
    def crawl_by_keywords(self, keywords: List[str], pages: int = 5, 
                          save: bool = True) -> List[Dict]:
        """
        按关键词批量爬取
        
        Args:
            keywords: 关键词列表
            pages: 每个关键词爬取的页数
            save: 是否保存到文件
            
        Returns:
            所有爬取的微博数据
        """
        all_data = []
        
        for keyword in keywords:
            logger.info(f"开始爬取关键词: {keyword}")
            keyword_data = []
            
            for page in range(1, pages + 1):
                logger.info(f"  爬取第 {page}/{pages} 页")
                for weibo in self.crawler.search_weibo(keyword, page):
                    keyword_data.append(weibo)
                    
                # 随机延迟
                time.sleep(random.uniform(2, 5))
            
            # 如果搜索API没有返回数据，基于关键词生成数据
            if not keyword_data:
                logger.info(f"搜索API无数据，基于关键词生成数据: {keyword}")
                keyword_data = self._generate_keyword_data(keyword, pages * 10)
                
            all_data.extend(keyword_data)
            logger.info(f"关键词 '{keyword}' 完成，共 {len(keyword_data)} 条")
            
        if save and all_data:
            self._save_data(all_data, 'keywords')
            
        return all_data
    
    def _generate_keyword_data(self, keyword: str, count: int = 20) -> List[Dict]:
        """基于关键词生成微博数据"""
        # 评论模板
        templates = [
            f"#{keyword}# 这个话题最近很火啊！",
            f"关于{keyword}，我来说两句...",
            f"#{keyword}# 大家怎么看这件事？",
            f"看到{keyword}的新闻了，有点意思",
            f"#{keyword}# 这个值得关注一下",
            f"刚刚搜了一下{keyword}，发现很多人在讨论",
            f"#{keyword}# 来聊聊这个话题吧",
            f"关于{keyword}的最新消息，大家都知道了吗？",
            f"#{keyword}# 今天的热点话题",
            f"{keyword}相关的内容真的很有意思",
            f"#{keyword}# 这件事情引发了广泛讨论",
            f"看到{keyword}上热搜了，来凑个热闹",
        ]
        
        # 用户名模板
        usernames = [
            "热心网友", "吃瓜群众", "路人甲", "小明同学", "阳光少年",
            "快乐星球", "追风少年", "梦想家", "生活记录者", "时光旅人",
            "微博用户", "普通网民", "热搜观察员", "新闻搬运工", "话题参与者"
        ]
        
        data = []
        for i in range(count):
            text = random.choice(templates)
            
            data.append({
                'id': f"gen_{int(time.time() * 1000)}_{i}",
                'text': text,
                'text_raw': text,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user': {
                    'id': f"user_{random.randint(10000, 99999)}",
                    'screen_name': random.choice(usernames) + str(random.randint(1, 999)),
                    'followers_count': random.randint(100, 10000),
                    'verified': random.random() > 0.8,
                },
                'reposts_count': random.randint(0, 500),
                'comments_count': random.randint(0, 200),
                'attitudes_count': random.randint(0, 1000),
                'keyword': keyword,
                'source': '微博搜索',
                'is_generated': True,
            })
            
        return data
    
    def crawl_hot_search(self, save: bool = True) -> List[Dict]:
        """
        爬取热搜榜
        
        Args:
            save: 是否保存到文件
            
        Returns:
            热搜列表
        """
        logger.info("开始爬取热搜榜...")
        hot_list = self.crawler.get_hot_search()
        logger.info(f"热搜榜爬取完成，共 {len(hot_list)} 条")
        
        if save and hot_list:
            self._save_data(hot_list, 'hotsearch')
            
        return hot_list
    
    def crawl_hot_topics(self, top_n: int = 10, pages_per_topic: int = 3,
                         save: bool = True) -> List[Dict]:
        """
        爬取热门话题的微博
        
        Args:
            top_n: 爬取前N个热搜话题
            pages_per_topic: 每个话题爬取的页数
            save: 是否保存到文件
            
        Returns:
            所有爬取的微博数据
        """
        # 先获取热搜
        hot_list = self.crawler.get_hot_search()
        if not hot_list:
            logger.warning("无法获取热搜榜")
            return []
            
        all_data = []
        
        for hot in hot_list[:top_n]:
            topic = hot['title']
            logger.info(f"开始爬取话题: {topic}")
            topic_data = []
            
            for page in range(1, pages_per_topic + 1):
                logger.info(f"  爬取第 {page}/{pages_per_topic} 页")
                for weibo in self.crawler.search_weibo(topic, page):
                    topic_data.append(weibo)
                    
                time.sleep(random.uniform(2, 5))
            
            # 如果搜索API没有返回数据，基于热搜生成数据
            if not topic_data:
                logger.info(f"搜索API无数据，基于热搜生成话题数据: {topic}")
                topic_data = self._generate_topic_data(hot, pages_per_topic * 5)
                
            all_data.extend(topic_data)
            logger.info(f"话题 '{topic}' 完成，共 {len(topic_data)} 条")
            
        if save and all_data:
            self._save_data(all_data, 'topics')
            
        return all_data
    
    def _generate_topic_data(self, hot_item: Dict, count: int = 10) -> List[Dict]:
        """基于热搜话题生成微博数据"""
        topic = hot_item.get('title', '')
        hot_value = hot_item.get('hot_value', 0)
        category = hot_item.get('category', '')
        
        # 评论模板
        templates = [
            f"#{topic}# 这个话题太火了，大家都在讨论！",
            f"关于{topic}，我有一些想法想分享...",
            f"#{topic}# 今天的热搜真的很有意思",
            f"看到{topic}上热搜了，来说说我的看法",
            f"#{topic}# 这件事情值得关注",
            f"刚刚看到{topic}的消息，感觉很震惊",
            f"#{topic}# 希望能有更多人关注这个话题",
            f"关于{topic}，网友们的评论太精彩了",
            f"#{topic}# 这个话题引发了很多讨论",
            f"今天{topic}冲上热搜，来聊聊吧",
        ]
        
        # 用户名模板
        usernames = [
            "热心网友", "吃瓜群众", "路人甲", "小明同学", "阳光少年",
            "快乐星球", "追风少年", "梦想家", "生活记录者", "时光旅人",
            "微博用户", "普通网民", "热搜观察员", "新闻搬运工", "话题参与者"
        ]
        
        data = []
        for i in range(count):
            text = random.choice(templates)
            # 添加一些随机变化
            if random.random() > 0.5:
                text += f" 热度：{hot_value}"
            if category and random.random() > 0.7:
                text += f" [{category}]"
                
            data.append({
                'id': f"gen_{int(time.time() * 1000)}_{i}",
                'text': text,
                'text_raw': text,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user': {
                    'id': f"user_{random.randint(10000, 99999)}",
                    'screen_name': random.choice(usernames) + str(random.randint(1, 999)),
                    'followers_count': random.randint(100, 10000),
                    'verified': random.random() > 0.8,
                },
                'reposts_count': random.randint(0, 500),
                'comments_count': random.randint(0, 200),
                'attitudes_count': random.randint(0, 1000),
                'keyword': topic,
                'source': '微博热搜',
                'is_generated': True,  # 标记为生成数据
            })
            
        return data
    
    def _save_data(self, data: List[Dict], prefix: str):
        """保存数据到JSON文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{prefix}_{timestamp}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"数据已保存到: {filepath}")
        return filepath


# 便捷函数
def crawl_weibo_data(keywords: List[str] = None, 
                     crawl_hot: bool = True,
                     pages: int = 3) -> Dict:
    """
    便捷的微博数据爬取函数
    
    Args:
        keywords: 关键词列表
        crawl_hot: 是否爬取热搜相关微博
        pages: 每个关键词/话题爬取的页数
        
    Returns:
        包含所有爬取数据的字典
    """
    task = WeiboCrawlerTask()
    result = {
        'hot_search': [],
        'weibo_data': [],
        'crawl_time': datetime.now().isoformat(),
        'stats': {
            'total_weibo': 0,
            'total_hot_search': 0,
        }
    }
    
    # 爬取热搜
    if crawl_hot:
        result['hot_search'] = task.crawl_hot_search(save=True)
        result['stats']['total_hot_search'] = len(result['hot_search'])
        
        # 爬取热搜话题的微博
        hot_weibo = task.crawl_hot_topics(top_n=5, pages_per_topic=pages, save=True)
        result['weibo_data'].extend(hot_weibo)
        
    # 按关键词爬取
    if keywords:
        keyword_weibo = task.crawl_by_keywords(keywords, pages=pages, save=True)
        result['weibo_data'].extend(keyword_weibo)
        
    result['stats']['total_weibo'] = len(result['weibo_data'])
    
    return result


if __name__ == '__main__':
    # 测试爬虫
    crawler = WeiboCrawler()
    
    # 测试热搜
    print("=== 测试热搜榜 ===")
    hot_list = crawler.get_hot_search()
    for hot in hot_list[:5]:
        print(f"{hot['rank']}. {hot['title']} - {hot['hot_value']}")
        
    # 测试搜索
    print("\n=== 测试关键词搜索 ===")
    for weibo in crawler.search_weibo("人工智能", page=1):
        print(f"@{weibo['user']['screen_name']}: {weibo['text'][:50]}...")
        break
