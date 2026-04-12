"""
HBase Client - 微博舆情分析系统
提供 HBase 读写工具, 支持本地/MySQL 回退 (无 HBase 时自动降级)

表结构: weibo_sentiment
  - cf_info:      基础信息 (weibo_id, content, user_name, post_time, source_url)
  - cf_sentiment:  情感分析 (score, label, confidence, method, analyzed_at)
  - cf_metrics:   热度指标 (reposts, comments, likes, heat_score, rank_score)

RowKey 设计: {reversed_timestamp}_{weibo_id} (保证最新数据在前, 避免热点)
"""
import os
import time
import json
import struct
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# HBase 表和列族定义
TABLE_SENTIMENT = "weibo_sentiment"
TABLE_RAW_INDEX = "weibo_raw_index"
CF_INFO = b"cf_info"
CF_SENTIMENT = b"cf_sentiment"
CF_METRICS = b"cf_metrics"
CF_IDX = b"cf_idx"


def get_hbase_connection():
    """获取 HBase Thrift 连接 (happybase)"""
    try:
        import happybase
        host = os.getenv("HBASE_HOST", os.getenv("HBASE_QUORUM", "localhost"))
        port = int(os.getenv("HBASE_THRIFT_PORT", os.getenv("HBASE_PORT", "9090")))
        timeout = int(os.getenv("HBASE_TIMEOUT", "30000"))
        conn = happybase.Connection(host=host, port=port, timeout=timeout)
        conn.open()
        return conn
    except ImportError:
        logger.warning("happybase not installed, install with: pip install happybase")
        return None
    except Exception as e:
        logger.error(f"HBase connection failed: {e}")
        return None


def is_hbase_available() -> bool:
    """检查 HBase 是否可用"""
    conn = get_hbase_connection()
    if conn:
        try:
            conn.tables()
            conn.close()
            return True
        except Exception:
            pass
    return False


def make_row_key(weibo_id: str, timestamp: Optional[float] = None) -> str:
    """
    生成 RowKey: {reversed_timestamp}_{weibo_id}
    reversed_timestamp = 9999999999 - unix_timestamp (秒)
    """
    ts = int(timestamp or time.time())
    reversed_ts = 9999999999 - ts
    return f"{reversed_ts:010d}_{weibo_id}"


def put_sentiment_result(
    weibo_id: str,
    info: Dict[str, str],
    sentiment: Dict[str, str],
    metrics: Dict[str, str],
    timestamp: Optional[float] = None,
) -> bool:
    """
    写入情感分析结果到 HBase

    Args:
        weibo_id: 微博 ID
        info: 基础信息 {content, user_name, post_time, source_url, ...}
        sentiment: 情感结果 {score, label, confidence, method, analyzed_at}
        metrics: 热度指标 {reposts, comments, likes, heat_score, rank_score}
        timestamp: 原始发布时间戳
    """
    conn = get_hbase_connection()
    if not conn:
        logger.warning(f"HBase unavailable, skipping write for {weibo_id}")
        return False

    try:
        table = conn.table(TABLE_SENTIMENT)
        row_key = make_row_key(weibo_id, timestamp)

        data = {}
        for k, v in info.items():
            data[f"cf_info:{k}".encode()] = str(v).encode("utf-8")
        for k, v in sentiment.items():
            data[f"cf_sentiment:{k}".encode()] = str(v).encode("utf-8")
        for k, v in metrics.items():
            data[f"cf_metrics:{k}".encode()] = str(v).encode("utf-8")

        table.put(row_key.encode(), data)
        logger.debug(f"HBase put: {row_key}")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"HBase put failed for {weibo_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return False


def batch_put_sentiment_results(records: List[Dict[str, Any]]) -> int:
    """
    批量写入情感分析结果

    Args:
        records: [{weibo_id, info:{...}, sentiment:{...}, metrics:{...}, timestamp}, ...]

    Returns:
        成功写入的记录数
    """
    conn = get_hbase_connection()
    if not conn:
        logger.warning("HBase unavailable, skipping batch write")
        return 0

    try:
        table = conn.table(TABLE_SENTIMENT)
        batch = table.batch(batch_size=100)
        count = 0

        for record in records:
            weibo_id = record.get("weibo_id", "")
            if not weibo_id:
                continue

            row_key = make_row_key(weibo_id, record.get("timestamp"))
            data = {}
            for k, v in record.get("info", {}).items():
                data[f"cf_info:{k}".encode()] = str(v).encode("utf-8")
            for k, v in record.get("sentiment", {}).items():
                data[f"cf_sentiment:{k}".encode()] = str(v).encode("utf-8")
            for k, v in record.get("metrics", {}).items():
                data[f"cf_metrics:{k}".encode()] = str(v).encode("utf-8")

            batch.put(row_key.encode(), data)
            count += 1

        batch.send()
        conn.close()
        logger.info(f"HBase batch put: {count} records")
        return count
    except Exception as e:
        logger.error(f"HBase batch put failed: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return 0


def scan_sentiment_results(
    limit: int = 100,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    扫描情感分析结果 (按时间倒序)

    Args:
        limit: 最大返回条数
        start_time: 起始时间戳 (越新越前)
        end_time: 结束时间戳
    """
    conn = get_hbase_connection()
    if not conn:
        return []

    try:
        table = conn.table(TABLE_SENTIMENT)

        # RowKey 为反转时间戳, 所以 start/stop 需要反转
        row_start = None
        row_stop = None
        if end_time:
            row_start = f"{9999999999 - int(end_time):010d}".encode()
        if start_time:
            row_stop = f"{9999999999 - int(start_time):010d}".encode()

        results = []
        for key, data in table.scan(
            row_start=row_start,
            row_stop=row_stop,
            limit=limit,
        ):
            record = {"row_key": key.decode()}
            for col_key, col_val in data.items():
                cf_col = col_key.decode()
                record[cf_col] = col_val.decode("utf-8")
            results.append(record)

        conn.close()
        return results
    except Exception as e:
        logger.error(f"HBase scan failed: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return []


def get_sentiment_by_id(weibo_id: str, timestamp: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """根据微博 ID 获取情感分析结果"""
    conn = get_hbase_connection()
    if not conn:
        return None

    try:
        table = conn.table(TABLE_SENTIMENT)
        row_key = make_row_key(weibo_id, timestamp)
        data = table.row(row_key.encode())

        if not data:
            conn.close()
            return None

        record = {"row_key": row_key}
        for col_key, col_val in data.items():
            record[col_key.decode()] = col_val.decode("utf-8")

        conn.close()
        return record
    except Exception as e:
        logger.error(f"HBase get failed for {weibo_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return None
