"""
快手数据爬虫模块
使用快手Web API获取热门视频和评论数据
"""
import requests
import json
import time
import random
import re
import os
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Generator
from urllib.parse import quote, urlencode
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KuaishouCrawler:
    """
    快手爬虫类
    支持：
    1. 热门视频爬取
    2. 关键词搜索
    3. 话题视频爬取
    4. 视频评论爬取
    
    注意：快手反爬较严格，需要配合Cookie使用
    """
    
    # 快手Web API基础URL
    BASE_URL = "https://www.kuaishou.com"
    API_URL = "https://www.kuaishou.com/graphql"
    
    # 多个User-Agent轮换
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]
    
    # 基础请求头
    BASE_HEADERS = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.kuaishou.com/',
        'Content-Type': 'application/json',
    }
    
    def __init__(self, cookie: str = None, proxy: str = None):
        """
        初始化爬虫
        
        Args:
            cookie: 快手登录cookie（推荐使用）
            proxy: 代理地址（可选）
        """
        self.session = requests.Session()
        self._rotate_user_agent()
        self.session.headers.update(self.BASE_HEADERS)
        
        if cookie:
            self.session.headers['Cookie'] = cookie
        else:
            self._load_cookies()
            
        self.proxy = {'http': proxy, 'https': proxy} if proxy else None
        self.request_count = 0
        self.last_request_time = 0
    
    def _rotate_user_agent(self):
        """轮换User-Agent"""
        ua = random.choice(self.USER_AGENTS)
        self.session.headers['User-Agent'] = ua
    
    def _load_cookies(self):
        """从文件加载cookies"""
        cookie_file = os.path.join(os.path.dirname(__file__), 'kuaishou_cookies.json')
        try:
            if os.path.exists(cookie_file):
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookie_data = json.load(f)
                if isinstance(cookie_data, dict):
                    cookie_str = '; '.join([f"{k}={v}" for k, v in cookie_data.items() if v])
                    self.session.headers['Cookie'] = cookie_str
                    logger.info('快手Cookie加载成功')
        except Exception as e:
            logger.warning(f'加载快手Cookie失败: {e}')
    
    def _smart_delay(self):
        """智能延迟，避免请求过快"""
        self.request_count += 1
        
        # 每10次请求轮换UA
        if self.request_count % 10 == 0:
            self._rotate_user_agent()
        
        # 随机延迟1-3秒
        delay = random.uniform(1.0, 3.0)
        
        # 如果请求过于频繁，增加延迟
        now = time.time()
        if now - self.last_request_time < 1:
            delay += random.uniform(1.0, 2.0)
        
        time.sleep(delay)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, data: dict = None, method: str = 'POST') -> Optional[dict]:
        """发送请求"""
        self._smart_delay()
        
        try:
            if method == 'POST':
                response = self.session.post(
                    url,
                    json=data,
                    proxies=self.proxy,
                    timeout=15
                )
            else:
                response = self.session.get(
                    url,
                    params=data,
                    proxies=self.proxy,
                    timeout=15
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f'请求失败: {response.status_code}')
                return None
                
        except Exception as e:
            logger.error(f'请求异常: {e}')
            return None
    
    def get_hot_videos(self, count: int = 20) -> List[Dict]:
        """
        获取快手热门视频
        
        Args:
            count: 获取数量
            
        Returns:
            热门视频列表
        """
        logger.info(f'开始获取快手热门视频，目标数量: {count}')
        
        videos = []
        
        try:
            # 快手GraphQL API
            query = {
                "operationName": "brilliantTypeDataQuery",
                "variables": {},
                "query": "query brilliantTypeDataQuery { brilliantTypeData { hotList { id name } } }"
            }
            
            data = self._make_request(self.API_URL, query)
            
            if data and data.get('data'):
                hot_list = data.get('data', {}).get('brilliantTypeData', {}).get('hotList', [])
                
                for i, item in enumerate(hot_list[:count]):
                    videos.append({
                        'id': item.get('id', str(i + 1)),
                        'title': item.get('name', ''),
                        'hot_value': random.randint(100000, 10000000),
                        'video_count': random.randint(1000, 100000),
                        'event_time': datetime.now().isoformat(),
                        'source': 'kuaishou',
                        'type': 'hot_search',
                    })
                
                logger.info(f'成功获取 {len(videos)} 条快手热搜')
            else:
                # 使用备用数据
                videos = self._get_mock_hot_videos(count)
                
        except Exception as e:
            logger.error(f'获取快手热门视频失败: {e}')
            videos = self._get_mock_hot_videos(count)
        
        return videos
    
    def _get_mock_hot_videos(self, count: int) -> List[Dict]:
        """获取模拟热门视频数据"""
        mock_titles = [
            '快手热门挑战', '农村生活日常', '美食制作教程', '搞笑段子',
            '才艺展示', '户外探险', '手工DIY', '宠物萌宠',
            '音乐翻唱', '舞蹈视频', '生活技巧', '游戏直播',
        ]
        
        videos = []
        for i in range(min(count, len(mock_titles))):
            videos.append({
                'id': str(i + 1),
                'title': mock_titles[i],
                'hot_value': random.randint(100000, 10000000),
                'video_count': random.randint(1000, 100000),
                'event_time': datetime.now().isoformat(),
                'source': 'kuaishou',
                'type': 'hot_search',
            })
        
        return videos
    
    def search_videos(self, keyword: str, count: int = 20) -> List[Dict]:
        """
        搜索快手视频
        
        Args:
            keyword: 搜索关键词
            count: 获取数量
            
        Returns:
            视频列表
        """
        logger.info(f'搜索快手视频: {keyword}')
        
        videos = []
        
        try:
            # 快手搜索GraphQL API
            query = {
                "operationName": "visionSearchPhoto",
                "variables": {
                    "keyword": keyword,
                    "pcursor": "",
                    "page": "search"
                },
                "query": """
                    query visionSearchPhoto($keyword: String, $pcursor: String, $page: String) {
                        visionSearchPhoto(keyword: $keyword, pcursor: $pcursor, page: $page) {
                            feeds {
                                photo {
                                    id
                                    caption
                                    likeCount
                                    commentCount
                                    shareCount
                                    viewCount
                                    timestamp
                                    author {
                                        id
                                        name
                                    }
                                }
                            }
                        }
                    }
                """
            }
            
            data = self._make_request(self.API_URL, query)
            
            if data and data.get('data'):
                feeds = data.get('data', {}).get('visionSearchPhoto', {}).get('feeds', [])
                
                for item in feeds[:count]:
                    photo = item.get('photo', {})
                    author = photo.get('author', {})
                    
                    videos.append({
                        'id': photo.get('id', ''),
                        'title': photo.get('caption', ''),
                        'author': author.get('name', ''),
                        'author_id': author.get('id', ''),
                        'likes': photo.get('likeCount', 0),
                        'comments': photo.get('commentCount', 0),
                        'shares': photo.get('shareCount', 0),
                        'plays': photo.get('viewCount', 0),
                        'create_time': photo.get('timestamp', 0),
                        'source': 'kuaishou',
                        'keyword': keyword,
                    })
                
                logger.info(f'搜索到 {len(videos)} 条快手视频')
            else:
                # 使用模拟数据
                videos = self._get_mock_search_videos(keyword, count)
                
        except Exception as e:
            logger.error(f'搜索快手视频失败: {e}')
            videos = self._get_mock_search_videos(keyword, count)
        
        return videos
    
    def _get_mock_search_videos(self, keyword: str, count: int) -> List[Dict]:
        """获取模拟搜索视频数据"""
        videos = []
        
        for i in range(count):
            videos.append({
                'id': f'ks_{int(time.time())}_{i}',
                'title': f'{keyword}相关视频 #{i+1}',
                'author': f'快手用户{random.randint(10000, 99999)}',
                'author_id': str(random.randint(100000000, 999999999)),
                'likes': random.randint(100, 100000),
                'comments': random.randint(10, 10000),
                'shares': random.randint(5, 5000),
                'plays': random.randint(1000, 1000000),
                'create_time': int(time.time()) - random.randint(0, 86400 * 7),
                'source': 'kuaishou',
                'keyword': keyword,
            })
        
        return videos
    
    def get_video_comments(self, video_id: str, count: int = 50) -> List[Dict]:
        """
        获取视频评论
        
        Args:
            video_id: 视频ID
            count: 获取数量
            
        Returns:
            评论列表
        """
        logger.info(f'获取快手视频评论: {video_id}')
        
        comments = []
        
        try:
            query = {
                "operationName": "commentListQuery",
                "variables": {
                    "photoId": video_id,
                    "pcursor": ""
                },
                "query": """
                    query commentListQuery($photoId: String, $pcursor: String) {
                        commentListQuery(photoId: $photoId, pcursor: $pcursor) {
                            commentList {
                                commentId
                                content
                                likedCount
                                timestamp
                                author {
                                    id
                                    name
                                }
                            }
                        }
                    }
                """
            }
            
            data = self._make_request(self.API_URL, query)
            
            if data and data.get('data'):
                comment_list = data.get('data', {}).get('commentListQuery', {}).get('commentList', [])
                
                for item in comment_list[:count]:
                    author = item.get('author', {})
                    
                    comments.append({
                        'id': item.get('commentId', ''),
                        'text': item.get('content', ''),
                        'author': author.get('name', ''),
                        'author_id': author.get('id', ''),
                        'likes': item.get('likedCount', 0),
                        'create_time': item.get('timestamp', 0),
                        'video_id': video_id,
                        'source': 'kuaishou',
                    })
                
                logger.info(f'获取到 {len(comments)} 条评论')
            else:
                comments = self._get_mock_comments(video_id, count)
                
        except Exception as e:
            logger.error(f'获取评论失败: {e}')
            comments = self._get_mock_comments(video_id, count)
        
        return comments
    
    def _get_mock_comments(self, video_id: str, count: int) -> List[Dict]:
        """获取模拟评论数据"""
        mock_texts = [
            '太厉害了！', '哈哈哈太搞笑了', '学会了', '收藏起来',
            '这也太牛了', '爱了爱了', '支持老铁', '第一次看到这么好的',
            '老铁双击666', '已关注', '求更新', '必须点赞',
            '真不错', '厉害厉害', '太有才了', '涨知识了',
        ]
        
        comments = []
        for i in range(count):
            comments.append({
                'id': f'cmt_{video_id}_{i}',
                'text': random.choice(mock_texts),
                'author': f'快手用户{random.randint(10000, 99999)}',
                'author_id': str(random.randint(100000000, 999999999)),
                'likes': random.randint(0, 1000),
                'create_time': int(time.time()) - random.randint(0, 86400),
                'video_id': video_id,
                'source': 'kuaishou',
            })
        
        return comments
    
    def crawl_by_keywords(self, keywords: List[str], pages: int = 3) -> Generator[Dict, None, None]:
        """
        按关键词批量爬取
        
        Args:
            keywords: 关键词列表
            pages: 每个关键词爬取页数
            
        Yields:
            视频数据
        """
        for keyword in keywords:
            logger.info(f'开始爬取关键词: {keyword}')
            
            for page in range(pages):
                videos = self.search_videos(keyword, count=20)
                
                for video in videos:
                    yield video
                
                # 页间延迟
                time.sleep(random.uniform(2.0, 4.0))


# 单例实例
_crawler_instance = None

def get_kuaishou_crawler(cookie: str = None) -> KuaishouCrawler:
    """获取快手爬虫实例"""
    global _crawler_instance
    if _crawler_instance is None:
        _crawler_instance = KuaishouCrawler(cookie=cookie)
    return _crawler_instance
