"""实时 Feed 后台爬虫
每 N 秒调微博 hottimeline 接口拉取最新微博, INSERT IGNORE 到 weibo_core_data,
为仪表盘"实时数据流"提供持续更新的真实数据源。

需要 /app/backend/crawler/cookies.json 包含有效 SUB/SUBP 等字段。
"""
import os
import json
import time
import threading
import logging
from datetime import datetime
import requests
import pymysql

from config import config

logger = logging.getLogger('RealtimeFeedCrawler')

_thread: threading.Thread = None
_stop_event = threading.Event()
_last_run = {'time': None, 'inserted': 0, 'fetched': 0, 'error': None}


def _load_cookie_str() -> str:
    """复用 crawler.cookie_grabber.load_cookies 兼容 list/dict 两种存储格式"""
    try:
        from crawler.cookie_grabber import load_cookies
        cookie_data = load_cookies() or {}
        if isinstance(cookie_data, dict) and cookie_data:
            return '; '.join([f"{k}={v}" for k, v in cookie_data.items() if v and not k.startswith('_')])
    except Exception as e:
        logger.warning(f'读取 cookie 失败: {e}')
    return ''


def _load_xsrf_token() -> str:
    """从 cookie 中提取 XSRF-TOKEN, 用于 X-XSRF-TOKEN 头.
    支持环境变量 WEIBO_XSRF_TOKEN 覆盖 (调试场景)."""
    env_tok = os.environ.get('WEIBO_XSRF_TOKEN')
    if env_tok:
        return env_tok
    try:
        from crawler.cookie_grabber import load_cookies
        cookie_data = load_cookies() or {}
        if isinstance(cookie_data, dict):
            return cookie_data.get('XSRF-TOKEN') or cookie_data.get('xsrf-token') or ''
    except Exception:
        pass
    return ''


def _parse_status(s: dict) -> dict:
    """微博 hottimeline status -> weibo_core_data row"""
    user = s.get('user') or {}
    pic_infos = s.get('pic_infos') or {}
    # 优先大图
    image_urls = []
    if isinstance(pic_infos, dict):
        for _, info in pic_infos.items():
            url = (info.get('large') or {}).get('url') or (info.get('original') or {}).get('url') or info.get('url')
            if url:
                image_urls.append(url)
    # 兼容 pic_ids + thumbnail_pic
    if not image_urls:
        thumb = s.get('thumbnail_pic')
        if thumb:
            image_urls.append(thumb.replace('thumbnail', 'large'))

    created_at_str = s.get('created_at') or ''
    try:
        # 'Sun May 11 02:34:56 +0800 2026' 格式
        created_at = datetime.strptime(created_at_str, '%a %b %d %H:%M:%S %z %Y').replace(tzinfo=None)
    except Exception:
        created_at = datetime.now()

    return {
        'weibo_id': int(s.get('id') or 0),
        'content': (s.get('text_raw') or s.get('text') or '')[:8000],
        'created_at': created_at,
        'user_id': int(user.get('idstr') or user.get('id') or 0),
        'user_name': (user.get('screen_name') or '')[:128],
        'verified': 1 if user.get('verified') else 0,
        'followers_count': int(user.get('followers_count') or 0),
        'reposts_count': int(s.get('reposts_count') or 0),
        'comments_count': int(s.get('comments_count') or 0),
        'attitudes_count': int(s.get('attitudes_count') or 0),
        'has_image': 1 if image_urls else 0,
        'has_video': 1 if s.get('page_info', {}).get('media_info') else 0,
        'image_urls': json.dumps(image_urls, ensure_ascii=False) if image_urls else None,
        'location': (s.get('region_name') or '').replace('发布于 ', '')[:128],
        'source': 'realtime_feed',
        'keyword': 'realtime_feed',
        'batch_id': 'realtime_feed',
    }


def _insert_batch(rows: list) -> int:
    if not rows:
        return 0
    inserted = 0
    conn = None
    try:
        conn = pymysql.connect(
            host=config.database.host,
            port=config.database.port,
            user=config.database.username,
            password=config.database.password,
            database=config.database.database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
        )
        sql = """
            INSERT IGNORE INTO weibo_core_data
            (weibo_id, content, created_at, user_id, user_name, verified,
             followers_count, reposts_count, comments_count, attitudes_count,
             has_image, has_video, image_urls, location, source, keyword, batch_id)
            VALUES
            (%(weibo_id)s, %(content)s, %(created_at)s, %(user_id)s, %(user_name)s, %(verified)s,
             %(followers_count)s, %(reposts_count)s, %(comments_count)s, %(attitudes_count)s,
             %(has_image)s, %(has_video)s, %(image_urls)s, %(location)s, %(source)s, %(keyword)s, %(batch_id)s)
        """
        with conn.cursor() as cur:
            for row in rows:
                if not row['weibo_id']:
                    continue
                try:
                    cur.execute(sql, row)
                    inserted += cur.rowcount
                except Exception as e:
                    logger.debug(f"insert skip {row['weibo_id']}: {e}")
        conn.commit()
    except Exception as e:
        logger.error(f'_insert_batch failed: {e}')
    finally:
        if conn:
            conn.close()
    return inserted


def _fetch_and_store():
    cookie_str = _load_cookie_str()
    if not cookie_str:
        _last_run['error'] = 'no cookie'
        return 0, 0
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Cookie': cookie_str,
        'Referer': 'https://weibo.com/',
    }
    xsrf = _load_xsrf_token()
    if xsrf:
        headers['X-XSRF-TOKEN'] = xsrf
        headers['x-requested-with'] = 'XMLHttpRequest'
    # group_id=102803 = 实时/热门 timeline
    url = ("https://weibo.com/ajax/feed/hottimeline"
           "?since_id=0&refresh=0&group_id=102803&containerid=102803"
           "&extparam=discover%7Cnew_feed&max_id=0&count=20")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            _last_run['error'] = f'http {resp.status_code}'
            return 0, 0
        statuses = (resp.json() or {}).get('statuses') or []
        rows = [_parse_status(s) for s in statuses if isinstance(s, dict)]
        inserted = _insert_batch(rows)
        _last_run['error'] = None
        return len(rows), inserted
    except Exception as e:
        _last_run['error'] = str(e)
        logger.warning(f'fetch failed: {e}')
        return 0, 0


def _loop(interval: int):
    logger.info(f'RealtimeFeedCrawler started, interval={interval}s')
    while not _stop_event.is_set():
        try:
            fetched, inserted = _fetch_and_store()
            _last_run['time'] = datetime.now().isoformat()
            _last_run['fetched'] = fetched
            _last_run['inserted'] = inserted
            if inserted > 0:
                logger.info(f'realtime feed: fetched={fetched} inserted={inserted}')
        except Exception as e:
            logger.error(f'loop iteration failed: {e}')
        _stop_event.wait(interval)


def start(interval: int = 30):
    """启动后台线程; 已启动则跳过"""
    global _thread
    if _thread and _thread.is_alive():
        return False
    _stop_event.clear()
    _thread = threading.Thread(target=_loop, args=(interval,), daemon=True, name='RealtimeFeedCrawler')
    _thread.start()
    return True


def stop():
    _stop_event.set()


def get_status() -> dict:
    return dict(_last_run, running=bool(_thread and _thread.is_alive()))
