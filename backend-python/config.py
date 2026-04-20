"""
Configuration Management for Weibo Sentiment Analysis System
Centralized configuration with environment variable support and default values
"""
import os
from typing import Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = 'localhost'
    port: int = 3306
    database: str = 'weibo_sentiment'
    username: str = 'root'
    password: str = '123456'
    charset: str = 'utf8mb4'
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        return cls(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '3306')),
            database=os.getenv('DB_NAME', 'weibo_sentiment'),
            username=os.getenv('DB_USER', os.getenv('DB_USERNAME', 'root')),
            password=os.getenv('DB_PASSWORD', '123456'),
            charset=os.getenv('DB_CHARSET', 'utf8mb4'),
            pool_size=int(os.getenv('DB_POOL_SIZE', '10')),
            max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '20')),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30')),
            pool_recycle=int(os.getenv('DB_POOL_RECYCLE', '3600')),
        )
    
    def get_connection_url(self) -> str:
        return f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"


@dataclass
class HBaseConfig:
    """HBase configuration"""
    quorum: str = 'localhost'
    port: int = 9090
    thrift_port: int = 9090
    master_port: int = 16000
    timeout: int = 30000
    
    @classmethod
    def from_env(cls) -> 'HBaseConfig':
        return cls(
            quorum=os.getenv('HBASE_HOST', os.getenv('HBASE_QUORUM', 'localhost')),
            port=int(os.getenv('HBASE_PORT', '9090')),
            thrift_port=int(os.getenv('HBASE_THRIFT_PORT', '9090')),
            master_port=int(os.getenv('HBASE_MASTER_PORT', '16000')),
            timeout=int(os.getenv('HBASE_TIMEOUT', '30000')),
        )


@dataclass
class HDFSConfig:
    """HDFS configuration"""
    namenode_host: str = ''
    namenode_port: int = 9000
    webhdfs_port: int = 50070
    user: str = 'root'
    raw_dir: str = '/weibo/raw'
    output_dir: str = '/weibo/output'
    checkpoint_dir: str = '/weibo/checkpoint'
    
    @classmethod
    def from_env(cls) -> 'HDFSConfig':
        return cls(
            namenode_host=os.getenv('HDFS_NAMENODE_HOST', ''),
            namenode_port=int(os.getenv('HDFS_NAMENODE_PORT', '9000')),
            webhdfs_port=int(os.getenv('HDFS_WEBHDFS_PORT', '50070')),
            user=os.getenv('HDFS_USER', 'root'),
            raw_dir=os.getenv('HDFS_RAW_DIR', '/weibo/raw'),
            output_dir=os.getenv('HDFS_OUTPUT_DIR', '/weibo/output'),
            checkpoint_dir=os.getenv('HDFS_CHECKPOINT_DIR', '/weibo/checkpoint'),
        )
    
    @property
    def is_enabled(self) -> bool:
        """Check if HDFS is configured"""
        return bool(self.namenode_host)
    
    @property
    def fs_default(self) -> str:
        """Get fs.defaultFS URL"""
        if self.is_enabled:
            return f'hdfs://{self.namenode_host}:{self.namenode_port}'
        return ''


@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = 'localhost'
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    socket_timeout: int = 5
    connection_pool_max_connections: int = 50
    
    @classmethod
    def from_env(cls) -> 'RedisConfig':
        return cls(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD') or None,
            socket_timeout=int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')),
            connection_pool_max_connections=int(os.getenv('REDIS_POOL_MAX_CONNECTIONS', '50')),
        )


@dataclass
class SparkConfig:
    """Spark configuration"""
    master_url: str = 'local[*]'
    app_name: str = 'WeiboSentimentAnalysis'
    executor_memory: str = '2g'
    driver_memory: str = '1g'
    max_result_size: str = '1g'
    executor_cores: int = 2
    driver_cores: int = 1
    default_parallelism: int = 100
    sql_adaptive_enabled: bool = True
    sql_adaptive_coalesce_partitions_enabled: bool = True
    
    @classmethod
    def from_env(cls) -> 'SparkConfig':
        return cls(
            master_url=os.getenv('SPARK_MASTER_URL', 'local[*]'),
            app_name=os.getenv('SPARK_APP_NAME', 'WeiboSentimentAnalysis'),
            executor_memory=os.getenv('SPARK_EXECUTOR_MEMORY', '2g'),
            driver_memory=os.getenv('SPARK_DRIVER_MEMORY', '1g'),
            max_result_size=os.getenv('SPARK_MAX_RESULT_SIZE', '1g'),
            executor_cores=int(os.getenv('SPARK_EXECUTOR_CORES', '2')),
            driver_cores=int(os.getenv('SPARK_DRIVER_CORES', '1')),
            default_parallelism=int(os.getenv('SPARK_DEFAULT_PARALLELISM', '100')),
            sql_adaptive_enabled=os.getenv('SPARK_SQL_ADAPTIVE_ENABLED', 'true').lower() == 'true',
            sql_adaptive_coalesce_partitions_enabled=os.getenv('SPARK_SQL_ADAPTIVE_COALESCE_ENABLED', 'true').lower() == 'true',
        )


