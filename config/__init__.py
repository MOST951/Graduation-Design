"""
微博情感分析系统 - 配置管理模块
================================
提供统一的配置管理，支持多环境配置
"""

import os
from pathlib import Path
from typing import List, Optional

# 尝试加载 dotenv
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass  # dotenv 未安装时跳过


class Config:
    """基础配置类"""
    
    # Flask 配置
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV: str = os.getenv('FLASK_ENV', 'development')
    DEBUG: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # 数据库配置
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_PORT: int = int(os.getenv('DB_PORT', '3306'))
    DB_NAME: str = os.getenv('DB_NAME', 'weibo_sentiment')
    DB_USERNAME: str = os.getenv('DB_USERNAME', 'root')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', '')
    
    @property
    def DATABASE_URL(self) -> str:
        """构建数据库连接URL"""
        return f"mysql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Redis 配置
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_PASSWORD: str = os.getenv('REDIS_PASSWORD', '')
    
    @property
    def REDIS_URL(self) -> str:
        """构建Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    # 服务端口配置
    FLASK_PORT: int = int(os.getenv('FLASK_RUN_PORT', '5000'))
    FRONTEND_PORT: int = int(os.getenv('FRONTEND_PORT', '5173'))
    API_BASE_URL: str = os.getenv('API_BASE_URL', 'http://localhost:5000')
    
    # CORS 配置
    @property
    def CORS_ORIGINS(self) -> List[str]:
        origins = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
        return [o.strip() for o in origins.split(',')]
    
    @property
    def CORS_METHODS(self) -> List[str]:
        methods = os.getenv('CORS_METHODS', 'GET,POST,PUT,DELETE,OPTIONS')
        return [m.strip() for m in methods.split(',')]
    
    # Spark 配置
    SPARK_MASTER_URL: str = os.getenv('SPARK_MASTER_URL', 'local[*]')
    SPARK_HOME: str = os.getenv('SPARK_HOME', '/opt/spark')
    SPARK_DRIVER_MEMORY: str = os.getenv('SPARK_DRIVER_MEMORY', '2g')
    SPARK_EXECUTOR_MEMORY: str = os.getenv('SPARK_EXECUTOR_MEMORY', '2g')
    
    # HDFS 配置
    HDFS_DEFAULT_FS: str = os.getenv('HDFS_DEFAULT_FS', 'hdfs://localhost:9000')
    
    # HBase 配置
    HBASE_HOST: str = os.getenv('HBASE_HOST', 'localhost')
    HBASE_PORT: int = int(os.getenv('HBASE_PORT', '9090'))
    
    # 模型配置
    MODEL_PATH: str = os.getenv('SENTIMENT_MODEL_PATH', 'backend/models/sentiment_model.pkl')
    BERT_MODEL_NAME: str = os.getenv('BERT_MODEL_NAME', 'hfl/chinese-bert-wwm-ext')
    MAX_TEXT_LENGTH: int = int(os.getenv('MAX_TEXT_LENGTH', '512'))
    ENABLE_CACHE: bool = os.getenv('ENABLE_CACHE', 'True').lower() == 'true'
    
    # 日志配置
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/app.log')
    
    @classmethod
    def validate(cls) -> bool:
        """验证必需配置"""
        instance = cls()
        required = ['SECRET_KEY']
        missing = []
        
        for key in required:
            value = getattr(instance, key, None)
            if not value or value == 'dev-secret-key-change-in-production':
                if instance.FLASK_ENV == 'production':
                    missing.append(key)
        
        if missing:
            raise ValueError(f"生产环境缺少必需配置: {missing}")
        return True


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    FLASK_ENV = 'development'


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    FLASK_ENV = 'production'
    
    # 生产环境安全配置
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    DB_NAME = 'weibo_sentiment_test'


# 配置映射
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env: Optional[str] = None) -> Config:
    """
    获取配置实例
    
    Args:
        env: 环境名称 (development/production/testing)
    
    Returns:
        对应环境的配置实例
    """
    env = env or os.getenv('FLASK_ENV', 'development')
    config_class = config_by_name.get(env, config_by_name['default'])
    return config_class()
