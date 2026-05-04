"""

数据存储服务模块

================



提供多种存储后端的统一接口：

1. HDFS存储：原始数据、清洗数据、特征向量（Parquet格式）

2. HBase存储：微博数据、用户画像、热点话题

3. MySQL存储：元数据、任务管理、系统配置

4. Redis缓存：热点数据、会话管理、分布式锁



使用示例:

    from backend.services.storage_service import StorageService

    

    storage = StorageService()

    

    # HDFS存储

    storage.hdfs.save_parquet(df, '/weibo/raw', partition_by=['date'])

    

    # MySQL操作

    storage.mysql.insert_task(task_data)

    

    # Redis缓存

    storage.redis.cache_hot_search(hot_list)

"""



import os

import json

import time

import hashlib

import logging

import threading

from abc import ABC, abstractmethod

from datetime import datetime, timedelta

from typing import Dict, List, Optional, Any, Union

from dataclasses import dataclass, field, asdict

from contextlib import contextmanager

from functools import wraps



# 配置日志

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('StorageService')





# ==================== 配置加载 ====================



def load_env_config() -> Dict[str, str]:

    """加载环境变量配置"""

    config = {}

    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')

    

    if os.path.exists(env_path):

        with open(env_path, 'r', encoding='utf-8') as f:

            for line in f:

                line = line.strip()

                if line and not line.startswith('#') and '=' in line:

                    key, value = line.split('=', 1)

                    config[key.strip()] = value.strip()

    

    # 从环境变量覆盖

    for key in ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USERNAME', 'DB_PASSWORD',

                'REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD',

                'HDFS_DEFAULT_FS', 'HBASE_HOST']:

        if key in os.environ:

            config[key] = os.environ[key]

    

    return config





ENV_CONFIG = load_env_config()





# ==================== 数据模型 ====================



@dataclass

class StorageConfig:

    """存储配置"""

    # MySQL

    mysql_host: str = ENV_CONFIG.get('DB_HOST', 'localhost')

    mysql_port: int = int(ENV_CONFIG.get('DB_PORT', '3306'))

    mysql_database: str = ENV_CONFIG.get('DB_NAME', 'weibo_prod')

    mysql_user: str = ENV_CONFIG.get('DB_USERNAME', 'root')

    mysql_password: str = ENV_CONFIG.get('DB_PASSWORD', '')

    

    # Redis

    redis_host: str = ENV_CONFIG.get('REDIS_HOST', 'localhost')

    redis_port: int = int(ENV_CONFIG.get('REDIS_PORT', '6379'))

    redis_password: str = ENV_CONFIG.get('REDIS_PASSWORD', '')

    redis_db: int = 0

    

    # HDFS

    hdfs_url: str = ENV_CONFIG.get('HDFS_DEFAULT_FS', 'hdfs://localhost:9000')

    hdfs_user: str = 'hadoop'

    

    # HBase

    hbase_host: str = ENV_CONFIG.get('HBASE_HOST', 'localhost')

    hbase_port: int = 9090

    

    # 本地存储（开发模式）

    local_storage_path: str = os.path.join(

        os.path.dirname(__file__), '..', 'data', 'storage'

    )





# ==================== HDFS存储客户端 ====================



