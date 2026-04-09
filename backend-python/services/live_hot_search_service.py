"""
微博实时热搜服务
================

直接从微博API实时获取热搜数据，并进行情感分析

功能特性：
1. 实时爬取微博热搜榜
2. 自动采集热搜话题相关微博
3. 实时情感分析
4. 定时自动刷新
5. 热搜变化检测
"""

import os
import re
import json
import time
import logging
import threading
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from collections import deque
from urllib.parse import quote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('LiveHotSearchService')


@dataclass
class LiveHotSearchConfig:
    refresh_interval: int = 60
    weibos_per_topic: int = 20
    top_n_topics: int = 10
    history_size: int = 100
    request_timeout: int = 15


@dataclass 
class HotSearchItem:
    rank: int
    title: str
    hot_value: int
    category: str = ""
    label: str = ""
    is_hot: bool = False
    is_new: bool = False
    is_fei: bool = False
    url: str = ""
    sentiment: str = "neutral"
    sentiment_score: float = 0.0
    positive_ratio: float = 0.0
    negative_ratio: float = 0.0
    weibo_count: int = 0
    sample_weibos: List[Dict] = field(default_factory=list)
    crawl_time: str = ""
    trend: str = "stable"


class WeiboHotSearchCrawler:
    WEB_API = "https://weibo.com"
    MOBILE_API = "https://m.weibo.cn"
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    ]
    
    def __init__(self, config: LiveHotSearchConfig = None):
        self.config = config or LiveHotSearchConfig()
        self.session = requests.Session()
        self.last_request_time = 0
    
    def _get_random_ua(self) -> str:
        import random
        return random.choice(self.USER_AGENTS)
    
    def _delay(self, min_sec: float = 0.5, max_sec: float = 1.5):
        import random
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(min_sec, max_sec)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self.last_request_time = time.time()
    
    def fetch_hot_search(self) -> List[Dict]:
        hot_list = self._fetch_hot_search_ajax()
        if hot_list:
            return hot_list
        hot_list = self._fetch_hot_search_mobile()
        return hot_list or []
    
    def _fetch_hot_search_ajax(self) -> List[Dict]:
        url = f"{self.WEB_API}/ajax/side/hotSearch"
        headers = {
            'User-Agent': self._get_random_ua(),
            'Accept': 'application/json',
            'Referer': 'https://weibo.com/',
        }
        
        try:
            self._delay()
            response = self.session.get(url, headers=headers, timeout=self.config.request_timeout)
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
            
            logger.info(f"获取到 {len(hot_list)} 条热搜")
            return hot_list
        except Exception as e:
            logger.error(f"Ajax API失败: {e}")
            return []
    
    def _fetch_hot_search_mobile(self) -> List[Dict]:
        url = f"{self.MOBILE_API}/api/container/getIndex"
        params = {'containerid': '106003type=25&t=3&disable_hot=1&filter_type=realtimehot'}
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
            'Accept': 'application/json',
            'Referer': 'https://m.weibo.cn/',
        }
        
        try:
            self._delay()
            response = self.session.get(url, params=params, headers=headers, timeout=self.config.request_timeout)
            if response.status_code != 200:
                return []
            
            data = response.json()
            if data.get('ok') != 1:
                return []
            
            hot_list = []
            cards = data.get('data', {}).get('cards', [])
            for card in cards:
                for item in card.get('card_group', []):
                    if item.get('card_type') == 4:
                        hot_list.append({
                            'rank': len(hot_list) + 1,
                            'title': item.get('desc', ''),
                            'hot_value': 0,
                            'crawl_time': datetime.now().isoformat(),
                        })
            return hot_list
        except Exception as e:
            logger.error(f"移动端API失败: {e}")
            return []
    
    def fetch_topic_weibos(self, keyword: str, limit: int = 20) -> List[Dict]:
        encoded_keyword = quote(keyword, safe='')
        url = f"{self.MOBILE_API}/api/container/getIndex"
        params = {
            'containerid': f'100103type=1&q={encoded_keyword}',
            'page_type': 'searchall',
            'page': 1
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
            'Accept': 'application/json',
            'Referer': 'https://m.weibo.cn/',
        }
        
        try:
            self._delay(0.8, 1.5)
            response = self.session.get(url, params=params, headers=headers, timeout=self.config.request_timeout)
            if response.status_code != 200:
                return []
            
            data = response.json()
            if data.get('ok') != 1:
                return []
            
            weibos = []
            cards = data.get('data', {}).get('cards', [])
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
            
            return weibos[:limit]
        except Exception as e:
            logger.error(f"搜索微博失败: {e}")
            return []
    
    def _parse_weibo(self, mblog: Dict, keyword: str = '') -> Dict:
        user = mblog.get('user', {})
        text = re.sub(r'<[^>]+>', '', mblog.get('text', '')).strip()
        
        return {
            'id': str(mblog.get('id', '')),
            'text': text,
            'user_id': str(user.get('id', '')),
            'user_name': user.get('screen_name', ''),
            'created_at': mblog.get('created_at', ''),
            'reposts_count': mblog.get('reposts_count', 0),
            'comments_count': mblog.get('comments_count', 0),
            'likes_count': mblog.get('attitudes_count', 0),
            'keyword': keyword,
            'crawl_time': datetime.now().isoformat(),
        }


