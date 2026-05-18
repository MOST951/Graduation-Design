"""

数据存储服务模块

================



提供两种存储后端的统一接口：

1. MySQL存储：全部业务数据、分析结果、用户信息、配置、任务管理

2. HDFS存储：原始微博数据文件（JSON）和Spark中间处理结果（Parquet）



使用示例:

    from backend.services.storage_service import StorageService

    

    storage = StorageService()

    

    # HDFS存储

    storage.hdfs.save_parquet(df, '/weibo/raw', partition_by=['date'])

    

    # MySQL操作

    storage.mysql.insert_task(task_data)

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

                'HDFS_DEFAULT_FS']:

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

    

    # HDFS

    hdfs_url: str = ENV_CONFIG.get('HDFS_DEFAULT_FS', 'hdfs://localhost:9000')

    hdfs_user: str = 'hadoop'

    

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





# ==================== 内存缓存（替代 Redis） ====================



class MemoryCache:

    """

    应用层内存缓存（替代 Redis）

    

    功能：

    - 热点数据缓存（TTL 自动过期）

    - 通用 KV 缓存

    """

    

    def __init__(self, max_size: int = 1024):

        self._cache: Dict[str, Any] = {}

        self._expire: Dict[str, float] = {}

        self._lock = threading.Lock()

        self._max_size = max_size

    

    def _evict_expired(self):

        """清除过期键"""

        now = time.time()

        expired = [k for k, v in self._expire.items() if now > v]

        for k in expired:

            self._cache.pop(k, None)

            self._expire.pop(k, None)

    

    def set(self, key: str, value: Any, expire: int = None):

        """设置缓存"""

        if isinstance(value, (dict, list)):

            value = json.dumps(value, ensure_ascii=False)

        with self._lock:

            self._evict_expired()

            if len(self._cache) >= self._max_size:

                oldest = next(iter(self._cache))

                self._cache.pop(oldest, None)

                self._expire.pop(oldest, None)

            self._cache[key] = value

            if expire:

                self._expire[key] = time.time() + expire

    

    def get(self, key: str) -> Optional[str]:

        """获取缓存"""

        with self._lock:

            if key in self._expire and time.time() > self._expire[key]:

                self._cache.pop(key, None)

                self._expire.pop(key, None)

                return None

            return self._cache.get(key)

    

    def get_json(self, key: str) -> Optional[Any]:

        """获取JSON缓存"""

        value = self.get(key)

        if value:

            try:

                return json.loads(value)

            except Exception:

                return value

        return None

    

    def delete(self, key: str):

        """删除缓存"""

        with self._lock:

            self._cache.pop(key, None)

            self._expire.pop(key, None)





# ==================== 统一存储服务 ====================



class StorageService:

    """

    统一存储服务

    

    整合 MySQL + HDFS + 内存缓存的统一接口

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

        self.mysql = MySQLClient(self.config)

        self.cache = MemoryCache()

        

        logger.info("StorageService初始化完成 (MySQL + HDFS + MemoryCache)")

    

    # ==================== 便捷方法 ====================

    

    def store_weibo_raw(self, df, date: str = None):

        """存储原始微博数据到HDFS"""

        date = date or datetime.now().strftime('%Y-%m-%d')

        path = f"/weibo/raw/date={date}"

        return self.hdfs.save_parquet(df, path, partition_by=['date'])

    

    def store_weibo_cleaned(self, df, date: str = None):

        """存储清洗后的微博数据到HDFS"""

        date = date or datetime.now().strftime('%Y-%m-%d')

        path = f"/weibo/cleaned/date={date}"

        return self.hdfs.save_parquet(df, path, partition_by=['date'])

    

    def store_features(self, df, feature_type: str, date: str = None):

        """存储特征向量到HDFS"""

        date = date or datetime.now().strftime('%Y-%m-%d')

        path = f"/weibo/features/{feature_type}/date={date}"

        return self.hdfs.save_parquet(df, path)

    

    def create_task(self, task_data: Dict) -> str:

        """创建采集任务（存储到MySQL）"""

        import uuid

        task_id = task_data.get('task_id') or str(uuid.uuid4())

        task_data['task_id'] = task_id

        

        # 存储到MySQL

        self.mysql.insert_task(task_data)

        

        return task_id

    

    def update_task_progress(self, task_id: str, progress: float, status: str = None):

        """更新任务进度（MySQL）"""

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

            'mysql': {

                'use_sqlite': self.mysql._use_sqlite,

                'host': self.config.mysql_host if not self.mysql._use_sqlite else 'sqlite'

            },

            'cache': {

                'type': 'memory',

                'max_size': self.cache._max_size

            }

        }

    

    def close(self):

        """关闭所有连接"""

        logger.info("存储服务连接已关闭")





# ==================== 便捷函数 ====================



_storage_instance = None



def get_storage_service() -> StorageService:

    """获取存储服务单例"""

    global _storage_instance

    if _storage_instance is None:

        _storage_instance = StorageService()

    return _storage_instance



# 全局内存缓存实例（供 redis_cache 装饰器等使用）

_memory_cache = MemoryCache()



def get_memory_cache() -> MemoryCache:

    """获取全局内存缓存单例"""

    return _memory_cache



def cache_decorator(key_prefix: str, expire: int = 3600):

    """缓存装饰器（使用内存缓存替代 Redis）"""

    def decorator(func):

        @wraps(func)

        def wrapper(*args, **kwargs):

            # 生成缓存键

            cache_key = f"{key_prefix}:{hashlib.md5(str(args).encode() + str(kwargs).encode()).hexdigest()}"

            

            # 尝试从缓存获取

            cached = _memory_cache.get_json(cache_key)

            if cached is not None:

                return cached

            

            # 执行函数

            result = func(*args, **kwargs)

            

            # 存入缓存

            if result is not None:

                _memory_cache.set(cache_key, result, expire)

            

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

    

    # 测试内存缓存

    print("\n测试内存缓存:")

    storage.cache.set('test_key', {'hello': 'world'}, 60)

    print(f"  设置: test_key = {{'hello': 'world'}}")

    print(f"  获取: {storage.cache.get_json('test_key')}")

    

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