class HDFSClient:

    """

    HDFS存储客户端

    

    支持：

    - Parquet格式存储

    - 分区策略（日期/话题/用户）

    - 数据压缩

    """

    

    # HDFS路径配置

    PATHS = {

        'raw_data': '/weibo/raw',

        'cleaned_data': '/weibo/cleaned',

        'features': '/weibo/features',

        'models': '/weibo/models',

        'checkpoints': '/weibo/checkpoints',

    }

    

    def __init__(self, config: StorageConfig):

        self.config = config

        self.hdfs_url = config.hdfs_url

        self._client = None

        self._use_local = True  # 默认使用本地存储

        

        # 尝试初始化HDFS客户端

        self._init_client()

    

    def _init_client(self):

        """初始化HDFS客户端"""

        try:

            # 尝试使用pyarrow的HDFS

            import pyarrow.fs as pafs

            self._client = pafs.HadoopFileSystem(self.hdfs_url)

            self._use_local = False

            logger.info(f"HDFS客户端初始化成功: {self.hdfs_url}")

        except Exception as e:

            logger.warning(f"HDFS不可用，使用本地存储: {e}")

            self._use_local = True

            # 创建本地存储目录

            os.makedirs(self.config.local_storage_path, exist_ok=True)

    

    def _get_local_path(self, hdfs_path: str) -> str:

        """获取本地存储路径"""

        # 将HDFS路径转换为本地路径

        local_path = os.path.join(

            self.config.local_storage_path,

            hdfs_path.lstrip('/')

        )

        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        return local_path

    

    def save_parquet(self, df, path: str, 

                     partition_by: List[str] = None,

                     mode: str = 'append',

                     compression: str = 'snappy') -> str:

        """

        保存DataFrame为Parquet格式

        

        Args:

            df: Spark DataFrame或Pandas DataFrame

            path: 存储路径

            partition_by: 分区列

            mode: 写入模式 (append/overwrite)

            compression: 压缩算法

            

        Returns:

            实际存储路径

        """

        full_path = f"{self.PATHS.get('raw_data', '')}{path}" if not path.startswith('/') else path

        

        if self._use_local:

            return self._save_parquet_local(df, full_path, partition_by, mode, compression)

        else:

            return self._save_parquet_hdfs(df, full_path, partition_by, mode, compression)

    

    def _save_parquet_local(self, df, path: str, partition_by: List[str],

                            mode: str, compression: str) -> str:

        """本地Parquet存储"""

        local_path = self._get_local_path(path)

        

        try:

            # 检查是否是Spark DataFrame

            if hasattr(df, 'write'):

                # Spark DataFrame

                writer = df.write.mode(mode)

                if partition_by:

                    writer = writer.partitionBy(*partition_by)

                writer.option("compression", compression).parquet(local_path)

            else:

                # Pandas DataFrame

                import pandas as pd

                if partition_by:

                    # 简单分区实现

                    for _, group in df.groupby(partition_by):

                        partition_values = '_'.join([str(group[col].iloc[0]) for col in partition_by])

                        partition_path = os.path.join(local_path, partition_values)

                        os.makedirs(partition_path, exist_ok=True)

                        group.to_parquet(

                            os.path.join(partition_path, f'data_{int(time.time())}.parquet'),

                            compression=compression

                        )

                else:

                    os.makedirs(os.path.dirname(local_path), exist_ok=True)

                    df.to_parquet(local_path, compression=compression)

            

            logger.info(f"Parquet保存成功: {local_path}")

            return local_path

            

        except Exception as e:

            logger.error(f"Parquet保存失败: {e}")

            raise

    

    def _save_parquet_hdfs(self, df, path: str, partition_by: List[str],

                           mode: str, compression: str) -> str:

        """HDFS Parquet存储"""

        hdfs_path = f"{self.hdfs_url}{path}"

        

        try:

            if hasattr(df, 'write'):

                # Spark DataFrame

                writer = df.write.mode(mode)

                if partition_by:

                    writer = writer.partitionBy(*partition_by)

                writer.option("compression", compression).parquet(hdfs_path)

            else:

                # 先保存到本地，再上传

                import tempfile

                with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:

                    df.to_parquet(tmp.name, compression=compression)

                    # 上传到HDFS

                    self._client.copy_from_local(tmp.name, path)

                    os.unlink(tmp.name)

            

            logger.info(f"HDFS Parquet保存成功: {hdfs_path}")

            return hdfs_path

            

        except Exception as e:

            logger.error(f"HDFS保存失败: {e}")

            raise

    

    def read_parquet(self, path: str, spark=None):

        """读取Parquet文件"""

        if self._use_local:

            local_path = self._get_local_path(path)

            if spark:

                return spark.read.parquet(local_path)

            else:

                import pandas as pd

                return pd.read_parquet(local_path)

        else:

            hdfs_path = f"{self.hdfs_url}{path}"

            if spark:

                return spark.read.parquet(hdfs_path)

            else:

                import pandas as pd

                return pd.read_parquet(hdfs_path)

    

    def list_files(self, path: str) -> List[str]:

        """列出目录下的文件"""

        if self._use_local:

            local_path = self._get_local_path(path)

            if os.path.exists(local_path):

                return os.listdir(local_path)

            return []

        else:

            try:

                return [f.path for f in self._client.get_file_info(

                    self._client.get_file_info(path).path

                )]

            except:

                return []

    

    def delete(self, path: str, recursive: bool = True):

        """删除文件或目录"""

        if self._use_local:

            local_path = self._get_local_path(path)

            if os.path.exists(local_path):

                import shutil

                if os.path.isdir(local_path):

                    shutil.rmtree(local_path)

                else:

                    os.remove(local_path)

        else:

            self._client.delete_file(path)

    

    def exists(self, path: str) -> bool:

        """检查路径是否存在"""

        if self._use_local:

            return os.path.exists(self._get_local_path(path))

        else:

            try:

                self._client.get_file_info(path)

                return True

            except:

                return False





# ==================== HBase存储客户端 ====================



