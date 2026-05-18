"""
HBase Client - DEPRECATED (已移除)

HBase 已从系统架构中移除。所有情感分析结果直接存储在 MySQL 中。
本文件保留空函数签名以避免残留 import 报错。
"""
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


def get_hbase_connection():
    """已移除 - 返回 None"""
    return None


def is_hbase_available() -> bool:
    """已移除 - 始终返回 False"""
    return False


def make_row_key(weibo_id: str, timestamp: Optional[float] = None) -> str:
    return ""


def put_sentiment_result(weibo_id: str, info: Dict, sentiment: Dict, metrics: Dict, timestamp: Optional[float] = None) -> bool:
    logger.debug("HBase已移除，情感结果请写入MySQL")
    return False


def batch_put_sentiment_results(records: List[Dict[str, Any]]) -> int:
    logger.debug("HBase已移除，情感结果请写入MySQL")
    return 0


def scan_sentiment_results(limit: int = 100, start_time: Optional[float] = None, end_time: Optional[float] = None) -> List[Dict[str, Any]]:
    return []


def get_sentiment_by_id(weibo_id: str, timestamp: Optional[float] = None) -> Optional[Dict[str, Any]]:
    return None