@dataclass
class FlaskConfig:
    """Flask application configuration"""
    secret_key: str = 'dev-secret-key-change-in-production'
    debug: bool = False
    testing: bool = False
    host: str = '0.0.0.0'
    port: int = 5000
    cors_origins: List[str] = None
    
    @classmethod
    def from_env(cls) -> 'FlaskConfig':
        cors_origins_str = os.getenv('CORS_ORIGINS', '*')
        cors_origins = [origin.strip() for origin in cors_origins_str.split(',')] if cors_origins_str else ['*']
        
        return cls(
            secret_key=os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
            debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true',
            testing=os.getenv('FLASK_TESTING', 'false').lower() == 'true',
            host=os.getenv('FLASK_HOST', '0.0.0.0'),
            port=int(os.getenv('FLASK_PORT', '5000')),
            cors_origins=cors_origins,
        )


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = 'INFO'
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_path: Optional[str] = None
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5
    
    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        return cls(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            format=os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            file_path=os.getenv('LOG_FILE_PATH') or None,
            max_bytes=int(os.getenv('LOG_MAX_BYTES', '10485760')),
            backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5')),
        )


@dataclass
class SecurityConfig:
    """Security configuration"""
    jwt_secret_key: str = 'jwt-secret-key-change-in-production'
    jwt_access_token_expires: int = 3600  # 1 hour
    jwt_refresh_token_expires: int = 86400  # 24 hours
    bcrypt_rounds: int = 12
    password_min_length: int = 8
    session_timeout: int = 1800  # 30 minutes
    
    @classmethod
    def from_env(cls) -> 'SecurityConfig':
        return cls(
            jwt_secret_key=os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production'),
            jwt_access_token_expires=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600')),
            jwt_refresh_token_expires=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', '86400')),
            bcrypt_rounds=int(os.getenv('BCRYPT_ROUNDS', '12')),
            password_min_length=int(os.getenv('PASSWORD_MIN_LENGTH', '8')),
            session_timeout=int(os.getenv('SESSION_TIMEOUT', '1800')),
        )


@dataclass
class CrawlerConfig:
    """Web crawler configuration"""
    default_request_interval: float = 1.0
    max_concurrent_requests: int = 5
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    user_agent_rotation: bool = True
    use_proxy: bool = False
    proxy_list: List[str] = None
    
    @classmethod
    def from_env(cls) -> 'CrawlerConfig':
        proxy_list_str = os.getenv('PROXY_LIST', '')
        proxy_list = [proxy.strip() for proxy in proxy_list_str.split(',') if proxy.strip()] if proxy_list_str else []
        
        return cls(
            default_request_interval=float(os.getenv('CRAWLER_DEFAULT_INTERVAL', '1.0')),
            max_concurrent_requests=int(os.getenv('CRAWLER_MAX_CONCURRENT', '5')),
            request_timeout=int(os.getenv('CRAWLER_REQUEST_TIMEOUT', '30')),
            max_retries=int(os.getenv('CRAWLER_MAX_RETRIES', '3')),
            retry_delay=float(os.getenv('CRAWLER_RETRY_DELAY', '1.0')),
            user_agent_rotation=os.getenv('CRAWLER_USER_AGENT_ROTATION', 'true').lower() == 'true',
            use_proxy=os.getenv('CRAWLER_USE_PROXY', 'false').lower() == 'true',
            proxy_list=proxy_list,
        )