class HBaseClient:

    """

    HBase存储客户端

    

    表结构设计：

    - weibo_raw: 原始微博数据

    - weibo_cleaned: 清洗后数据

    - user_profiles: 用户画像

    - hot_topics: 热点话题

    

    RowKey设计：时间戳反转 + 用户ID/话题ID

    """

    

    # 表结构定义

    TABLES = {

        'weibo_raw': {

            'cf_basic': ['id', 'mid', 'text', 'source', 'created_at'],

            'cf_user': ['user_id', 'user_name', 'user_verified'],

            'cf_stats': ['reposts_count', 'comments_count', 'attitudes_count'],

            'cf_media': ['pics', 'video_url'],

        },

        'weibo_cleaned': {

            'cf_basic': ['id', 'cleaned_text', 'tokens'],

            'cf_features': ['tfidf', 'word2vec', 'sentiment_score'],

            'cf_meta': ['keyword', 'topic', 'crawl_time'],

        },

        'user_profiles': {

            'cf_basic': ['user_id', 'screen_name', 'description', 'location'],

            'cf_stats': ['followers_count', 'friends_count', 'statuses_count'],

            'cf_analysis': ['sentiment_avg', 'activity_score', 'influence_score'],

        },

        'hot_topics': {

            'cf_basic': ['topic', 'hot_value', 'category'],

            'cf_stats': ['weibo_count', 'user_count', 'sentiment_distribution'],

            'cf_trend': ['hourly_trend', 'daily_trend'],

        },

    }

    

    def __init__(self, config: StorageConfig):

        self.config = config

        self._connection = None

        self._use_local = True

        

        self._init_connection()

    

    def _init_connection(self):

        """初始化HBase连接"""

        try:

            import happybase

            self._connection = happybase.Connection(

                host=self.config.hbase_host,

                port=self.config.hbase_port

            )

            self._use_local = False

            logger.info(f"HBase连接成功: {self.config.hbase_host}:{self.config.hbase_port}")

        except Exception as e:

            logger.warning(f"HBase不可用，使用本地JSON存储: {e}")

            self._use_local = True

            self._local_data = {}

            self._local_path = os.path.join(

                self.config.local_storage_path, 'hbase_local'

            )

            os.makedirs(self._local_path, exist_ok=True)

            self._load_local_data()

    

    def _load_local_data(self):

        """加载本地数据"""

        for table_name in self.TABLES.keys():

            file_path = os.path.join(self._local_path, f'{table_name}.json')

            if os.path.exists(file_path):

                try:

                    with open(file_path, 'r', encoding='utf-8') as f:

                        self._local_data[table_name] = json.load(f)

                except:

                    self._local_data[table_name] = {}

            else:

                self._local_data[table_name] = {}

    

    def _save_local_data(self, table_name: str):

        """保存本地数据"""

        file_path = os.path.join(self._local_path, f'{table_name}.json')

        with open(file_path, 'w', encoding='utf-8') as f:

            json.dump(self._local_data.get(table_name, {}), f, ensure_ascii=False, indent=2)

    

    @staticmethod

    def generate_rowkey(timestamp: datetime = None, entity_id: str = '') -> str:

        """

        生成RowKey

        

        格式：反转时间戳_实体ID

        反转时间戳确保最新数据在前

        """

        if timestamp is None:

            timestamp = datetime.now()

        

        # 时间戳反转（使用最大时间戳减去当前时间戳）

        max_ts = 9999999999999  # 13位时间戳最大值

        current_ts = int(timestamp.timestamp() * 1000)

        reversed_ts = max_ts - current_ts

        

        # 组合RowKey

        if entity_id:

            return f"{reversed_ts}_{entity_id}"

        return str(reversed_ts)

    

    def put(self, table_name: str, rowkey: str, data: Dict[str, Any]):

        """

        写入数据

        

        Args:

            table_name: 表名

            rowkey: 行键

            data: 数据字典 {列族:列名: 值}

        """

        if self._use_local:

            if table_name not in self._local_data:

                self._local_data[table_name] = {}

            self._local_data[table_name][rowkey] = data

            self._save_local_data(table_name)

        else:

            table = self._connection.table(table_name)

            # 转换数据格式

            hbase_data = {}

            for key, value in data.items():

                if isinstance(value, (dict, list)):

                    value = json.dumps(value, ensure_ascii=False)

                elif not isinstance(value, bytes):

                    value = str(value)

                hbase_data[key.encode()] = value.encode() if isinstance(value, str) else value

            table.put(rowkey.encode(), hbase_data)

    

    def batch_put(self, table_name: str, rows: List[Dict]):

        """

        批量写入

        

        Args:

            table_name: 表名

            rows: 数据列表 [{'rowkey': ..., 'data': {...}}, ...]

        """

        if self._use_local:

            if table_name not in self._local_data:

                self._local_data[table_name] = {}

            for row in rows:

                self._local_data[table_name][row['rowkey']] = row['data']

            self._save_local_data(table_name)

        else:

            table = self._connection.table(table_name)

            with table.batch(batch_size=1000) as batch:

                for row in rows:

                    hbase_data = {}

                    for key, value in row['data'].items():

                        if isinstance(value, (dict, list)):

                            value = json.dumps(value, ensure_ascii=False)

                        elif not isinstance(value, bytes):

                            value = str(value)

                        hbase_data[key.encode()] = value.encode() if isinstance(value, str) else value

                    batch.put(row['rowkey'].encode(), hbase_data)

    

    def get(self, table_name: str, rowkey: str) -> Optional[Dict]:

        """获取单行数据"""

        if self._use_local:

            return self._local_data.get(table_name, {}).get(rowkey)

        else:

            table = self._connection.table(table_name)

            row = table.row(rowkey.encode())

            if row:

                return {k.decode(): v.decode() for k, v in row.items()}

            return None

    

    def scan(self, table_name: str, 

             row_start: str = None, 

             row_stop: str = None,

             limit: int = 100,

             filter_str: str = None) -> List[Dict]:

        """

        扫描表

        

        Args:

            table_name: 表名

            row_start: 起始行键

            row_stop: 结束行键

            limit: 返回数量限制

            filter_str: 过滤条件

            

        Returns:

            数据列表

        """

        if self._use_local:

            data = self._local_data.get(table_name, {})

            results = []

            for rowkey, row_data in sorted(data.items()):

                if row_start and rowkey < row_start:

                    continue

                if row_stop and rowkey >= row_stop:

                    break

                results.append({'rowkey': rowkey, 'data': row_data})

                if len(results) >= limit:

                    break

            return results

        else:

            table = self._connection.table(table_name)

            results = []

            for key, data in table.scan(

                row_start=row_start.encode() if row_start else None,

                row_stop=row_stop.encode() if row_stop else None,

                limit=limit,

                filter=filter_str

            ):

                results.append({

                    'rowkey': key.decode(),

                    'data': {k.decode(): v.decode() for k, v in data.items()}

                })

            return results

    

    def delete(self, table_name: str, rowkey: str):

        """删除行"""

        if self._use_local:

            if table_name in self._local_data and rowkey in self._local_data[table_name]:

                del self._local_data[table_name][rowkey]

                self._save_local_data(table_name)

        else:

            table = self._connection.table(table_name)

            table.delete(rowkey.encode())

    

    def create_table(self, table_name: str, column_families: List[str] = None):

        """创建表"""

        if self._use_local:

            if table_name not in self._local_data:

                self._local_data[table_name] = {}

        else:

            if column_families is None:

                column_families = list(self.TABLES.get(table_name, {}).keys())

            

            families = {cf: dict() for cf in column_families}

            self._connection.create_table(table_name, families)

    

    def close(self):

        """关闭连接"""

        if self._connection:

            self._connection.close()





