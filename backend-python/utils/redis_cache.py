"""
Redis 缓存装饰器 - 论文 4.3.1 Redis "暂存热点数据" 落地

用法:
    from utils.redis_cache import redis_cache

    @dashboard_bp.route('/overview')
    @redis_cache('dashboard:overview', ttl=60)
    def get_overview():
        return jsonify({...})

特性:
- Redis 不可用时优雅降级 (直接调原函数)
- 仅缓存 jsonify 返回的 (response, status) 或 response 对象的 body
- key 支持函数计算 (key=lambda req: ...)
"""
from __future__ import annotations
import os
import json
import logging
from functools import wraps
from typing import Callable, Optional

from flask import request

logger = logging.getLogger(__name__)

_client = None
_init_tried = False


def get_redis_client():
    """懒加载单例 Redis 客户端"""
    global _client, _init_tried
    if _client is not None or _init_tried:
        return _client
    _init_tried = True
    try:
        import redis as _redis
        c = _redis.Redis(
            host=os.environ.get('REDIS_HOST', 'localhost'),
            port=int(os.environ.get('REDIS_PORT', '6379')),
            password=os.environ.get('REDIS_PASSWORD') or None,
            db=int(os.environ.get('REDIS_DB', '0')),
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        c.ping()
        _client = c
        logger.info("redis_cache: Redis 已连接, 热点数据缓存已启用")
    except Exception as e:
        logger.warning(f"redis_cache: Redis 不可用, 装饰器降级直透: {e}")
        _client = None
    return _client


def redis_cache(key_prefix: str, ttl: int = 60,
                key_fn: Optional[Callable] = None):
    """
    将 view 函数返回值缓存到 Redis

    :param key_prefix: 缓存 key 前缀, 例如 'dashboard:overview'
    :param ttl:        过期秒数
    :param key_fn:     可选的 key 计算函数 (req)->str, 默认拼接 query string
    """
    def decorator(view_fn):
        @wraps(view_fn)
        def wrapper(*args, **kwargs):
            cli = get_redis_client()
            if cli is None:
                return view_fn(*args, **kwargs)

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
            try:
                cached = cli.get(cache_key)
                if cached is not None:
                    from flask import Response
                    resp = Response(cached, mimetype='application/json')
                    resp.headers['X-Cache'] = 'HIT'
                    resp.headers['X-Cache-Key'] = cache_key
                    return resp
            except Exception as e:
                logger.debug(f"redis_cache GET 失败: {e}")

            # 未命中, 调原函数
            result = view_fn(*args, **kwargs)

            # 写缓存 (仅对 200 的 jsonify 结果)
            try:
                # result 可能是 Response, 也可能是 (Response, status) 元组
                resp = result[0] if isinstance(result, tuple) else result
                status = result[1] if isinstance(result, tuple) and len(result) > 1 else 200
                if status == 200 and hasattr(resp, 'get_data'):
                    body = resp.get_data(as_text=True)
                    cli.setex(cache_key, ttl, body)
                    if hasattr(resp, 'headers'):
                        resp.headers['X-Cache'] = 'MISS'
                        resp.headers['X-Cache-Key'] = cache_key
            except Exception as e:
                logger.debug(f"redis_cache SET 失败: {e}")

            return result

        return wrapper
    return decorator
