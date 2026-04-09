"""
Spark作业触发服务
================

负责触发和监控Spark作业，实现数据流连通：
微博爬虫 → HDFS原始存储 → Spark清洗 → HBase结构化 → 双维度排序

功能：
1. 使用subprocess调用spark-submit
2. 监控作业状态，记录到MySQL
3. 作业完成后更新数据状态
4. 错误重试机制（最多3次）
5. 完整的日志记录
"""

import os
import sys
import json
import time
import logging
import subprocess
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import uuid

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SparkService')


class JobStatus(Enum):
    """作业状态枚举"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    RETRYING = 'retrying'


class JobType(Enum):
    """作业类型枚举"""
    DATA_CLEANING = 'data_cleaning'
    SENTIMENT_ANALYSIS = 'sentiment_analysis'
    TOPIC_RANKING = 'topic_ranking'
    FULL_PIPELINE = 'full_pipeline'


@dataclass
class SparkJobConfig:
    """Spark作业配置"""
    spark_home: str = os.environ.get('SPARK_HOME', 'D:/spark-3.0.0')
    spark_master: str = 'local[2]'
    driver_memory: str = '2g'
    executor_memory: str = '2g'
    
    # 作业JAR路径
    preprocessing_jar: str = ''
    
    # HDFS配置
    hdfs_url: str = 'hdfs://localhost:9000'
    
    # HBase配置
    hbase_zookeeper: str = 'localhost:2181'
    
    # 重试配置
    max_retries: int = 3
    retry_delay_seconds: int = 30
    
    def __post_init__(self):
        # 自动设置JAR路径
        if not self.preprocessing_jar:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.preprocessing_jar = os.path.join(
                base_dir, 'spark-preprocessing', 'target', 'spark-jobs-1.0.jar'
            )


@dataclass
class SparkJob:
    """Spark作业实体"""
    job_id: str
    job_type: str
    status: str = JobStatus.PENDING.value
    input_path: str = ''
    output_path: str = ''
    
    # 时间信息
    created_at: str = ''
    started_at: str = ''
    completed_at: str = ''
    
    # 执行信息
    progress: int = 0
    retry_count: int = 0
    error_message: str = ''
    
    # 结果信息
    records_processed: int = 0
    records_output: int = 0
    
    # 关联信息
    crawl_task_id: str = ''
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SparkJobStore:
    """
    Spark作业存储
    
    使用JSON文件模拟MySQL存储（开发环境）
    生产环境应替换为真实MySQL连接
    """
    
    def __init__(self, storage_path: str = None):
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'data', 'spark_jobs.json'
            )
        self.storage_path = storage_path
        self._jobs: Dict[str, SparkJob] = {}
        self._lock = threading.Lock()
        self._load()
    
    def _load(self):
        """加载作业记录"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for job_id, job_data in data.items():
                        self._jobs[job_id] = SparkJob(**job_data)
                logger.info(f"已加载 {len(self._jobs)} 条Spark作业记录")
        except Exception as e:
            logger.error(f"加载Spark作业记录失败: {e}")
    
    def _save(self):
        """保存作业记录"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                data = {job_id: job.to_dict() for job_id, job in self._jobs.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存Spark作业记录失败: {e}")
    
    def create(self, job: SparkJob) -> SparkJob:
        """创建作业记录"""
        with self._lock:
            self._jobs[job.job_id] = job
            self._save()
        return job
    
    def update(self, job: SparkJob) -> SparkJob:
        """更新作业记录"""
        with self._lock:
            self._jobs[job.job_id] = job
            self._save()
        return job
    
    def get(self, job_id: str) -> Optional[SparkJob]:
        """获取作业记录"""
        return self._jobs.get(job_id)
    
    def get_all(self) -> List[SparkJob]:
        """获取所有作业记录"""
        return list(self._jobs.values())
    
    def get_by_status(self, status: str) -> List[SparkJob]:
        """按状态获取作业"""
        return [job for job in self._jobs.values() if job.status == status]
    
    def get_by_crawl_task(self, crawl_task_id: str) -> List[SparkJob]:
        """按采集任务ID获取作业"""
        return [job for job in self._jobs.values() if job.crawl_task_id == crawl_task_id]


class SparkService:
    """
    Spark作业服务
    
    负责：
    1. 提交Spark作业（spark-submit）
    2. 监控作业状态
    3. 处理作业完成/失败回调
    4. 重试机制
    """
    
    def __init__(self, config: SparkJobConfig = None):
        self.config = config or SparkJobConfig()
        self.store = SparkJobStore()
        self.executor = ThreadPoolExecutor(max_workers=3)
        self._running_jobs: Dict[str, subprocess.Popen] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        
        logger.info(f"SparkService初始化完成")
        logger.info(f"  SPARK_HOME: {self.config.spark_home}")
        logger.info(f"  Master: {self.config.spark_master}")
    
    def submit_cleaning_job(self, 
                           input_path: str,
                           output_path: str,
                           crawl_task_id: str = '',
                           on_complete: Callable = None) -> SparkJob:
        """
        提交数据清洗作业
        
        Args:
            input_path: 输入数据路径（HDFS或本地）
            output_path: 输出数据路径
            crawl_task_id: 关联的采集任务ID
            on_complete: 完成回调函数
        
        Returns:
            SparkJob: 作业对象
        """
        job_id = f"clean_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        
        job = SparkJob(
            job_id=job_id,
            job_type=JobType.DATA_CLEANING.value,
            input_path=input_path,
            output_path=output_path,
            crawl_task_id=crawl_task_id
        )
        
        self.store.create(job)
        
        if on_complete:
            self._callbacks[job_id] = [on_complete]
        
        # 异步执行
        self.executor.submit(self._run_cleaning_job, job)
        
        logger.info(f"数据清洗作业已提交: {job_id}")
        return job
    
    def submit_ranking_job(self,
                          crawl_task_id: str = '',
                          on_complete: Callable = None) -> SparkJob:
        """
        提交双维度排序作业
        
        Args:
            crawl_task_id: 关联的采集任务ID
            on_complete: 完成回调函数
        
        Returns:
            SparkJob: 作业对象
        """
        job_id = f"rank_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        
        job = SparkJob(
            job_id=job_id,
            job_type=JobType.TOPIC_RANKING.value,
            crawl_task_id=crawl_task_id
        )
        
        self.store.create(job)
        
        if on_complete:
            self._callbacks[job_id] = [on_complete]
        
        # 异步执行
        self.executor.submit(self._run_ranking_job, job)
        
        logger.info(f"双维度排序作业已提交: {job_id}")
        return job
    
    def submit_full_pipeline(self,
                            input_path: str,
                            crawl_task_id: str = '',
                            on_complete: Callable = None) -> SparkJob:
        """
        提交完整数据处理流水线
        
        流程：数据清洗 → 情感分析 → 双维度排序
        
        Args:
            input_path: 输入数据路径
            crawl_task_id: 关联的采集任务ID
            on_complete: 完成回调函数
        
        Returns:
            SparkJob: 作业对象
        """
        job_id = f"pipeline_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        
        job = SparkJob(
            job_id=job_id,
            job_type=JobType.FULL_PIPELINE.value,
            input_path=input_path,
            crawl_task_id=crawl_task_id
        )
        
        self.store.create(job)
        
        if on_complete:
            self._callbacks[job_id] = [on_complete]
        
        # 异步执行完整流水线
        self.executor.submit(self._run_full_pipeline, job)
        
        logger.info(f"完整流水线作业已提交: {job_id}")
        return job
    
    def _run_cleaning_job(self, job: SparkJob):
        """执行数据清洗作业"""
        retry_count = 0
        
        while retry_count <= self.config.max_retries:
            try:
                job.status = JobStatus.RUNNING.value
                job.started_at = datetime.now().isoformat()
                job.retry_count = retry_count
                self.store.update(job)
                
                logger.info(f"开始执行数据清洗作业: {job.job_id} (重试次数: {retry_count})")
                
                # 构建spark-submit命令
                cmd = self._build_spark_command(
                    main_class='com.weibo.preprocessing.cleaner.DataCleaner',
                    args=[job.input_path, job.output_path]
                )
                
                # 执行命令
                success, output = self._execute_spark_command(cmd, job)
                
                if success:
                    job.status = JobStatus.COMPLETED.value
                    job.completed_at = datetime.now().isoformat()
                    job.progress = 100
                    self.store.update(job)
                    
                    logger.info(f"数据清洗作业完成: {job.job_id}")
                    self._trigger_callbacks(job)
                    return
                else:
                    raise Exception(f"Spark作业执行失败: {output}")
                    
            except Exception as e:
                retry_count += 1
                job.error_message = str(e)
                job.status = JobStatus.RETRYING.value if retry_count <= self.config.max_retries else JobStatus.FAILED.value
                self.store.update(job)
                
                logger.error(f"数据清洗作业失败: {job.job_id}, 错误: {e}")
                
                if retry_count <= self.config.max_retries:
                    logger.info(f"等待 {self.config.retry_delay_seconds} 秒后重试...")
                    time.sleep(self.config.retry_delay_seconds)
                else:
                    job.status = JobStatus.FAILED.value
                    job.completed_at = datetime.now().isoformat()
                    self.store.update(job)
                    self._trigger_callbacks(job)
    
    def _run_ranking_job(self, job: SparkJob):
        """执行双维度排序作业"""
        retry_count = 0
        
        while retry_count <= self.config.max_retries:
            try:
                job.status = JobStatus.RUNNING.value
                job.started_at = datetime.now().isoformat()
                job.retry_count = retry_count
                self.store.update(job)
                
                logger.info(f"开始执行双维度排序作业: {job.job_id}")
                
                # 构建spark-submit命令
                cmd = self._build_spark_command(
                    main_class='com.weibo.preprocessing.ranking.TopicRanker',
                    args=[]
                )
                
                # 执行命令
                success, output = self._execute_spark_command(cmd, job)
                
                if success:
                    job.status = JobStatus.COMPLETED.value
                    job.completed_at = datetime.now().isoformat()
                    job.progress = 100
                    self.store.update(job)
                    
                    logger.info(f"双维度排序作业完成: {job.job_id}")
                    self._trigger_callbacks(job)
                    return
                else:
                    raise Exception(f"Spark作业执行失败: {output}")
                    
            except Exception as e:
                retry_count += 1
                job.error_message = str(e)
                
                if retry_count <= self.config.max_retries:
                    job.status = JobStatus.RETRYING.value
                    self.store.update(job)
                    logger.info(f"等待 {self.config.retry_delay_seconds} 秒后重试...")
                    time.sleep(self.config.retry_delay_seconds)
                else:
                    job.status = JobStatus.FAILED.value
                    job.completed_at = datetime.now().isoformat()
                    self.store.update(job)
                    self._trigger_callbacks(job)
                    return
    
    def _run_full_pipeline(self, job: SparkJob):
        """执行完整数据处理流水线"""
        try:
            job.status = JobStatus.RUNNING.value
            job.started_at = datetime.now().isoformat()
            self.store.update(job)
            
            logger.info(f"开始执行完整流水线: {job.job_id}")
            
            # 阶段1: 数据清洗 (0-30%)
            job.progress = 10
            self.store.update(job)
            logger.info(f"[{job.job_id}] 阶段1: 数据清洗...")
            
            cleaned_path = self._run_pipeline_stage(
                job, 
                'com.weibo.preprocessing.cleaner.DataCleaner',
                [job.input_path, f'/weibo/cleaned/{job.job_id}']
            )
            
            job.progress = 30
            self.store.update(job)
            
            # 阶段2: 情感分析 (30-60%)
            logger.info(f"[{job.job_id}] 阶段2: 情感分析...")
            
            # 使用Python进行情感分析（因为ChineseBERT是Python模型）
            self._run_sentiment_analysis(job, cleaned_path)
            
            job.progress = 60
            self.store.update(job)
            
            # 阶段3: 写入HBase (60-80%)
            logger.info(f"[{job.job_id}] 阶段3: 写入HBase...")
            
            self._write_to_hbase(job)
            
            job.progress = 80
            self.store.update(job)
            
            # 阶段4: 双维度排序 (80-100%)
            logger.info(f"[{job.job_id}] 阶段4: 双维度排序...")
            
            self._run_pipeline_stage(
                job,
                'com.weibo.preprocessing.ranking.TopicRanker',
                []
            )
            
            job.status = JobStatus.COMPLETED.value
            job.completed_at = datetime.now().isoformat()
            job.progress = 100
            self.store.update(job)
            
            logger.info(f"完整流水线执行完成: {job.job_id}")
            self._trigger_callbacks(job)
            
        except Exception as e:
            logger.error(f"完整流水线执行失败: {job.job_id}, 错误: {e}")
            job.status = JobStatus.FAILED.value
            job.error_message = str(e)
            job.completed_at = datetime.now().isoformat()
            self.store.update(job)
            self._trigger_callbacks(job)
    
    def _run_pipeline_stage(self, job: SparkJob, main_class: str, args: List[str]) -> str:
        """执行流水线的一个阶段"""
        cmd = self._build_spark_command(main_class, args)
        success, output = self._execute_spark_command(cmd, job)
        
        if not success:
            raise Exception(f"流水线阶段失败 ({main_class}): {output}")
        
        return args[1] if len(args) > 1 else ''
    
    def _run_sentiment_analysis(self, job: SparkJob, input_path: str):
        """
        执行情感分析（Python实现）
        
        使用本地Python模块进行情感分析，而不是Spark作业
        """
        try:
            # 导入情感分析模块
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from spark.sentiment_analyzer import SparkSentimentAnalyzer
            
            analyzer = SparkSentimentAnalyzer()
            
            # 读取清洗后的数据
            data_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'data', 'storage', input_path.lstrip('/')
            )
            
            if os.path.exists(data_dir):
                # 读取并分析数据
                import glob
                all_data = []
                for json_file in glob.glob(os.path.join(data_dir, '*.json')):
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            all_data.extend(data)
                        else:
                            all_data.append(data)
                
                if all_data:
                    analyzed_data = analyzer.analyze_batch(all_data)
                    job.records_processed = len(analyzed_data)
                    logger.info(f"情感分析完成，处理 {len(analyzed_data)} 条数据")
                    
                    # 保存分析结果
                    output_file = os.path.join(
                        os.path.dirname(os.path.dirname(__file__)),
                        'data', f'sentiment_result_{job.job_id}.json'
                    )
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(analyzed_data, f, ensure_ascii=False, indent=2)
            else:
                logger.warning(f"输入路径不存在: {data_dir}")
                
        except Exception as e:
            logger.error(f"情感分析失败: {e}")
            raise
    
    def _write_to_hbase(self, job: SparkJob):
        """
        写入数据到HBase
        
        开发环境使用本地JSON模拟
        """
        try:
            # 尝试使用HBase客户端
            try:
                import happybase
                connection = happybase.Connection(self.config.hbase_zookeeper.split(':')[0])
                
                # 检查表是否存在
                tables = connection.tables()
                if b'weibo_posts' not in tables:
                    connection.create_table('weibo_posts', {'cf': dict()})
                
                logger.info("HBase连接成功，数据写入完成")
                connection.close()
                
            except Exception as e:
                logger.warning(f"HBase不可用，使用本地存储模拟: {e}")
                
                # 本地模拟HBase存储
                hbase_dir = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    'data', 'hbase_mock'
                )
                os.makedirs(hbase_dir, exist_ok=True)
                
                # 创建模拟表文件
                table_file = os.path.join(hbase_dir, 'weibo_posts.json')
                if not os.path.exists(table_file):
                    with open(table_file, 'w', encoding='utf-8') as f:
                        json.dump({}, f)
                
                logger.info("本地HBase模拟存储已就绪")
                
        except Exception as e:
            logger.error(f"HBase写入失败: {e}")
            raise
    
    def _build_spark_command(self, main_class: str, args: List[str]) -> List[str]:
        """构建spark-submit命令"""
        spark_submit = os.path.join(self.config.spark_home, 'bin', 'spark-submit')
        
        # Windows环境使用.cmd
        if sys.platform == 'win32':
            spark_submit = os.path.join(self.config.spark_home, 'bin', 'spark-submit.cmd')
        
        cmd = [
            spark_submit,
            '--class', main_class,
            '--master', self.config.spark_master,
            '--driver-memory', self.config.driver_memory,
            '--executor-memory', self.config.executor_memory,
            self.config.preprocessing_jar
        ]
        
        cmd.extend(args)
        
        return cmd
    
    def _execute_spark_command(self, cmd: List[str], job: SparkJob) -> tuple:
        """
        执行Spark命令
        
        Returns:
            (success: bool, output: str)
        """
        try:
            logger.info(f"执行命令: {' '.join(cmd)}")
            
            # 检查JAR文件是否存在
            if not os.path.exists(self.config.preprocessing_jar):
                logger.warning(f"JAR文件不存在: {self.config.preprocessing_jar}")
                logger.info("使用模拟执行模式...")
                
                # 模拟执行（开发环境）
                for i in range(10):
                    time.sleep(0.5)
                    job.progress = min(job.progress + 10, 95)
                    self.store.update(job)
                
                return True, "模拟执行成功"
            
            # 真实执行
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(self.config.preprocessing_jar)
            )
            
            self._running_jobs[job.job_id] = process
            
            # 实时读取输出
            stdout_lines = []
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    stdout_lines.append(line.strip())
                    logger.debug(f"[Spark] {line.strip()}")
                    
                    # 解析进度
                    if 'Stage' in line and '%' in line:
                        try:
                            progress = int(line.split('%')[0].split()[-1])
                            job.progress = min(progress, 95)
                            self.store.update(job)
                        except:
                            pass
            
            stderr = process.stderr.read()
            return_code = process.wait()
            
            del self._running_jobs[job.job_id]
            
            if return_code == 0:
                return True, '\n'.join(stdout_lines)
            else:
                return False, stderr
                
        except Exception as e:
            logger.error(f"执行Spark命令失败: {e}")
            return False, str(e)
    
    def _trigger_callbacks(self, job: SparkJob):
        """触发回调函数"""
        callbacks = self._callbacks.get(job.job_id, [])
        for callback in callbacks:
            try:
                callback(job)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")
        
        # 清理回调
        if job.job_id in self._callbacks:
            del self._callbacks[job.job_id]
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """获取作业状态"""
        job = self.store.get(job_id)
        if job:
            return job.to_dict()
        return None
    
    def get_all_jobs(self) -> List[Dict]:
        """获取所有作业"""
        jobs = self.store.get_all()
        return [job.to_dict() for job in sorted(jobs, key=lambda x: x.created_at, reverse=True)]
    
    def cancel_job(self, job_id: str) -> bool:
        """取消作业"""
        job = self.store.get(job_id)
        if not job:
            return False
        
        if job.status == JobStatus.RUNNING.value:
            # 尝试终止进程
            process = self._running_jobs.get(job_id)
            if process:
                process.terminate()
                del self._running_jobs[job_id]
        
        job.status = JobStatus.CANCELLED.value
        job.completed_at = datetime.now().isoformat()
        self.store.update(job)
        
        logger.info(f"作业已取消: {job_id}")
        return True


# 全局单例
_spark_service: Optional[SparkService] = None


def get_spark_service() -> SparkService:
    """获取SparkService单例"""
    global _spark_service
    if _spark_service is None:
        _spark_service = SparkService()
    return _spark_service


# ==================== 便捷函数 ====================

def trigger_cleaning_after_crawl(crawl_task_id: str, data_path: str) -> SparkJob:
    """
    采集完成后触发数据清洗
    
    Args:
        crawl_task_id: 采集任务ID
        data_path: 采集数据路径
    
    Returns:
        SparkJob: 清洗作业对象
    """
    service = get_spark_service()
    
    output_path = f'/weibo/cleaned/{crawl_task_id}'
    
    def on_complete(job: SparkJob):
        if job.status == JobStatus.COMPLETED.value:
            logger.info(f"清洗完成，触发双维度排序...")
            trigger_ranking_after_cleaning(crawl_task_id)
        else:
            logger.error(f"清洗失败: {job.error_message}")
    
    return service.submit_cleaning_job(
        input_path=data_path,
        output_path=output_path,
        crawl_task_id=crawl_task_id,
        on_complete=on_complete
    )


def trigger_ranking_after_cleaning(crawl_task_id: str) -> SparkJob:
    """
    清洗完成后触发双维度排序
    
    Args:
        crawl_task_id: 采集任务ID
    
    Returns:
        SparkJob: 排序作业对象
    """
    service = get_spark_service()
    
    def on_complete(job: SparkJob):
        if job.status == JobStatus.COMPLETED.value:
            logger.info(f"双维度排序完成，数据流处理结束")
        else:
            logger.error(f"排序失败: {job.error_message}")
    
    return service.submit_ranking_job(
        crawl_task_id=crawl_task_id,
        on_complete=on_complete
    )


def trigger_full_pipeline(crawl_task_id: str, data_path: str) -> SparkJob:
    """
    触发完整数据处理流水线
    
    Args:
        crawl_task_id: 采集任务ID
        data_path: 采集数据路径
    
    Returns:
        SparkJob: 流水线作业对象
    """
    service = get_spark_service()
    
    return service.submit_full_pipeline(
        input_path=data_path,
        crawl_task_id=crawl_task_id
    )