# ==================== MySQL存储客户端 ====================



class MySQLClient:

    """

    MySQL存储客户端

    

    管理：

    - 任务管理表

    - 用户配置表

    - 系统日志表

    - 模型元数据表

    """

    

    def __init__(self, config: StorageConfig):

        self.config = config

        self._connection = None

        self._pool = None

        self._use_sqlite = True

        

        self._init_connection()

    

    def _init_connection(self):

        """初始化数据库连接"""

        try:

            import pymysql

            from dbutils.pooled_db import PooledDB

            

            self._pool = PooledDB(

                creator=pymysql,

                maxconnections=10,

                mincached=2,

                host=self.config.mysql_host,

                port=self.config.mysql_port,

                user=self.config.mysql_user,

                password=self.config.mysql_password,

                database=self.config.mysql_database,

                charset='utf8mb4',

                cursorclass=pymysql.cursors.DictCursor

            )

            self._use_sqlite = False

            logger.info(f"MySQL连接池初始化成功: {self.config.mysql_host}")

        except Exception as e:

            logger.warning(f"MySQL不可用，使用SQLite: {e}")

            self._use_sqlite = True

            self._init_sqlite()

    

    def _init_sqlite(self):

        """初始化SQLite（开发模式）"""

        import sqlite3

        

        db_path = os.path.join(self.config.local_storage_path, 'weibo.db')

        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        

        self._sqlite_path = db_path

        

        # 创建表

        conn = sqlite3.connect(db_path)

        cursor = conn.cursor()

        

        # 任务表

        cursor.execute('''

            CREATE TABLE IF NOT EXISTS collection_tasks (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                task_id TEXT UNIQUE NOT NULL,

                name TEXT NOT NULL,

                type TEXT NOT NULL,

                status TEXT DEFAULT 'pending',

                progress REAL DEFAULT 0,

                params TEXT,

                result_count INTEGER DEFAULT 0,

                error_message TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

            )

        ''')

        

        # 模型元数据表

        cursor.execute('''

            CREATE TABLE IF NOT EXISTS model_metadata (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                model_id TEXT UNIQUE NOT NULL,

                model_name TEXT NOT NULL,

                model_type TEXT NOT NULL,

                version TEXT,

                path TEXT,

                metrics TEXT,

                status TEXT DEFAULT 'active',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

            )

        ''')

        

        # 系统日志表

        cursor.execute('''

            CREATE TABLE IF NOT EXISTS system_logs (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                level TEXT NOT NULL,

                module TEXT,

                message TEXT,

                details TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

            )

        ''')

        

        # 用户配置表

        cursor.execute('''

            CREATE TABLE IF NOT EXISTS user_configs (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id TEXT NOT NULL,

                config_key TEXT NOT NULL,

                config_value TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(user_id, config_key)

            )

        ''')

        

        conn.commit()

        conn.close()

        logger.info(f"SQLite初始化成功: {db_path}")

    

    @contextmanager

    def get_connection(self):

        """获取数据库连接"""

        if self._use_sqlite:

            import sqlite3

            conn = sqlite3.connect(self._sqlite_path)

            conn.row_factory = sqlite3.Row

            try:

                yield conn

                conn.commit()

            finally:

                conn.close()

        else:

            conn = self._pool.connection()

            try:

                yield conn

                conn.commit()

            finally:

                conn.close()

    

    def execute(self, sql: str, params: tuple = None) -> int:

        """执行SQL语句"""

        with self.get_connection() as conn:

            cursor = conn.cursor()

            cursor.execute(sql, params or ())

            return cursor.lastrowid

    

    def query(self, sql: str, params: tuple = None) -> List[Dict]:

        """查询数据"""

        with self.get_connection() as conn:

            cursor = conn.cursor()

            cursor.execute(sql, params or ())

            rows = cursor.fetchall()

            if self._use_sqlite:

                return [dict(row) for row in rows]

            return rows

    

    def query_one(self, sql: str, params: tuple = None) -> Optional[Dict]:

        """查询单条数据"""

        results = self.query(sql, params)

        return results[0] if results else None

    

    # ==================== 任务管理 ====================

    

    def insert_task(self, task_data: Dict) -> int:

        """插入任务"""

        sql = '''

            INSERT INTO collection_tasks 

            (task_id, name, type, status, params)

            VALUES (?, ?, ?, ?, ?)

        ''' if self._use_sqlite else '''

            INSERT INTO collection_tasks 

            (task_id, name, type, status, params)

            VALUES (%s, %s, %s, %s, %s)

        '''

        

        return self.execute(sql, (

            task_data.get('task_id'),

            task_data.get('name'),

            task_data.get('type'),

            task_data.get('status', 'pending'),

            json.dumps(task_data.get('params', {}))

        ))

    

    def update_task(self, task_id: str, updates: Dict):

        """更新任务"""

        set_clause = ', '.join([f"{k} = ?" if self._use_sqlite else f"{k} = %s" 

                                for k in updates.keys()])

        sql = f'''

            UPDATE collection_tasks 

            SET {set_clause}, updated_at = CURRENT_TIMESTAMP

            WHERE task_id = {"?" if self._use_sqlite else "%s"}

        '''

        

        params = list(updates.values()) + [task_id]

        self.execute(sql, tuple(params))

    

    def get_task(self, task_id: str) -> Optional[Dict]:

        """获取任务"""

        sql = f'''

            SELECT * FROM collection_tasks 

            WHERE task_id = {"?" if self._use_sqlite else "%s"}

        '''

        return self.query_one(sql, (task_id,))

    

    def list_tasks(self, status: str = None, limit: int = 100) -> List[Dict]:

        """列出任务"""

        if status:

            sql = f'''

                SELECT * FROM collection_tasks 

                WHERE status = {"?" if self._use_sqlite else "%s"}

                ORDER BY created_at DESC

                LIMIT {"?" if self._use_sqlite else "%s"}

            '''

            return self.query(sql, (status, limit))

        else:

            sql = f'''

                SELECT * FROM collection_tasks 

                ORDER BY created_at DESC

                LIMIT {"?" if self._use_sqlite else "%s"}

            '''

            return self.query(sql, (limit,))

    

    # ==================== 模型元数据 ====================

    

    def save_model_metadata(self, model_data: Dict) -> int:

        """保存模型元数据"""

        sql = '''

            INSERT OR REPLACE INTO model_metadata 

            (model_id, model_name, model_type, version, path, metrics, status)

            VALUES (?, ?, ?, ?, ?, ?, ?)

        ''' if self._use_sqlite else '''

            INSERT INTO model_metadata 

            (model_id, model_name, model_type, version, path, metrics, status)

            VALUES (%s, %s, %s, %s, %s, %s, %s)

            ON DUPLICATE KEY UPDATE

            model_name = VALUES(model_name),

            version = VALUES(version),

            path = VALUES(path),

            metrics = VALUES(metrics),

            status = VALUES(status),

            updated_at = CURRENT_TIMESTAMP

        '''

        

        return self.execute(sql, (

            model_data.get('model_id'),

            model_data.get('model_name'),

            model_data.get('model_type'),

            model_data.get('version'),

            model_data.get('path'),

            json.dumps(model_data.get('metrics', {})),

            model_data.get('status', 'active')

        ))

    

    def get_model_metadata(self, model_id: str) -> Optional[Dict]:

        """获取模型元数据"""

        sql = f'''

            SELECT * FROM model_metadata 

            WHERE model_id = {"?" if self._use_sqlite else "%s"}

        '''

        return self.query_one(sql, (model_id,))

    

    # ==================== 系统日志 ====================

    

    def log(self, level: str, module: str, message: str, details: Dict = None):

        """记录系统日志"""

        sql = '''

            INSERT INTO system_logs (level, module, message, details)

            VALUES (?, ?, ?, ?)

        ''' if self._use_sqlite else '''

            INSERT INTO system_logs (level, module, message, details)

            VALUES (%s, %s, %s, %s)

        '''

        

        self.execute(sql, (

            level,

            module,

            message,

            json.dumps(details) if details else None

        ))

    

    def get_logs(self, level: str = None, 

                 module: str = None,

                 limit: int = 100) -> List[Dict]:

        """获取系统日志"""

        conditions = []

        params = []

        

        if level:

            conditions.append(f"level = {'?' if self._use_sqlite else '%s'}")

            params.append(level)

        if module:

            conditions.append(f"module = {'?' if self._use_sqlite else '%s'}")

            params.append(module)

        

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        

        sql = f'''

            SELECT * FROM system_logs 

            {where_clause}

            ORDER BY created_at DESC

            LIMIT {"?" if self._use_sqlite else "%s"}

        '''

        params.append(limit)

        

        return self.query(sql, tuple(params))





