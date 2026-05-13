"""
HDFS Client - 微博舆情分析系统
提供 HDFS 读写工具, 支持本地模式回退 (无 HDFS 时自动使用本地文件系统)
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# HDFS 默认路径
# 论文 5.1: 原始 JSON 按天分区存到 HDFS /raw/YYYY-MM-DD/
HDFS_RAW_DIR = os.getenv("HDFS_RAW_DIR", "/raw")
HDFS_OUTPUT_DIR = os.getenv("HDFS_OUTPUT_DIR", "/output")
HDFS_CHECKPOINT_DIR = os.getenv("HDFS_CHECKPOINT_DIR", "/checkpoint")
HDFS_CLEANED_DIR = os.getenv("HDFS_CLEANED_DIR", "/cleaned")


def get_hdfs_url() -> Optional[str]:
    """获取 HDFS NameNode URL, 返回 None 表示使用本地模式"""
    host = os.getenv("HDFS_NAMENODE_HOST", "")
    port = os.getenv("HDFS_NAMENODE_PORT", "9000")
    if host:
        return f"hdfs://{host}:{port}"
    return None


def is_hdfs_available() -> bool:
    """检查 HDFS 是否可用"""
    hdfs_url = get_hdfs_url()
    if not hdfs_url:
        return False
    try:
        from hdfs import InsecureClient
        client = InsecureClient(
            f"http://{os.getenv('HDFS_NAMENODE_HOST', 'namenode')}:50070",
            user="root",
            timeout=5
        )
        client.status("/")
        return True
    except Exception as e:
        logger.debug(f"HDFS not available: {e}")
        return False


def get_hdfs_client():
    """获取 HDFS WebHDFS 客户端.

    端口优先级: HDFS_WEBHDFS_PORT > 50070 (Hadoop 2 default) > 9870 (Hadoop 3 default).
    本项目 namenode 容器实际监听 50070 (Hadoop 2), 故默认 50070.
    """
    try:
        from hdfs import InsecureClient
        host = os.getenv("HDFS_NAMENODE_HOST", "namenode")
        port = os.getenv("HDFS_WEBHDFS_PORT", "50070")
        user = os.getenv("HDFS_USER", "root")
        client = InsecureClient(f"http://{host}:{port}", user=user, timeout=30)
        return client
    except ImportError:
        logger.warning("hdfs package not installed, install with: pip install hdfs")
        return None
    except Exception as e:
        logger.error(f"Failed to create HDFS client: {e}")
        return None


# ==================== 论文 5.1 按日期分区 ====================

def get_raw_partition_path(task_id: str, when: Optional[datetime] = None) -> str:
    """生成按日期分区的 HDFS 原始数据路径.

    论文 5.1: 获取的数据保存为 JSON 文件并按天存储到 HDFS 上.
    路径格式: {HDFS_RAW_DIR}/dt=YYYY-MM-DD/crawl_result_<task_id>.json

    使用 dt= 前缀符合 Hive/Spark 风格分区, 后续 Spark 作业能直接按
    分区裁剪 (PARTITION BY dt) 提高查询性能.
    """
    when = when or datetime.now()
    return f"{HDFS_RAW_DIR}/dt={when.strftime('%Y-%m-%d')}/crawl_result_{task_id}.json"


def upload_raw_to_hdfs_partitioned(local_path: str, task_id: str,
                                    when: Optional[datetime] = None) -> Optional[str]:
    """采集结果按天分区上传到 HDFS, 返回 HDFS 路径; 失败返回 None.

    与 upload_to_hdfs 的差异: 自动构造 /raw/dt=YYYY-MM-DD/<file>.json 路径,
    并在父目录不存在时自动建.
    """
    if not os.path.exists(local_path):
        logger.warning(f"Local file not found, skip HDFS upload: {local_path}")
        return None

    client = get_hdfs_client()
    if not client:
        return None

    hdfs_path = get_raw_partition_path(task_id, when)
    parent_dir = os.path.dirname(hdfs_path)
    try:
        client.makedirs(parent_dir, permission=755)
        client.upload(hdfs_path, local_path, overwrite=True)
        logger.info(f"采集结果已按日期分区上传 HDFS: {local_path} -> {hdfs_path}")
        return hdfs_path
    except Exception as e:
        logger.error(f"HDFS partitioned upload failed: {e}", exc_info=True)
        return None


def upload_to_hdfs(local_path: str, hdfs_path: str, overwrite: bool = True) -> bool:
    """上传本地文件到 HDFS"""
    client = get_hdfs_client()
    if not client:
        logger.warning(f"HDFS unavailable, skipping upload: {local_path}")
        return False
    try:
        client.upload(hdfs_path, local_path, overwrite=overwrite)
        logger.info(f"Uploaded to HDFS: {local_path} -> {hdfs_path}")
        return True
    except Exception as e:
        logger.error(f"HDFS upload failed: {e}")
        return False


def upload_json_to_hdfs(data: Any, hdfs_path: str) -> bool:
    """将 JSON 数据直接写入 HDFS"""
    client = get_hdfs_client()
    if not client:
        logger.warning(f"HDFS unavailable, skipping JSON upload to {hdfs_path}")
        return False
    try:
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        with client.write(hdfs_path, overwrite=True) as writer:
            writer.write(json_bytes)
        logger.info(f"Wrote JSON to HDFS: {hdfs_path} ({len(json_bytes)} bytes)")
        return True
    except Exception as e:
        logger.error(f"HDFS JSON write failed: {e}")
        return False


def read_from_hdfs(hdfs_path: str) -> Optional[str]:
    """从 HDFS 读取文本内容"""
    client = get_hdfs_client()
    if not client:
        return None
    try:
        with client.read(hdfs_path, encoding="utf-8") as reader:
            return reader.read()
    except Exception as e:
        logger.error(f"HDFS read failed: {e}")
        return None


def list_hdfs_dir(hdfs_path: str) -> List[str]:
    """列出 HDFS 目录下的文件"""
    client = get_hdfs_client()
    if not client:
        return []
    try:
        return client.list(hdfs_path, status=False)
    except Exception as e:
        logger.error(f"HDFS list failed: {e}")
        return []


def get_raw_data_path(filename: str = "") -> str:
    """获取原始数据路径 (HDFS 或本地)"""
    hdfs_url = get_hdfs_url()
    if hdfs_url:
        base = f"{hdfs_url}{HDFS_RAW_DIR}"
    else:
        base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "weibo_raw")
        os.makedirs(base, exist_ok=True)
    return f"{base}/{filename}" if filename else base


def get_output_data_path(filename: str = "") -> str:
    """获取输出数据路径 (HDFS 或本地)"""
    hdfs_url = get_hdfs_url()
    if hdfs_url:
        base = f"{hdfs_url}{HDFS_OUTPUT_DIR}"
    else:
        base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "output")
        os.makedirs(base, exist_ok=True)
    return f"{base}/{filename}" if filename else base
