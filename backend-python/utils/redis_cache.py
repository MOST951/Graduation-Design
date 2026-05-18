"""
内存缓存装饰器 - 论文 4.3.1 "暂存热点数据" 落地

用法:
    from utils.redis_cache import redis_cache

    @dashboard_bp.route('/overview')
    @redis_cache('dashboard:overview', ttl=60)
    def get_overview():
        return jsonify({...})

特性:
- 使用进程内 MemoryCache（无需外部 Redis 依赖）
- 仅缓存 jsonify 返回的 (response, status) 或 response 对象的 body
- key 支持函数计算 (key=lambda req: ...)
"""
from __future__ import annotations
import logging
import threading
import time
import json
from functools import wraps
from typing import Callable, Dict, Any, Optional

from flask import request

logger = logging.getLogger(__name__)

# --------------- 轻量进程内缓存 ---------------

_cache_store: Dict[str, str] = {}
_cache_expire: Dict[str, float] = {}
_cache_lock = threading.Lock()


def _cache_get(key: str) -> Optional[str]:
    with _cache_lock:
        if key in _cache_expire and time.time() > _cache_expire[key]:
            _cache_store.pop(key, None)
            _cache_expire.pop(key, None)
            return None
        return _cache_store.get(key)


def _cache_set(key: str, value: str, ttl: int):
    with _cache_lock:
        _cache_store[key] = value
        _cache_expire[key] = time.time() + ttl
        # 简单 LRU：超过 2048 键时清理过期
        if len(_cache_store) > 2048:
            now = time.time()
            expired = [k for k, v in _cache_expire.items() if now > v]
            for k in expired:
                _cache_store.pop(k, None)
                _cache_expire.pop(k, None)


# --------------- 公共装饰器 ---------------

def redis_cache(key_prefix: str, ttl: int = 60,
                key_fn: Optional[Callable] = None):
    """
    将 view 函数返回值缓存到进程内存

    :param key_prefix: 缓存 key 前缀, 例如 'dashboard:overview'
    :param ttl:        过期秒数
    :param key_fn:     可选的 key 计算函数 (req)->str, 默认拼接 query string
    """
    def decorator(view_fn):
        @wraps(view_fn)
        def wrapper(*args, **kwargs):
            # 组装 cache key
            try:
                if key_fn is not None:
                    suffix = key_fn(request)
                else:
                    qs = request.query_string.decode('utf-8') if request.query_string else ''
                    suffix = qs or '_'
                cache_key = f"{key_prefix}:{suffix}"
            except Exception:
                cache_key = key_prefix

            # 命中缓存
            cached = _cache_get(cache_key)
            if cached is not None:
                from flask import Response
                resp = Response(cached, mimetype='application/json')
                resp.headers['X-Cache'] = 'HIT'
                resp.headers['X-Cache-Key'] = cache_key
                return resp

            # 未命中, 调原函数
            result = view_fn(*args, **kwargs)

            # 写缓存 (仅对 200 的 jsonify 结果)
            try:
                resp = result[0] if isinstance(result, tuple) else result
                status = result[1] if isinstance(result, tuple) and len(result) > 1 else 200
                if status == 200 and hasattr(resp, 'get_data'):
                    body = resp.get_data(as_text=True)
                    _cache_set(cache_key, body, ttl)
                    if hasattr(resp, 'headers'):
                        resp.headers['X-Cache'] = 'MISS'
                        resp.headers['X-Cache-Key'] = cache_key
            except Exception as e:
                logger.debug(f"cache SET 失败: {e}")

            return result

        return wrapper
    return decorator