# ==================== Redis缓存客户端 ====================



class RedisClient:

    """

    Redis缓存客户端

    

    功能：

    - 热点数据缓存

    - 会话管理

    - 实时计算中间结果

    - 分布式锁

    """

    

    # 缓存键前缀

    KEY_PREFIX = {

        'hot_search': 'weibo:hot_search',

        'hot_topic': 'weibo:hot_topic:',

        'user_session': 'session:',

        'task_progress': 'task:progress:',

        'cache': 'cache:',

        'lock': 'lock:',

        'rate_limit': 'rate_limit:',

    }

    

    # 默认过期时间（秒）

    DEFAULT_EXPIRE = {

        'hot_search': 300,      # 5分钟

        'hot_topic': 600,       # 10分钟

        'user_session': 3600,   # 1小时

        'task_progress': 86400, # 1天

        'cache': 3600,          # 1小时

    }

    

    def __init__(self, config: StorageConfig):

        self.config = config

        self._client = None

        self._use_local = True

        self._local_cache = {}

        self._local_expire = {}

        self._lock = threading.Lock()

        

        self._init_client()

    

    def _init_client(self):

        """初始化Redis客户端"""

        try:

            import redis

            self._client = redis.Redis(

                host=self.config.redis_host,

                port=self.config.redis_port,

                password=self.config.redis_password or None,

                db=self.config.redis_db,

                decode_responses=True

            )

            # 测试连接

            self._client.ping()

            self._use_local = False

            logger.info(f"Redis连接成功: {self.config.redis_host}:{self.config.redis_port}")

        except Exception as e:

            logger.warning(f"Redis不可用，使用本地缓存: {e}")

            self._use_local = True

    

    def _check_expire(self, key: str) -> bool:

        """检查本地缓存是否过期"""

        if key in self._local_expire:

            if time.time() > self._local_expire[key]:

                del self._local_cache[key]

                del self._local_expire[key]

                return True

        return False

    

    def set(self, key: str, value: Any, expire: int = None):

        """设置缓存"""

        if isinstance(value, (dict, list)):

            value = json.dumps(value, ensure_ascii=False)

        

        if self._use_local:

            with self._lock:

                self._local_cache[key] = value

                if expire:

                    self._local_expire[key] = time.time() + expire

        else:

            if expire:

                self._client.setex(key, expire, value)

            else:

                self._client.set(key, value)

    

    def get(self, key: str) -> Optional[str]:

        """获取缓存"""

        if self._use_local:

            with self._lock:

                self._check_expire(key)

                return self._local_cache.get(key)

        else:

            return self._client.get(key)

    

    def get_json(self, key: str) -> Optional[Any]:

        """获取JSON缓存"""

        value = self.get(key)

        if value:

            try:

                return json.loads(value)

            except:

                return value

        return None

    

    def delete(self, key: str):

        """删除缓存"""

        if self._use_local:

            with self._lock:

                self._local_cache.pop(key, None)

                self._local_expire.pop(key, None)

        else:

            self._client.delete(key)

    

    def exists(self, key: str) -> bool:

        """检查键是否存在"""

        if self._use_local:

            with self._lock:

                self._check_expire(key)

                return key in self._local_cache

        else:

            return self._client.exists(key)

    

    def expire(self, key: str, seconds: int):

        """设置过期时间"""

        if self._use_local:

            with self._lock:

                if key in self._local_cache:

                    self._local_expire[key] = time.time() + seconds

        else:

            self._client.expire(key, seconds)

    

    def incr(self, key: str, amount: int = 1) -> int:

        """递增"""

        if self._use_local:

            with self._lock:

                current = int(self._local_cache.get(key, 0))

                self._local_cache[key] = str(current + amount)

                return current + amount

        else:

            return self._client.incr(key, amount)

    

    # ==================== 热点数据缓存 ====================

    

    def cache_hot_search(self, hot_list: List[Dict], expire: int = None):

        """缓存热搜榜"""

        key = self.KEY_PREFIX['hot_search']

        expire = expire or self.DEFAULT_EXPIRE['hot_search']

        self.set(key, hot_list, expire)

        logger.debug(f"缓存热搜榜: {len(hot_list)} 条")

    

    def get_hot_search(self) -> Optional[List[Dict]]:

        """获取热搜榜缓存"""

        key = self.KEY_PREFIX['hot_search']

        return self.get_json(key)

    

    def cache_topic_data(self, topic: str, data: Dict, expire: int = None):

        """缓存话题数据"""

        key = f"{self.KEY_PREFIX['hot_topic']}{topic}"

        expire = expire or self.DEFAULT_EXPIRE['hot_topic']

        self.set(key, data, expire)

    

    def get_topic_data(self, topic: str) -> Optional[Dict]:

        """获取话题数据缓存"""

        key = f"{self.KEY_PREFIX['hot_topic']}{topic}"

        return self.get_json(key)

    

    # ==================== 会话管理 ====================

    

    def set_session(self, session_id: str, data: Dict, expire: int = None):

        """设置会话"""

        key = f"{self.KEY_PREFIX['user_session']}{session_id}"

        expire = expire or self.DEFAULT_EXPIRE['user_session']

        self.set(key, data, expire)

    

    def get_session(self, session_id: str) -> Optional[Dict]:

        """获取会话"""

        key = f"{self.KEY_PREFIX['user_session']}{session_id}"

        return self.get_json(key)

    

    def delete_session(self, session_id: str):

        """删除会话"""

        key = f"{self.KEY_PREFIX['user_session']}{session_id}"

        self.delete(key)

    

    # ==================== 任务进度 ====================

    

    def set_task_progress(self, task_id: str, progress: Dict):

        """设置任务进度"""

        key = f"{self.KEY_PREFIX['task_progress']}{task_id}"

        self.set(key, progress, self.DEFAULT_EXPIRE['task_progress'])

    

    def get_task_progress(self, task_id: str) -> Optional[Dict]:

        """获取任务进度"""

        key = f"{self.KEY_PREFIX['task_progress']}{task_id}"

        return self.get_json(key)

    

    # ==================== 分布式锁 ====================

    

    def acquire_lock(self, lock_name: str, 

                     expire: int = 30,

                     retry: int = 3,

                     retry_delay: float = 0.1) -> bool:

        """

        获取分布式锁

        

        Args:

            lock_name: 锁名称

            expire: 锁过期时间（秒）

            retry: 重试次数

            retry_delay: 重试间隔（秒）

            

        Returns:

            是否获取成功

        """

        key = f"{self.KEY_PREFIX['lock']}{lock_name}"

        

        for _ in range(retry):

            if self._use_local:

                with self._lock:

                    self._check_expire(key)

                    if key not in self._local_cache:

                        self._local_cache[key] = '1'

                        self._local_expire[key] = time.time() + expire

                        return True

            else:

                if self._client.set(key, '1', ex=expire, nx=True):

                    return True

            

            time.sleep(retry_delay)

        

        return False

    

    def release_lock(self, lock_name: str):

        """释放分布式锁"""

        key = f"{self.KEY_PREFIX['lock']}{lock_name}"

        self.delete(key)

    

    @contextmanager

    def lock(self, lock_name: str, expire: int = 30):

        """分布式锁上下文管理器"""

        acquired = self.acquire_lock(lock_name, expire)

        if not acquired:

            raise RuntimeError(f"无法获取锁: {lock_name}")

        try:

            yield

        finally:

            self.release_lock(lock_name)

    

    # ==================== 限流 ====================

    

    def check_rate_limit(self, key: str, 

                         max_requests: int,

                         window_seconds: int) -> bool:

        """

        检查限流

        

        Args:

            key: 限流键（如用户ID、IP）

            max_requests: 窗口内最大请求数

            window_seconds: 时间窗口（秒）

            

        Returns:

            True 如果允许请求，False 如果被限流

        """

        rate_key = f"{self.KEY_PREFIX['rate_limit']}{key}"

        

        current = self.incr(rate_key)

        

        if current == 1:

            self.expire(rate_key, window_seconds)

        

        return current <= max_requests





