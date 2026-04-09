"""
Logging Configuration for Weibo Sentiment Analysis System
Provides centralized logging setup with console and file output
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from functools import wraps
import traceback

from config import config


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Add color to level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logging():
    """Setup logging configuration with console and file handlers"""
    
    # Ensure logs directory exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Get configuration
    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)
    log_format = config.logging.format
    log_file = config.logging.file_path or "logs/app.log"
    max_bytes = config.logging.max_bytes
    backup_count = config.logging.backup_count
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = ColoredFormatter(log_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Create separate error file handler for ERROR and CRITICAL
    error_log_file = log_dir / "error.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
    )
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)
    
    # Log initialization
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")
    logger.info(f"Log level: {config.logging.level}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Error log file: {error_log_file}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)


def log_operation(operation_name: str, level: str = "INFO"):
    """Decorator to log operation start and end with timing"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = datetime.now()
            
            # Log operation start
            getattr(logger, level.lower())(
                f"Operation '{operation_name}' started - {func.__name__}"
            )
            
            try:
                result = func(*args, **kwargs)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # Log operation success
                getattr(logger, level.lower())(
                    f"Operation '{operation_name}' completed successfully - "
                    f"{func.__name__} took {duration:.2f}s"
                )
                
                return result
                
            except Exception as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # Log operation failure
                logger.error(
                    f"Operation '{operation_name}' failed - "
                    f"{func.__name__} took {duration:.2f}s - Error: {str(e)}"
                )
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
                
        return wrapper
    return decorator


def log_api_call(endpoint: str, method: str = "GET"):
    """Decorator to log API calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = datetime.now()
            
            # Log API call start
            logger.info(f"API call {method} {endpoint} started")
            
            try:
                result = func(*args, **kwargs)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # Log API call success
                logger.info(f"API call {method} {endpoint} completed - {duration:.3f}s")
                
                return result
                
            except Exception as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # Log API call failure
                logger.error(f"API call {method} {endpoint} failed - {duration:.3f}s - Error: {str(e)}")
                raise
                
        return wrapper
    return decorator


def log_task_progress(task_id: str, operation: str, progress: Optional[float] = None):
    """Log task progress updates"""
    logger = get_logger("tasks")
    
    if progress is not None:
        logger.info(f"Task {task_id} - {operation} - Progress: {progress:.1f}%")
    else:
        logger.info(f"Task {task_id} - {operation}")


def log_pipeline_stage(stage_name: str, status: str, details: Optional[str] = None):
    """Log pipeline stage status"""
    logger = get_logger("pipeline")
    
    message = f"Pipeline stage '{stage_name}' - {status}"
    if details:
        message += f" - {details}"
    
    if status.upper() in ["STARTED", "COMPLETED", "SUCCESS"]:
        logger.info(message)
    elif status.upper() in ["FAILED", "ERROR"]:
        logger.error(message)
    else:
        logger.info(message)


def log_sentiment_analysis(text_preview: str, result: Optional[str] = None, error: Optional[str] = None):
    """Log sentiment analysis operations"""
    logger = get_logger("sentiment")
    
    # Truncate text preview for logging
    text_preview = text_preview[:100] + "..." if len(text_preview) > 100 else text_preview
    
    if result:
        logger.info(f"Sentiment analysis completed - Text: '{text_preview}' - Result: {result}")
    elif error:
        logger.error(f"Sentiment analysis failed - Text: '{text_preview}' - Error: {error}")
    else:
        logger.info(f"Sentiment analysis started - Text: '{text_preview}'")


def log_data_collection(task_id: str, operation: str, count: Optional[int] = None, error: Optional[str] = None):
    """Log data collection operations"""
    logger = get_logger("collection")
    
    if count is not None:
        logger.info(f"Data collection - Task {task_id} - {operation} - Count: {count}")
    elif error:
        logger.error(f"Data collection - Task {task_id} - {operation} - Error: {error}")
    else:
        logger.info(f"Data collection - Task {task_id} - {operation}")


def log_user_action(user_id: str, action: str, details: Optional[str] = None):
    """Log user actions for audit trail"""
    logger = get_logger("audit")
    
    message = f"User {user_id} - {action}"
    if details:
        message += f" - {details}"
    
    logger.info(message)


def log_system_event(event_type: str, message: str, level: str = "INFO"):
    """Log system events"""
    logger = get_logger("system")
    
    log_message = f"System event - {event_type} - {message}"
    getattr(logger, level.lower())(log_message)


# Initialize logging when module is imported
setup_logging()

# Export commonly used functions
__all__ = [
    'get_logger',
    'log_operation',
    'log_api_call',
    'log_task_progress',
    'log_pipeline_stage',
    'log_sentiment_analysis',
    'log_data_collection',
    'log_user_action',
    'log_system_event',
    'setup_logging'
]