class SimpleSentimentAnalyzer:
    POSITIVE = {'好', '棒', '赞', '喜欢', '爱', '开心', '高兴', '快乐', '幸福', '精彩', '厉害', '牛', '强', '美', '感动', '支持', '期待', '成功', '加油', '满意', '感谢', '祝福', '恭喜', '推荐', '完美', '哈哈', 'yyds', '绝绝子', '太可了', '666'}
    NEGATIVE = {'差', '烂', '垃圾', '讨厌', '恨', '愤怒', '生气', '难过', '伤心', '失望', '糟糕', '恶心', '无语', '崩溃', '绝望', '痛苦', '悲伤', '害怕', '担心', '失败', '骗', '坑', '呵呵', '滚', '傻', '破防', '裂开', '麻了', 'emo'}
    NEGATION = {'不', '没', '没有', '无', '别', '未'}
    DEGREE = {'很': 1.5, '非常': 2.0, '特别': 2.0, '超级': 2.0, '太': 1.8, '真': 1.5}
    
    def analyze(self, text: str) -> Dict:
        if not text:
            return {'sentiment': 'neutral', 'score': 0.0, 'confidence': 0.5}
        
        text = text.lower()
        has_neg = any(n in text for n in self.NEGATION)
        degree = max((d for w, d in self.DEGREE.items() if w in text), default=1.0)
        
        pos = sum(1 for w in self.POSITIVE if w in text) * degree
        neg = sum(1 for w in self.NEGATIVE if w in text) * degree
        
        if has_neg:
            pos, neg = neg * 0.8, pos * 0.8
        
        total = pos + neg
        if total == 0:
            return {'sentiment': 'neutral', 'score': 0.0, 'confidence': 0.5}
        
        score = (pos - neg) / max(total, 1)
        score = max(-1.0, min(1.0, score))
        
        if score > 0.2:
            sentiment = 'positive'
        elif score < -0.2:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {'sentiment': sentiment, 'score': round(score, 4), 'confidence': round(0.5 + abs(score) * 0.4, 4)}
    
    def analyze_batch(self, texts: List[str]) -> Dict:
        results = [self.analyze(t) for t in texts]
        if not results:
            return {'sentiment': 'neutral', 'score': 0.0, 'positive_ratio': 0.0, 'negative_ratio': 0.0}
        
        pos = sum(1 for r in results if r['sentiment'] == 'positive')
        neg = sum(1 for r in results if r['sentiment'] == 'negative')
        total = len(results)
        avg_score = sum(r['score'] for r in results) / total
        
        if pos > neg * 1.5:
            sentiment = 'positive'
        elif neg > pos * 1.5:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {
            'sentiment': sentiment,
            'score': round(avg_score, 4),
            'positive_ratio': round(pos / total * 100, 2),
            'negative_ratio': round(neg / total * 100, 2),
        }