# ==================== 统一存储服务 ====================



class StorageService:

    """

    统一存储服务

    

    整合HDFS、HBase、MySQL、Redis的统一接口

    """

    

    def __init__(self, config: StorageConfig = None):

        """

        初始化存储服务

        

        Args:

            config: 存储配置，为None时使用默认配置

        """

        self.config = config or StorageConfig()

        

        # 初始化各存储客户端

        self.hdfs = HDFSClient(self.config)

        self.hbase = HBaseClient(self.config)

        self.mysql = MySQLClient(self.config)

        self.redis = RedisClient(self.config)

        

        logger.info("StorageService初始化完成")

    

    # ==================== 便捷方法 ====================

    

    def store_weibo_raw(self, df, date: str = None):

        """存储原始微博数据"""

        date = date or datetime.now().strftime('%Y-%m-%d')

        path = f"/weibo/raw/date={date}"

        return self.hdfs.save_parquet(df, path, partition_by=['date'])

    

    def store_weibo_cleaned(self, df, date: str = None):

        """存储清洗后的微博数据"""

        date = date or datetime.now().strftime('%Y-%m-%d')

        path = f"/weibo/cleaned/date={date}"

        return self.hdfs.save_parquet(df, path, partition_by=['date'])

    

    def store_features(self, df, feature_type: str, date: str = None):

        """存储特征向量"""

        date = date or datetime.now().strftime('%Y-%m-%d')

        path = f"/weibo/features/{feature_type}/date={date}"

        return self.hdfs.save_parquet(df, path)

    

    def cache_and_store_hot_search(self, hot_list: List[Dict]):

        """缓存并存储热搜榜"""

        # 缓存到Redis

        self.redis.cache_hot_search(hot_list)

        

        # 存储到HBase

        timestamp = datetime.now()

        rows = []

        for item in hot_list:

            rowkey = self.hbase.generate_rowkey(timestamp, str(item.get('rank', '')))

            rows.append({

                'rowkey': rowkey,

                'data': {

                    'cf_basic:title': item.get('title', ''),

                    'cf_basic:hot_value': str(item.get('hot_value', 0)),

                    'cf_basic:category': item.get('category', ''),

                    'cf_stats:crawl_time': timestamp.isoformat(),

                }

            })

        

        self.hbase.batch_put('hot_topics', rows)

        logger.info(f"热搜榜存储完成: {len(hot_list)} 条")

    

    def get_hot_search_cached(self) -> Optional[List[Dict]]:

        """获取热搜榜（优先从缓存）"""

        # 先查缓存

        cached = self.redis.get_hot_search()

        if cached:

            return cached

        

        # 从HBase查询最新数据

        results = self.hbase.scan('hot_topics', limit=50)

        if results:

            hot_list = []

            for row in results:

                data = row.get('data', {})

                hot_list.append({

                    'rank': len(hot_list) + 1,

                    'title': data.get('cf_basic:title', ''),

                    'hot_value': int(data.get('cf_basic:hot_value', 0)),

                    'category': data.get('cf_basic:category', ''),

                })

            

            # 更新缓存

            self.redis.cache_hot_search(hot_list)

            return hot_list

        

        return None

    

    def create_task(self, task_data: Dict) -> str:

        """创建采集任务"""

        import uuid

        task_id = task_data.get('task_id') or str(uuid.uuid4())

        task_data['task_id'] = task_id

        

        # 存储到MySQL

        self.mysql.insert_task(task_data)

        

        # 初始化进度缓存

        self.redis.set_task_progress(task_id, {

            'status': 'pending',

            'progress': 0,

            'created_at': datetime.now().isoformat()

        })

        

        return task_id

    

    def update_task_progress(self, task_id: str, progress: float, status: str = None):

        """更新任务进度"""

        # 更新Redis缓存

        progress_data = self.redis.get_task_progress(task_id) or {}

        progress_data['progress'] = progress

        if status:

            progress_data['status'] = status

        progress_data['updated_at'] = datetime.now().isoformat()

        self.redis.set_task_progress(task_id, progress_data)

        

        # 更新MySQL

        updates = {'progress': progress}

        if status:

            updates['status'] = status

        self.mysql.update_task(task_id, updates)

    

    def get_stats(self) -> Dict:

        """获取存储服务统计信息"""

        return {

            'hdfs': {

                'use_local': self.hdfs._use_local,

                'url': self.hdfs.hdfs_url if not self.hdfs._use_local else self.config.local_storage_path

            },

            'hbase': {

                'use_local': self.hbase._use_local,

                'tables': list(self.hbase.TABLES.keys())

            },

            'mysql': {

                'use_sqlite': self.mysql._use_sqlite,

                'host': self.config.mysql_host if not self.mysql._use_sqlite else 'sqlite'

            },

            'redis': {

                'use_local': self.redis._use_local,

                'host': self.config.redis_host if not self.redis._use_local else 'local'

            }

        }

    

    def close(self):

        """关闭所有连接"""

        self.hbase.close()

        logger.info("存储服务连接已关闭")