@dataclass
class ModelConfig:
    """Machine learning model configuration"""
    model_cache_dir: str = './model_cache'
    default_sentiment_model: str = 'bert-base-chinese'
    confidence_threshold: float = 0.7
    batch_size: int = 32
    max_sequence_length: int = 512
    use_gpu: bool = False
    
    @classmethod
    def from_env(cls) -> 'ModelConfig':
        return cls(
            model_cache_dir=os.getenv('MODEL_CACHE_DIR', './model_cache'),
            default_sentiment_model=os.getenv('DEFAULT_SENTIMENT_MODEL', 'bert-base-chinese'),
            confidence_threshold=float(os.getenv('CONFIDENCE_THRESHOLD', '0.7')),
            batch_size=int(os.getenv('MODEL_BATCH_SIZE', '32')),
            max_sequence_length=int(os.getenv('MODEL_MAX_SEQUENCE_LENGTH', '512')),
            use_gpu=os.getenv('MODEL_USE_GPU', 'false').lower() == 'true',
        )


@dataclass
class SystemConfig:
    """System configuration parameters"""
    session_timeout: int = 120  # minutes
    data_retention: int = 30    # days
    debug_mode: bool = False
    audit_enabled: bool = True
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    backup_enabled: bool = True
    backup_interval: int = 24   # hours
    
    @classmethod
    def from_env(cls) -> 'SystemConfig':
        return cls(
            session_timeout=int(os.getenv('SESSION_TIMEOUT', '120')),
            data_retention=int(os.getenv('DATA_RETENTION', '30')),
            debug_mode=os.getenv('DEBUG', 'false').lower() == 'true',
            audit_enabled=os.getenv('AUDIT_ENABLED', 'true').lower() == 'true',
            max_upload_size=int(os.getenv('MAX_UPLOAD_SIZE', str(10 * 1024 * 1024))),
            backup_enabled=os.getenv('BACKUP_ENABLED', 'true').lower() == 'true',
            backup_interval=int(os.getenv('BACKUP_INTERVAL', '24')),
        )


@dataclass
class Config:
    """Main configuration class containing all sub-configurations"""
    flask: FlaskConfig
    database: DatabaseConfig
    hbase: HBaseConfig
    hdfs: HDFSConfig
    redis: RedisConfig
    spark: SparkConfig
    logging: LoggingConfig
    security: SecurityConfig
    crawler: CrawlerConfig
    model: ModelConfig
    system: SystemConfig
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables"""
        return cls(
            flask=FlaskConfig.from_env(),
            database=DatabaseConfig.from_env(),
            hbase=HBaseConfig.from_env(),
            hdfs=HDFSConfig.from_env(),
            redis=RedisConfig.from_env(),
            spark=SparkConfig.from_env(),
            logging=LoggingConfig.from_env(),
            security=SecurityConfig.from_env(),
            crawler=CrawlerConfig.from_env(),
            model=ModelConfig.from_env(),
            system=SystemConfig.from_env(),
        )
    
    def validate(self) -> bool:
        """Validate configuration values"""
        errors = []
        
        # Validate Flask config
        if not self.flask.secret_key or self.flask.secret_key == 'dev-secret-key-change-in-production':
            if not self.flask.debug:
                errors.append("SECRET_KEY must be set in production")
        
        # Validate database config
        if not self.database.password:
            errors.append("Database password not configured")
        
        # Validate security config
        if not self.security.jwt_secret_key or self.security.jwt_secret_key == 'jwt-secret-key-change-in-production':
            if not self.flask.debug:
                errors.append("JWT_SECRET_KEY must be set in production")
        
        if errors:
            for error in errors:
                logger.error(f"Configuration validation error: {error}")
            return False
        
        return True
    
    def setup_logging(self):
        """Setup logging based on configuration"""
        import logging.handlers
        
        level = getattr(logging, self.logging.level.upper(), logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(self.logging.format)
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # File handler (if configured)
        if self.logging.file_path:
            file_handler = logging.handlers.RotatingFileHandler(
                self.logging.file_path,
                maxBytes=self.logging.max_bytes,
                backupCount=self.logging.backup_count
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)


# Global configuration instance
config = Config.from_env()

# Validate and setup logging on import
if not config.validate():
    logger.warning("Configuration validation failed. Some features may not work correctly.")

config.setup_logging()

# Export commonly used configurations
__all__ = [
    'Config',
    'config',
    'DatabaseConfig',
    'HBaseConfig',
    'HDFSConfig',
    'RedisConfig',
    'SparkConfig',
    'FlaskConfig',
    'LoggingConfig',
    'SecurityConfig',
    'CrawlerConfig',
    'ModelConfig'
]