class LiveHotSearchService:
    def __init__(self, config: LiveHotSearchConfig = None):
        self.config = config or LiveHotSearchConfig()
        self.crawler = WeiboHotSearchCrawler(self.config)
        self.sentiment = SimpleSentimentAnalyzer()
        
        self.current_hot_list: List[HotSearchItem] = []
        self.history: deque = deque(maxlen=self.config.history_size)
        self.previous_titles: set = set()
        
        self.callbacks: List[Callable] = []
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        
        self.stats = {
            'total_refreshes': 0,
            'last_refresh': None,
            'total_weibos_collected': 0,
        }
    
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()
        logger.info(f"实时热搜服务已启动 (刷新间隔: {self.config.refresh_interval}秒)")
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("实时热搜服务已停止")
    
    def add_callback(self, callback: Callable):
        self.callbacks.append(callback)
    
    def _refresh_loop(self):
        while self._running:
            try:
                self.refresh()
            except Exception as e:
                logger.error(f"刷新失败: {e}")
            time.sleep(self.config.refresh_interval)
    
    def refresh(self):
        logger.info("开始刷新热搜...")
        
        raw_list = self.crawler.fetch_hot_search()
        if not raw_list:
            logger.warning("未获取到热搜数据")
            return
        
        hot_items = []
        current_titles = set()
        
        for raw in raw_list[:50]:
            title = raw.get('title', '')
            if not title:
                continue
            
            current_titles.add(title)
            
            trend = 'stable'
            if title not in self.previous_titles:
                trend = 'new'
            
            item = HotSearchItem(
                rank=raw.get('rank', 0),
                title=title,
                hot_value=raw.get('hot_value', 0),
                category=raw.get('category', ''),
                label=raw.get('label', ''),
                is_hot=raw.get('is_hot', False),
                is_new=raw.get('is_new', False),
                is_fei=raw.get('is_fei', False),
                url=raw.get('url', ''),
                crawl_time=raw.get('crawl_time', datetime.now().isoformat()),
                trend=trend,
            )
            hot_items.append(item)
        
        for i, item in enumerate(hot_items[:self.config.top_n_topics]):
            try:
                weibos = self.crawler.fetch_topic_weibos(item.title, self.config.weibos_per_topic)
                if weibos:
                    item.weibo_count = len(weibos)
                    item.sample_weibos = weibos[:5]
                    self.stats['total_weibos_collected'] += len(weibos)
                    
                    texts = [w.get('text', '') for w in weibos]
                    sentiment_result = self.sentiment.analyze_batch(texts)
                    item.sentiment = sentiment_result['sentiment']
                    item.sentiment_score = sentiment_result['score']
                    item.positive_ratio = sentiment_result['positive_ratio']
                    item.negative_ratio = sentiment_result['negative_ratio']
            except Exception as e:
                logger.error(f"采集热搜微博失败 [{item.title}]: {e}")
        
        with self._lock:
            self.current_hot_list = hot_items
            self.previous_titles = current_titles
            self.history.append({
                'timestamp': datetime.now().isoformat(),
                'hot_list': [asdict(h) for h in hot_items[:20]],
            })
        
        self.stats['total_refreshes'] += 1
        self.stats['last_refresh'] = datetime.now().isoformat()
        
        new_topics = [h.title for h in hot_items if h.trend == 'new']
        if new_topics:
            for cb in self.callbacks:
                try:
                    cb('new_hot', new_topics, hot_items)
                except Exception as e:
                    logger.error(f"回调失败: {e}")
        
        logger.info(f"热搜刷新完成: {len(hot_items)} 条, 新热搜: {len(new_topics)} 条")
    
    def get_hot_search(self) -> List[Dict]:
        with self._lock:
            return [asdict(h) for h in self.current_hot_list]
    
    def get_hot_search_with_sentiment(self) -> Dict:
        with self._lock:
            hot_list = [asdict(h) for h in self.current_hot_list]
        
        if not hot_list:
            return {'hot_list': [], 'summary': {}, 'last_refresh': None}
        
        pos = sum(1 for h in hot_list if h.get('sentiment') == 'positive')
        neg = sum(1 for h in hot_list if h.get('sentiment') == 'negative')
        total = len(hot_list)
        
        return {
            'hot_list': hot_list,
            'summary': {
                'total': total,
                'positive_count': pos,
                'negative_count': neg,
                'neutral_count': total - pos - neg,
                'positive_ratio': round(pos / total * 100, 2) if total else 0,
                'negative_ratio': round(neg / total * 100, 2) if total else 0,
            },
            'last_refresh': self.stats['last_refresh'],
        }
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        with self._lock:
            return list(self.history)[-limit:]
    
    def get_stats(self) -> Dict:
        return {
            **self.stats,
            'current_count': len(self.current_hot_list),
            'running': self._running,
        }
    
    def force_refresh(self) -> List[Dict]:
        self.refresh()
        return self.get_hot_search()


_service_instance: LiveHotSearchService = None

def get_live_hot_search_service() -> LiveHotSearchService:
    global _service_instance
    if _service_instance is None:
        _service_instance = LiveHotSearchService()
    return _service_instance

def start_live_hot_search(config: LiveHotSearchConfig = None) -> LiveHotSearchService:
    service = get_live_hot_search_service()
    if config:
        service.config = config
    service.start()
    return service

def stop_live_hot_search():
    global _service_instance
    if _service_instance:
        _service_instance.stop()


if __name__ == '__main__':
    print("=" * 60)
    print("微博实时热搜服务测试")
    print("=" * 60)
    
    service = LiveHotSearchService(LiveHotSearchConfig(refresh_interval=120))
    
    def on_new_hot(event, new_topics, hot_list):
        print(f"\n[新热搜] {', '.join(new_topics[:5])}")
    
    service.add_callback(on_new_hot)
    
    print("\n首次获取热搜...")
    service.refresh()
    
    hot_data = service.get_hot_search_with_sentiment()
    print(f"\n获取到 {hot_data['summary']['total']} 条热搜")
    print(f"情感分布: 正面{hot_data['summary']['positive_ratio']}% / 负面{hot_data['summary']['negative_ratio']}%")
    
    print("\n热搜TOP10:")
    for h in hot_data['hot_list'][:10]:
        sentiment_icon = {'positive': '😊', 'negative': '😢', 'neutral': '😐'}.get(h['sentiment'], '😐')
        print(f"  {h['rank']}. {h['title']} ({h['hot_value']}) {sentiment_icon} [{h['sentiment']}]")
        if h.get('sample_weibos'):
            print(f"     样本: {h['sample_weibos'][0].get('text', '')[:50]}...")
    
    print("\n启动自动刷新服务...")
    service.start()
    
    try:
        while True:
            time.sleep(30)
            stats = service.get_stats()
            print(f"[状态] 刷新次数: {stats['total_refreshes']} | 采集微博: {stats['total_weibos_collected']}")
    except KeyboardInterrupt:
        print("\n停止服务...")
        service.stop()