# ==================== 便捷函数 ====================



_storage_instance = None



def get_storage_service() -> StorageService:

    """获取存储服务单例"""

    global _storage_instance

    if _storage_instance is None:

        _storage_instance = StorageService()

    return _storage_instance





def cache_decorator(key_prefix: str, expire: int = 3600):

    """缓存装饰器"""

    def decorator(func):

        @wraps(func)

        def wrapper(*args, **kwargs):

            storage = get_storage_service()

            

            # 生成缓存键

            cache_key = f"{key_prefix}:{hashlib.md5(str(args).encode() + str(kwargs).encode()).hexdigest()}"

            

            # 尝试从缓存获取

            cached = storage.redis.get_json(cache_key)

            if cached is not None:

                return cached

            

            # 执行函数

            result = func(*args, **kwargs)

            

            # 存入缓存

            if result is not None:

                storage.redis.set(cache_key, result, expire)

            

            return result

        return wrapper

    return decorator





# ==================== 命令行入口 ====================



if __name__ == '__main__':

    # 测试存储服务

    storage = StorageService()

    

    print("存储服务状态:")

    stats = storage.get_stats()

    for service, info in stats.items():

        print(f"  {service}: {info}")

    

    # 测试Redis

    print("\n测试Redis缓存:")

    storage.redis.set('test_key', {'hello': 'world'}, 60)

    print(f"  设置: test_key = {{'hello': 'world'}}")

    print(f"  获取: {storage.redis.get_json('test_key')}")

    

    # 测试MySQL

    print("\n测试MySQL:")

    task_id = storage.create_task({

        'name': '测试任务',

        'type': 'keyword_search',

        'params': {'keyword': '人工智能'}

    })

    print(f"  创建任务: {task_id}")

    task = storage.mysql.get_task(task_id)

    print(f"  查询任务: {task}")

    

    storage.close()

