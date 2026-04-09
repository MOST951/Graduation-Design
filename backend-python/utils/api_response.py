"""
API响应工具模块
===============
提供统一的API响应格式和错误处理

用于答辩演示时提供友好的错误提示
"""

from flask import jsonify
from functools import wraps
import traceback
import logging

logger = logging.getLogger(__name__)


class APIResponse:
    """统一API响应类"""
    
    @staticmethod
    def success(data=None, message="操作成功", code=200):
        """成功响应"""
        response = {
            "code": code,
            "success": True,
            "message": message,
            "data": data
        }
        return jsonify(response), code
    
    @staticmethod
    def error(message="操作失败", code=500, details=None):
        """错误响应"""
        response = {
            "code": code,
            "success": False,
            "message": message,
            "data": None
        }
        if details:
            response["details"] = details
        return jsonify(response), code
    
    @staticmethod
    def bad_request(message="请求参数错误", details=None):
        """400 错误"""
        return APIResponse.error(message, 400, details)
    
    @staticmethod
    def not_found(message="资源不存在"):
        """404 错误"""
        return APIResponse.error(message, 404)
    
    @staticmethod
    def server_error(message="服务器内部错误", details=None):
        """500 错误"""
        return APIResponse.error(message, 500, details)


# 错误消息映射（用户友好）
ERROR_MESSAGES = {
    "ConnectionError": "网络连接失败，请检查网络设置",
    "TimeoutError": "请求超时，请稍后重试",
    "FileNotFoundError": "文件不存在，请检查路径",
    "PermissionError": "权限不足，请检查文件权限",
    "JSONDecodeError": "数据格式错误，请检查输入",
    "ValueError": "参数值无效，请检查输入",
    "KeyError": "缺少必要参数",
    "TypeError": "参数类型错误",
    "ImportError": "模块加载失败，请检查依赖",
    "RuntimeError": "运行时错误，请稍后重试",
}


def get_friendly_error_message(exception: Exception) -> str:
    """获取用户友好的错误消息"""
    error_type = type(exception).__name__
    
    # 检查是否有预定义的友好消息
    if error_type in ERROR_MESSAGES:
        return ERROR_MESSAGES[error_type]
    
    # 检查异常消息中的关键词
    error_str = str(exception).lower()
    
    if "connection" in error_str or "connect" in error_str:
        return "连接失败，请检查服务是否启动"
    elif "timeout" in error_str:
        return "操作超时，请稍后重试"
    elif "permission" in error_str or "denied" in error_str:
        return "权限不足，请检查权限设置"
    elif "not found" in error_str or "不存在" in error_str:
        return "请求的资源不存在"
    elif "invalid" in error_str or "无效" in error_str:
        return "输入参数无效，请检查后重试"
    elif "spark" in error_str:
        return "Spark服务异常，请检查Spark是否正常运行"
    elif "model" in error_str or "模型" in error_str:
        return "模型加载失败，请检查模型文件"
    elif "database" in error_str or "mysql" in error_str:
        return "数据库连接失败，请检查数据库配置"
    
    # 默认消息
    return f"操作失败: {str(exception)[:100]}"


def api_error_handler(func):
    """API错误处理装饰器
    
    使用方法:
        @api_error_handler
        def my_api_endpoint():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 记录详细错误日志
            logger.error(f"API错误 [{func.__name__}]: {str(e)}")
            logger.debug(traceback.format_exc())
            
            # 返回友好的错误消息
            friendly_message = get_friendly_error_message(e)
            
            return APIResponse.error(
                message=friendly_message,
                code=500,
                details={
                    "error_type": type(e).__name__,
                    "endpoint": func.__name__
                }
            )
    return wrapper


def validate_required_params(data: dict, required: list) -> tuple:
    """验证必需参数
    
    Args:
        data: 请求数据
        required: 必需参数列表
    
    Returns:
        (is_valid, missing_params)
    """
    if not data:
        return False, required
    
    missing = [param for param in required if param not in data or data[param] is None]
    return len(missing) == 0, missing


def validate_params(required_params: list):
    """参数验证装饰器
    
    使用方法:
        @validate_params(['text', 'model'])
        def analyze_sentiment():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            
            # 获取请求数据
            if request.method == 'GET':
                data = request.args.to_dict()
            else:
                data = request.get_json(silent=True) or {}
            
            # 验证参数
            is_valid, missing = validate_required_params(data, required_params)
            
            if not is_valid:
                return APIResponse.bad_request(
                    message=f"缺少必需参数: {', '.join(missing)}",
                    details={"missing_params": missing}
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
