# 微博爬虫模块
"""
爬虫模块 - 支持微博、抖音、快手数据采集

主要组件:
- WeiboSpider: 微博爬虫（推荐使用）
- WeiboCrawler: 微博爬虫（备用）
- DouyinCrawler: 抖音爬虫
- KuaishouCrawler: 快手爬虫
"""

from .weibo_spider import WeiboSpider, CookiePool, UserAgentPool
from .weibo_spider import crawl_hot_search, crawl_keyword, crawl_user

__all__ = [
    'WeiboSpider',
    'CookiePool', 
    'UserAgentPool',
    'crawl_hot_search',
    'crawl_keyword',
    'crawl_user',
]
