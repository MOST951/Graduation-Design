"""
JWT Authentication Middleware for Flask
Validates JWT tokens issued by either Flask or Spring Boot backend.
"""
import functools
import logging
from flask import request, jsonify, g

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency
_jwt = None
_config = None


def _get_jwt():
    global _jwt
    if _jwt is None:
        try:
            import jwt as pyjwt
            _jwt = pyjwt
        except ImportError:
            logger.warning("PyJWT not installed, JWT auth will be disabled")
            _jwt = False
    return _jwt


def _get_config():
    global _config
    if _config is None:
        try:
            from config import config
            _config = config
        except Exception:
            _config = False
    return _config


def token_required(f):
    """
    Decorator that requires a valid JWT token in the Authorization header.
    Sets g.current_user with the decoded token payload if valid.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        jwt_lib = _get_jwt()
        cfg = _get_config()

        # If PyJWT not available, skip auth (dev mode)
        if not jwt_lib or not cfg:
            g.current_user = {'username': 'anonymous', 'role': 'user'}
            return f(*args, **kwargs)

        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        if not token:
            return jsonify({
                'code': 401,
                'message': '缺少认证令牌，请先登录'
            }), 401

        # Try multiple secrets (Flask and Java backend may use different keys)
        secrets = []
        if hasattr(cfg, 'security') and hasattr(cfg.security, 'jwt_secret_key'):
            secrets.append(cfg.security.jwt_secret_key)
        if hasattr(cfg, 'flask') and hasattr(cfg.flask, 'secret_key'):
            secrets.append(cfg.flask.secret_key)

        # Also try env vars
        import os
        env_secret = os.getenv('JWT_SECRET_KEY') or os.getenv('JWT_SECRET')
        if env_secret and env_secret not in secrets:
            secrets.append(env_secret)

        if not secrets:
            secrets = ['dev-secret-key-change-in-production']

        last_error = None
        for secret in secrets:
            try:
                payload = jwt_lib.decode(
                    token,
                    secret,
                    algorithms=['HS256', 'HS384', 'HS512'],
                    options={"verify_exp": True}
                )
                g.current_user = payload
                return f(*args, **kwargs)
            except jwt_lib.ExpiredSignatureError:
                return jsonify({
                    'code': 401,
                    'message': '令牌已过期，请重新登录'
                }), 401
            except jwt_lib.InvalidTokenError as e:
                last_error = e
                continue

        logger.warning(f"JWT validation failed: {last_error}")
        return jsonify({
            'code': 401,
            'message': '无效的认证令牌'
        }), 401

    return decorated


def optional_token(f):
    """
    Decorator that optionally parses JWT token but does not require it.
    Sets g.current_user to None if no valid token present.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        jwt_lib = _get_jwt()
        cfg = _get_config()
        g.current_user = None

        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer ') and jwt_lib and cfg:
            token = auth_header[7:]
            secrets = []
            if hasattr(cfg, 'security') and hasattr(cfg.security, 'jwt_secret_key'):
                secrets.append(cfg.security.jwt_secret_key)
            import os
            env_secret = os.getenv('JWT_SECRET_KEY') or os.getenv('JWT_SECRET')
            if env_secret:
                secrets.append(env_secret)
            for secret in secrets:
                try:
                    g.current_user = jwt_lib.decode(
                        token, secret,
                        algorithms=['HS256', 'HS384', 'HS512'],
                        options={"verify_exp": True}
                    )
                    break
                except Exception:
                    continue

        return f(*args, **kwargs)
    return decorated
