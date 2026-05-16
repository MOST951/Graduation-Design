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
            # 即使传了cookie参数，也从cookies.json加载UA保持会话指纹一致
            self._load_ua_from_cookie_file()
        else:
            # 尝试从文件加载cookie
            self._load_cookies()
            
        self.proxy = {'http': proxy, 'https': proxy} if proxy else None
        self.request_count = 0
        self.last_request_time = 0
        self._driver = None  # Selenium driver，懒加载
    
    def _rotate_user_agent(self):
        """轮换User-Agent"""
        ua = random.choice(self.USER_AGENTS)
        self.session.headers['User-Agent'] = ua
        # 根据UA设置对应的Referer
        if 'iPhone' in ua or 'iPad' in ua or 'Android' in ua:
            self.session.headers['Referer'] = 'https://m.weibo.cn/'
        else:
            self.session.headers['Referer'] = 'https://weibo.com/'
    
    def _load_ua_from_cookie_file(self):
        """仅从cookies.json加载UA信息，保持会话指纹一致"""
        cookie_file = os.path.join(os.path.dirname(__file__), 'cookies.json')
        try:
            if os.path.exists(cookie_file):
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookie_data = json.load(f)
                candidates = [cookie_data] if isinstance(cookie_data, dict) else (cookie_data or [])
                for cookie_dict in candidates:
                    if not isinstance(cookie_dict, dict):
                        continue
                    ua = cookie_dict.get('_user_agent')
                    if ua:
                        self.session.headers['User-Agent'] = ua
                        logger.info(f"从cookies.json同步UA: {ua[:50]}")
                    return
        except Exception:
            pass

    def _load_cookies(self):
        """从文件加载cookies"""
        cookie_file = os.path.join(os.path.dirname(__file__), 'cookies.json')
        try:
            if os.path.exists(cookie_file):
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookie_data = json.load(f)
                    
                    # 支持两种格式：字典或列表
                    candidates = [cookie_data] if isinstance(cookie_data, dict) else (cookie_data or [])
                    for cookie_dict in candidates:
                        if not isinstance(cookie_dict, dict) or not cookie_dict.get('SUB'):
                            continue
                        cookie_str = '; '.join([f"{k}={v}" for k, v in cookie_dict.items() if v and not k.startswith('_')])
                        if not cookie_str:
                            continue
                        self.session.headers['Cookie'] = cookie_str
                        # 同步 _user_agent / _referer 等浏览器取证头，保证与导出 cookie 处于同一会话指纹
                        ua = cookie_dict.get('_user_agent')
                        if ua:
                            self.session.headers['User-Agent'] = ua
                        ref = cookie_dict.get('_referer')
                        if ref:
                            self.session.headers['Referer'] = ref
                        logger.info(f"已加载Cookie (SUB: {cookie_dict.get('SUB','')[:20]}..., UA: {(ua or '')[:50]})")
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
        优先使用 weibo.com/ajax API（无需Cookie），备用移动端API
        
        Returns:
            热搜列表，每项包含：rank, title, hot_value, category
        """
        # 方法1: weibo.com/ajax/side/hotSearch（无需Cookie，最可靠）
        try:
            headers = {
                'User-Agent': self.session.headers.get('User-Agent',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
                'Accept': 'application/json',
                'Referer': 'https://weibo.com/',
            }
            resp = requests.get('https://weibo.com/ajax/side/hotSearch',
                                headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('ok') == 1:
                    realtime = data.get('data', {}).get('realtime', [])
                    if realtime:
                        hot_list = []
                        for i, item in enumerate(realtime):
                            hot_list.append({
                                'rank': i + 1,
                                'title': item.get('word', ''),
                                'hot_value': item.get('num', 0),
                                'category': item.get('label_name', ''),
                                'url': f"https://s.weibo.com/weibo?q=%23{quote(item.get('word', ''))}%23",
                                'crawl_time': datetime.now().isoformat()
                            })
                        logger.info(f"ajax/side/hotSearch 获取 {len(hot_list)} 条热搜")
                        return hot_list[:50]
        except Exception as e:
            logger.warning(f"ajax/side/hotSearch 失败: {e}")

        # 方法2: 移动端API
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
    
    def _init_selenium(self) -> bool:
        """懒加载 Selenium 浏览器并注入 Cookie"""
        if self._driver is not None:
            return True
        try:
            from crawler.cookie_grabber import get_selenium_driver, load_cookies
            from selenium.webdriver.common.by import By

            logger.info("[Selenium] 创建 headless 浏览器...")
            self._driver = get_selenium_driver()
            self._driver.set_window_size(1920, 1080)

            # 先访问 weibo.com 域名，才能 set cookie
            self._driver.get('https://weibo.com/')
            time.sleep(2)

            # 注入 cookies.json 中的 Cookie
            cookie_data = load_cookies()
            injected = 0
            for name, value in cookie_data.items():
                if name.startswith('_'):
                    continue
                try:
                    self._driver.add_cookie({
                        'name': name, 'value': value,
                        'domain': '.weibo.com', 'path': '/'
                    })
                    injected += 1
                except Exception:
                    pass

            # 刷新页面使 Cookie 生效
            self._driver.get('https://weibo.com/')
            time.sleep(2)

            # 检查是否登录成功（不在登录页）
            url = self._driver.current_url
            if 'passport' in url or 'login' in url:
                logger.warning("[Selenium] Cookie 注入后仍被重定向到登录页")
                self._close_driver()
                return False

            logger.info(f"[Selenium] 浏览器就绪，注入 {injected} 个 Cookie")
            return True
        except Exception as e:
            logger.error(f"[Selenium] 初始化失败: {e}")
            self._close_driver()
            return False

    def _search_weibo_selenium(self, keyword: str, page: int = 1) -> List[Dict]:
        """
        使用 Selenium 驱动浏览器搜索微博：
        第1页：在搜索框输入关键词→回车；后续页：直接跳转 URL。
        """
        if not self._init_selenium():
            return []

        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        try:
            if page == 1:
                # -------- 第 1 页：通过搜索框输入关键词 --------
                self._driver.get('https://weibo.com/')
                time.sleep(random.uniform(1.5, 2.5))

                search_ok = False
                search_selectors = [
                    'input.woo-input-main',
                    'input[placeholder*="\u641c\u7d22"]',
                    '.gn_search input',
                    'input[type="text"]',
                ]
                for sel in search_selectors:
                    try:
                        el = WebDriverWait(self._driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        if not el:
                            continue
                        # 先点击激活搜索框（新版微博需要）
                        try:
                            el.click()
                            time.sleep(0.3)
                        except Exception:
                            self._driver.execute_script(
                                "arguments[0].focus(); arguments[0].click();", el)
                            time.sleep(0.3)
                        el.clear()
                        for ch in keyword:
                            el.send_keys(ch)
                            time.sleep(random.uniform(0.05, 0.15))
                        time.sleep(random.uniform(0.3, 0.6))
                        el.send_keys(Keys.ENTER)
                        time.sleep(1)
                        # 微博搜索会在新标签页打开结果
                        handles = self._driver.window_handles
                        if len(handles) > 1:
                            self._driver.switch_to.window(handles[-1])
                            logger.info(f"[Selenium] 搜索结果在新标签页打开，已切换")
                        logger.info(f"[Selenium] 已在搜索框输入 [{keyword}] 并回车 ({sel})")
                        search_ok = True
                        break
                    except Exception as e:
                        logger.debug(f"[Selenium] \u9009\u62e9\u5668 {sel} \u5931\u8d25: {e}")
                        continue

                if not search_ok:
                    logger.info("[Selenium] \u641c\u7d22\u6846\u4ea4\u4e92\u5931\u8d25\uff0c\u901a\u8fc7\u6d4f\u89c8\u5668\u76f4\u63a5\u8bbf\u95ee\u641c\u7d22URL")
                    self._driver.get(f'https://s.weibo.com/weibo?q={quote(keyword)}')
            else:
                # -------- 第 2+ 页：直接跳转 --------
                url = f'https://s.weibo.com/weibo?q={quote(keyword)}&page={page}'
                self._driver.get(url)
                logger.info(f"[Selenium] \u76f4\u63a5\u8df3\u8f6c {url}")

            # 等待搜索结果加载
            time.sleep(random.uniform(2.5, 4.0))

            # 检查是否被重定向到登录页
            cur = self._driver.current_url
            if 'passport' in cur or 'login' in cur:
                logger.warning("[Selenium] \u641c\u7d22\u65f6\u88ab\u91cd\u5b9a\u5411\u5230\u767b\u5f55\u9875\uff0cCookie \u53ef\u80fd\u5df2\u5931\u6548")
                return []

            # 获取页面源码并复用现有解析器
            html = self._driver.page_source
            results = self._parse_search_html(html, keyword)
            logger.info(f"[Selenium] \u641c\u7d22 '{keyword}' page={page} \u89e3\u6790\u5f97\u5230 {len(results)} \u6761\u5fae\u535a")
            return results

        except Exception as e:
            logger.error(f"[Selenium] \u641c\u7d22\u5931\u8d25: {e}")
            return []

    def _close_driver(self):
        """关闭 Selenium 浏览器"""
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

    def close(self):
        """释放所有资源"""
        self._close_driver()

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
        # 方法1: Selenium 浏览器搜索（最真实，反爬风险最低）
        selenium_results = self._search_weibo_selenium(keyword, page)
        if selenium_results:
            for weibo in selenium_results:
                yield weibo
            return

        # 方法2: requests + Cookie 直接访问 s.weibo.com（回退）
        logger.info(f"[Selenium] 无结果，回退到 requests 方式")
        pc_results = list(self._search_weibo_pc(keyword, page))
        if pc_results:
            for weibo in pc_results:
                yield weibo
            return
        
        # 方法3: 移动端API（可能需要Cookie）
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

    def _search_weibo_ajax(self, keyword: str, page: int = 1) -> List[Dict]:
        """
        使用 weibo.com/ajax/statuses/searchPosts JSON API 搜索。
        需要 Cookie 中包含 SUB 和 XSRF-TOKEN。
        """
        cookie = self.session.headers.get('Cookie', '')
        if not cookie or 'SUB=' not in cookie:
            return []

        # 从 cookie 中提取 XSRF-TOKEN
        xsrf = ''
        for part in cookie.split(';'):
            part = part.strip()
            if part.startswith('XSRF-TOKEN='):
                xsrf = part.split('=', 1)[1]
                break

        headers = {
            'User-Agent': self.session.headers.get('User-Agent',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
            'Accept': 'application/json, text/plain, */*',
            'Referer': f'https://s.weibo.com/weibo?q={quote(keyword)}',
            'Cookie': cookie,
        }
        if xsrf:
            headers['X-XSRF-TOKEN'] = xsrf

        try:
            time.sleep(random.uniform(0.5, 1.5))
            resp = requests.get(
                'https://weibo.com/ajax/statuses/searchPosts',
                params={'q': keyword, 'page': page},
                headers=headers, timeout=15
            )
        except Exception as e:
            logger.warning(f"ajax searchPosts 请求失败: {e}")
            return []

        if resp.status_code != 200:
            logger.warning(f"ajax searchPosts 返回 {resp.status_code}")
            return []

        try:
            data = resp.json()
        except Exception:
            logger.warning("ajax searchPosts 响应非JSON")
            return []

        if data.get('ok') != 1:
            logger.info(f"ajax searchPosts ok={data.get('ok')}，Cookie 可能已失效")
            return []

        statuses = data.get('data', {}).get('statuses', [])
        if not statuses:
            return []

        results = []
        for mblog in statuses:
            results.append(self._parse_weibo(mblog, keyword))

        logger.info(f"ajax searchPosts '{keyword}' page={page} 获取 {len(results)} 条真实微博")
        return results

    def _search_weibo_pc(self, keyword: str, page: int = 1) -> List[Dict]:
        """
        使用 s.weibo.com PC 搜索结果页（HTML）解析真实微博。
        需要 cookie 中包含 SUB。
        """
        cookie = self.session.headers.get('Cookie', '')
        if not cookie or 'SUB=' not in cookie:
            return []

        url = f"https://s.weibo.com/weibo?q={quote(keyword)}&page={page}"
        # PC搜索必须使用桌面UA，移动端UA会导致s.weibo.com返回不同格式
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        stored_ua = self.session.headers.get('User-Agent', '')
        if 'Windows' in stored_ua or 'Macintosh' in stored_ua:
            ua = stored_ua
        headers = {
            'User-Agent': ua,
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

    @staticmethod
    def _normalize_weibo_time(raw: str) -> str:
        """
        把微博搜索页的中文时间转为 ISO 格式 YYYY-MM-DD HH:MM:SS
        支持：
          '05月14日 20:01'  -> '2026-05-14 20:01:00'
          '今天 18:30'      -> 当天
          '4分钟前'         -> 回推
          '1小时前'         -> 回推
          '昨天 09:00'      -> 昨天
          '2025-03-01'      -> 原样
        """
        now = datetime.now()
        if not raw:
            return now.strftime('%Y-%m-%d %H:%M:%S')

        raw = raw.strip()

        # "X分钟前"
        m = re.match(r'(\d+)\s*分钟前', raw)
        if m:
            return (now - timedelta(minutes=int(m.group(1)))).strftime('%Y-%m-%d %H:%M:%S')

        # "X小时前"
        m = re.match(r'(\d+)\s*小时前', raw)
        if m:
            return (now - timedelta(hours=int(m.group(1)))).strftime('%Y-%m-%d %H:%M:%S')

        # "X秒前"
        m = re.match(r'(\d+)\s*秒前', raw)
        if m:
            return (now - timedelta(seconds=int(m.group(1)))).strftime('%Y-%m-%d %H:%M:%S')

        # "今天 HH:MM"
        m = re.match(r'今天\s*(\d{1,2}):(\d{2})', raw)
        if m:
            return now.replace(hour=int(m.group(1)), minute=int(m.group(2)),
                               second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')

        # "昨天 HH:MM"
        m = re.match(r'昨天\s*(\d{1,2}):(\d{2})', raw)
        if m:
            d = now - timedelta(days=1)
            return d.replace(hour=int(m.group(1)), minute=int(m.group(2)),
                             second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')

        # "MM月DD日 HH:MM"  (当年)
        m = re.match(r'(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})', raw)
        if m:
            month, day, hour, minute = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            return datetime(now.year, month, day, hour, minute).strftime('%Y-%m-%d %H:%M:%S')

        # "YYYY-MM-DD HH:MM" 已经是标准格式
        m = re.match(r'(\d{4})-(\d{2})-(\d{2})', raw)
        if m:
            return raw if len(raw) >= 16 else raw + ' 00:00:00'

        # 兜底：返回当前时间
        return now.strftime('%Y-%m-%d %H:%M:%S')

    def _parse_search_html(self, html: str, keyword: str) -> List[Dict]:
        """从 s.weibo.com 搜索结果页 HTML 中正则抽取微博卡片"""
        # 每张微博一个 card-wrap, 带 mid
        # 属性顺序不固定：raw HTML 为 class="card-wrap" mid="..."
        # Selenium DOM 为 mid="..." class="card-wrap"
        # 故用宽松正则：匹配同时包含 card-wrap 和 mid 的 div
        card_pattern = re.compile(
            r'<div\b[^>]*?\bmid="(?P<mid>\d+)"[^>]*?\bclass="card-wrap"[^>]*>'
            r'(?P<body>.*?)'
            r'(?=<div\b[^>]*?\bclass="card-wrap"[^>]*>|<div\s+class="m-page"|\Z)',
            re.DOTALL
        )
        # 同时尝试另一种属性顺序（class 在 mid 前面）
        card_pattern_alt = re.compile(
            r'<div\b[^>]*?\bclass="card-wrap"[^>]*?\bmid="(?P<mid>\d+)"[^>]*>'
            r'(?P<body>.*?)'
            r'(?=<div\b[^>]*?\bclass="card-wrap"[^>]*>|<div\s+class="m-page"|\Z)',
            re.DOTALL
        )
        # 用户 a 标签 (class 顺序 / 属性顺序在不同卡片可能不同, 故先抓整体 tag 再分别取属性)
        re_user_tag = re.compile(r'<a\b(?P<attrs>[^>]*\bclass="name"[^>]*)>(?P<inner>[^<]+)</a>', re.DOTALL)
        re_attr_href = re.compile(r'\bhref="([^"]+)"')
        re_attr_nick = re.compile(r'\bnick-name="([^"]*)"')
        re_uid = re.compile(r'(?:weibo\.com|com)/(?:u/)?(\d{6,})')
        # 正文 (顺序: 优先 _full 隐藏完整段, 否则取常规)
        re_text_full = re.compile(r'<p[^>]*node-type="feed_list_content_full"[^>]*>(?P<txt>.*?)</p>', re.DOTALL)
        re_text_short = re.compile(r'<p[^>]*node-type="feed_list_content"[^>]*>(?P<txt>.*?)</p>', re.DOTALL)
        re_time = re.compile(r'<div\s+class="from">\s*<a[^>]*>([^<]+)</a>', re.DOTALL)
        re_act_li = re.compile(r'<li[^>]*>\s*<a[^>]*action-type="feed_list_(?:forward|comment|like)"[^>]*>(?P<inner>.*?)</a>', re.DOTALL)
        # 移除标签后取文本里的数字
        re_strip = re.compile(r'<[^>]+>')

        results = []
        # 尝试两种属性顺序，取匹配数多的那个
        matches_a = list(card_pattern.finditer(html))
        matches_b = list(card_pattern_alt.finditer(html))
        all_matches = matches_a if len(matches_a) >= len(matches_b) else matches_b
        # 去重（同一 mid 只保留首次）
        seen_mids = set()
        for m in all_matches:
            mid = m.group('mid')
            if mid in seen_mids:
                continue
            seen_mids.add(mid)
            body = m.group('body')

            # 用户: 抓 <a class="name" ...>nick</a> 整 tag 再分别取属性
            mu = re_user_tag.search(body)
            if not mu:
                continue
            attrs = mu.group('attrs')
            inner_nick = mu.group('inner').strip()
            href_m = re_attr_href.search(attrs)
            nick_m = re_attr_nick.search(attrs)
            href = href_m.group(1) if href_m else ''
            nick = (nick_m.group(1) if nick_m else inner_nick).strip()
            uid_m = re_uid.search(href)
            uid = uid_m.group(1) if uid_m else ''
            if href and not href.startswith('http'):
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
            raw_time = mtime.group(1).strip() if mtime else ''
            created_at = self._normalize_weibo_time(raw_time)

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
    
    def __init__(self, data_dir: str = None, cookie: str = None):
        """
        初始化任务管理器
        
        Args:
            data_dir: 数据存储目录
            cookie: 微博登录Cookie（可选，传递给爬虫实例）
        """
        self.crawler = WeiboCrawler(cookie=cookie)
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 
            'weibo_raw'
        )
        os.makedirs(self.data_dir, exist_ok=True)

    def close(self):
        """释放爬虫资源（Selenium 浏览器等）"""
        if self.crawler:
            self.crawler.close()
        
    def crawl_by_keywords(self, keywords: List[str], pages: int = 50, 
                          save: bool = True, progress_callback=None) -> List[Dict]:
        """
        按关键词批量爬取
        
        Args:
            keywords: 关键词列表
            pages: 每个关键词最大爬取页数 (不足则提前停止)
            save: 是否保存到文件
            progress_callback: 可选回调 fn(keyword, page, total_pages, partial_data_so_far)
                               每爬完 1 页触发, 用于上层 (API) 实时刷新 collected/partial_data
            
        Returns:
            所有爬取的微博数据
        """
        all_data = []
        
        for keyword in keywords:
            logger.info(f"开始爬取关键词: {keyword} (最多 {pages} 页)")
            keyword_data = []
            empty_count = 0
            
            for page in range(1, pages + 1):
                logger.info(f"  爬取第 {page}/{pages} 页")
                page_data = []
                for weibo in self.crawler.search_weibo(keyword, page):
                    page_data.append(weibo)
                
                if not page_data:
                    empty_count += 1
                    logger.info(f"  第 {page} 页无数据 (连续空页: {empty_count})")
                    if empty_count >= 2:
                        logger.info(f"  连续2页无数据，关键词 '{keyword}' 采集结束 (共 {page} 页)")
                        break
                else:
                    empty_count = 0
                    keyword_data.extend(page_data)

                # 每页结束实时回调 (含合成本批数据快照)
                if progress_callback:
                    try:
                        progress_callback(keyword, page, pages, all_data + keyword_data)
                    except Exception as cb_err:
                        logger.debug(f"progress_callback 抛错(忽略): {cb_err}")

                # 随机延迟
                time.sleep(random.uniform(2, 5))
            
            # 如果搜索API没有返回数据，记录Cookie问题并生成兜底数据
            if not keyword_data:
                cookie = self.crawler.session.headers.get('Cookie', '')
                if not cookie or 'SUB=' not in cookie:
                    logger.warning(f"关键词搜索需要有效的微博Cookie（必须包含SUB字段），当前Cookie无效，回退为合成数据: {keyword}")
                else:
                    logger.warning(f"Cookie中有SUB但搜索仍无数据（Cookie可能已过期），回退为合成数据: {keyword}")
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
    
    def crawl_hot_topics(self, top_n: int = 10, pages_per_topic: int = 50,
                         save: bool = True) -> List[Dict]:
        """
        爬取热门话题的微博
        
        Args:
            top_n: 爬取前N个热搜话题
            pages_per_topic: 每个话题最大爬取页数 (不足则提前停止)
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
            logger.info(f"开始爬取话题: {topic} (最多 {pages_per_topic} 页)")
            topic_data = []
            empty_count = 0
            
            for page in range(1, pages_per_topic + 1):
                logger.info(f"  爬取第 {page}/{pages_per_topic} 页")
                page_data = []
                for weibo in self.crawler.search_weibo(topic, page):
                    page_data.append(weibo)
                
                if not page_data:
                    empty_count += 1
                    if empty_count >= 2:
                        logger.info(f"  连续2页无数据，话题 '{topic}' 采集结束 (共 {page} 页)")
                        break
                else:
                    empty_count = 0
                    topic_data.extend(page_data)
                    
                time.sleep(random.uniform(2, 5))
            
            # 如果搜索API没有返回数据，记录原因并生成兜底数据
            if not topic_data:
                cookie = self.crawler.session.headers.get('Cookie', '')
                if not cookie or 'SUB=' not in cookie:
                    logger.warning(f"话题搜索需要有效Cookie（含SUB），回退为合成数据: {topic}")
                else:
                    logger.warning(f"Cookie有SUB但话题搜索无数据（可能已过期），回退为合成数据: {topic}")
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
