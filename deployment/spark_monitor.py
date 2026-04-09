"""
Spark 伪集群性能监控
====================

监控和优化Spark伪集群性能

功能：
1. 作业性能监控：执行时间、任务数量、数据吞吐量
2. 资源使用监控：内存、CPU、磁盘I/O
3. 数据统计：输入输出数据量、Shuffle数据量
4. 可视化展示：实时仪表板、历史趋势图、性能预警
"""

import os
import sys
import json
import time
import logging
import threading
import psutil
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import deque
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('SparkMonitor')


@dataclass
class JobMetrics:
    """作业性能指标"""
    job_id: str
    job_name: str
    status: str  # running, completed, failed
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: float = 0
    
    # 任务统计
    num_stages: int = 0
    num_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    
    # 数据统计
    input_records: int = 0
    output_records: int = 0
    input_bytes: int = 0
    output_bytes: int = 0
    shuffle_read_bytes: int = 0
    shuffle_write_bytes: int = 0
    
    # 性能指标
    records_per_second: float = 0
    bytes_per_second: float = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ResourceMetrics:
    """资源使用指标"""
    timestamp: str
    
    # CPU
    cpu_percent: float = 0
    cpu_count: int = 0
    
    # 内存
    memory_total_mb: float = 0
    memory_used_mb: float = 0
    memory_percent: float = 0
    
    # 磁盘
    disk_read_mb: float = 0
    disk_write_mb: float = 0
    disk_io_percent: float = 0
    
    # 网络
    network_sent_mb: float = 0
    network_recv_mb: float = 0
    
    # JVM (Spark)
    jvm_heap_used_mb: float = 0
    jvm_heap_max_mb: float = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PerformanceAlert:
    """性能预警"""
    alert_id: str
    alert_type: str  # high_memory, slow_job, high_cpu, etc.
    severity: str    # low, medium, high, critical
    message: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: str
    job_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SparkMonitor:
    """
    Spark 性能监控器
    
    监控Spark伪集群的作业性能和资源使用
    """
    
    # Spark REST API 配置
    SPARK_MASTER_URL = os.getenv('SPARK_MASTER_URL', 'http://localhost:8080')
    SPARK_HISTORY_URL = os.getenv('SPARK_HISTORY_URL', 'http://localhost:18080')
    
    # 性能阈值
    THRESHOLDS = {
        'memory_percent': 85,      # 内存使用率阈值
        'cpu_percent': 90,         # CPU使用率阈值
        'job_duration_seconds': 300,  # 作业时长阈值（5分钟）
        'task_failure_rate': 0.1,  # 任务失败率阈值
        'shuffle_spill_ratio': 0.5,  # Shuffle溢出比例阈值
    }
    
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(__file__), 'spark_metrics'
        )
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 数据存储
        self._job_metrics: Dict[str, JobMetrics] = {}
        self._resource_history: deque = deque(maxlen=1000)  # 保留最近1000条
        self._alerts: List[PerformanceAlert] = []
        
        # 监控状态
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # 上次IO统计
        self._last_disk_io = None
        self._last_net_io = None
        self._last_io_time = None
        
        # 加载历史数据
        self._load_data()
    
    def _load_data(self):
        """加载历史数据"""
        try:
            metrics_file = os.path.join(self.data_dir, 'job_metrics.json')
            if os.path.exists(metrics_file):
                with open(metrics_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for job_data in data:
                        self._job_metrics[job_data['job_id']] = JobMetrics(**job_data)
                logger.info(f"已加载 {len(self._job_metrics)} 条作业指标")
        except Exception as e:
            logger.error(f"加载历史数据失败: {e}")
    
    def _save_data(self):
        """保存数据"""
        try:
            # 保存作业指标
            metrics_file = os.path.join(self.data_dir, 'job_metrics.json')
            with open(metrics_file, 'w', encoding='utf-8') as f:
                data = [m.to_dict() for m in self._job_metrics.values()]
                json.dump(data[-100:], f, ensure_ascii=False, indent=2)  # 只保留最近100条
            
            # 保存资源历史
            resource_file = os.path.join(self.data_dir, 'resource_history.json')
            with open(resource_file, 'w', encoding='utf-8') as f:
                data = [r.to_dict() for r in self._resource_history]
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 保存报警
            alerts_file = os.path.join(self.data_dir, 'alerts.json')
            with open(alerts_file, 'w', encoding='utf-8') as f:
                data = [a.to_dict() for a in self._alerts[-100:]]
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
    
    # ==================== 作业监控 ====================
    
    def get_spark_applications(self) -> List[Dict]:
        """获取Spark应用列表"""
        try:
            response = requests.get(
                f"{self.SPARK_MASTER_URL}/api/v1/applications",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"获取Spark应用失败: {e}")
        return []
    
    def get_job_details(self, app_id: str, job_id: str) -> Optional[Dict]:
        """获取作业详情"""
        try:
            response = requests.get(
                f"{self.SPARK_MASTER_URL}/api/v1/applications/{app_id}/jobs/{job_id}",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"获取作业详情失败: {e}")
        return None
    
    def get_stage_details(self, app_id: str, stage_id: str) -> Optional[Dict]:
        """获取Stage详情"""
        try:
            response = requests.get(
                f"{self.SPARK_MASTER_URL}/api/v1/applications/{app_id}/stages/{stage_id}",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"获取Stage详情失败: {e}")
        return None
    
    def collect_job_metrics(self, job_id: str, job_name: str = None) -> JobMetrics:
        """
        收集作业性能指标
        
        Args:
            job_id: 作业ID
            job_name: 作业名称
        
        Returns:
            JobMetrics: 作业性能指标
        """
        metrics = JobMetrics(
            job_id=job_id,
            job_name=job_name or f"Job_{job_id}",
            status='unknown',
            start_time=datetime.now().isoformat()
        )
        
        try:
            # 尝试从Spark REST API获取
            apps = self.get_spark_applications()
            for app in apps:
                job_details = self.get_job_details(app['id'], job_id)
                if job_details:
                    metrics.status = job_details.get('status', 'unknown').lower()
                    metrics.num_stages = job_details.get('numStages', 0)
                    metrics.num_tasks = job_details.get('numTasks', 0)
                    metrics.completed_tasks = job_details.get('numCompletedTasks', 0)
                    metrics.failed_tasks = job_details.get('numFailedTasks', 0)
                    
                    if job_details.get('submissionTime'):
                        metrics.start_time = job_details['submissionTime']
                    if job_details.get('completionTime'):
                        metrics.end_time = job_details['completionTime']
                        # 计算持续时间
                        start = datetime.fromisoformat(metrics.start_time.replace('Z', '+00:00'))
                        end = datetime.fromisoformat(metrics.end_time.replace('Z', '+00:00'))
                        metrics.duration_seconds = (end - start).total_seconds()
                    
                    break
        except Exception as e:
            logger.warning(f"从Spark API收集指标失败: {e}")
        
        with self._lock:
            self._job_metrics[job_id] = metrics
        
        return metrics
    
    def update_job_metrics(self, job_id: str, **kwargs) -> Optional[JobMetrics]:
        """更新作业指标"""
        with self._lock:
            if job_id in self._job_metrics:
                metrics = self._job_metrics[job_id]
                for key, value in kwargs.items():
                    if hasattr(metrics, key):
                        setattr(metrics, key, value)
                
                # 计算吞吐量
                if metrics.duration_seconds > 0:
                    metrics.records_per_second = metrics.output_records / metrics.duration_seconds
                    metrics.bytes_per_second = metrics.output_bytes / metrics.duration_seconds
                
                return metrics
        return None
    
    def complete_job(self, job_id: str, status: str = 'completed',
                    input_records: int = 0, output_records: int = 0,
                    input_bytes: int = 0, output_bytes: int = 0) -> Optional[JobMetrics]:
        """完成作业并记录最终指标"""
        with self._lock:
            if job_id in self._job_metrics:
                metrics = self._job_metrics[job_id]
                metrics.status = status
                metrics.end_time = datetime.now().isoformat()
                
                # 计算持续时间
                start = datetime.fromisoformat(metrics.start_time)
                end = datetime.fromisoformat(metrics.end_time)
                metrics.duration_seconds = (end - start).total_seconds()
                
                # 更新数据统计
                metrics.input_records = input_records
                metrics.output_records = output_records
                metrics.input_bytes = input_bytes
                metrics.output_bytes = output_bytes
                
                # 计算吞吐量
                if metrics.duration_seconds > 0:
                    metrics.records_per_second = output_records / metrics.duration_seconds
                    metrics.bytes_per_second = output_bytes / metrics.duration_seconds
                
                # 检查性能预警
                self._check_job_alerts(metrics)
                
                # 保存数据
                self._save_data()
                
                return metrics
        return None
    
    # ==================== 资源监控 ====================
    
    def collect_resource_metrics(self) -> ResourceMetrics:
        """收集系统资源指标"""
        metrics = ResourceMetrics(timestamp=datetime.now().isoformat())
        
        try:
            # CPU
            metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
            metrics.cpu_count = psutil.cpu_count()
            
            # 内存
            mem = psutil.virtual_memory()
            metrics.memory_total_mb = mem.total / (1024 * 1024)
            metrics.memory_used_mb = mem.used / (1024 * 1024)
            metrics.memory_percent = mem.percent
            
            # 磁盘I/O
            disk_io = psutil.disk_io_counters()
            current_time = time.time()
            
            if self._last_disk_io and self._last_io_time:
                time_delta = current_time - self._last_io_time
                if time_delta > 0:
                    metrics.disk_read_mb = (disk_io.read_bytes - self._last_disk_io.read_bytes) / (1024 * 1024) / time_delta
                    metrics.disk_write_mb = (disk_io.write_bytes - self._last_disk_io.write_bytes) / (1024 * 1024) / time_delta
            
            self._last_disk_io = disk_io
            
            # 网络I/O
            net_io = psutil.net_io_counters()
            
            if self._last_net_io and self._last_io_time:
                time_delta = current_time - self._last_io_time
                if time_delta > 0:
                    metrics.network_sent_mb = (net_io.bytes_sent - self._last_net_io.bytes_sent) / (1024 * 1024) / time_delta
                    metrics.network_recv_mb = (net_io.bytes_recv - self._last_net_io.bytes_recv) / (1024 * 1024) / time_delta
            
            self._last_net_io = net_io
            self._last_io_time = current_time
            
            # 尝试获取JVM内存（通过Spark REST API）
            try:
                apps = self.get_spark_applications()
                if apps:
                    app_id = apps[0]['id']
                    response = requests.get(
                        f"{self.SPARK_MASTER_URL}/api/v1/applications/{app_id}/executors",
                        timeout=5
                    )
                    if response.status_code == 200:
                        executors = response.json()
                        total_heap_used = sum(e.get('memoryUsed', 0) for e in executors)
                        total_heap_max = sum(e.get('maxMemory', 0) for e in executors)
                        metrics.jvm_heap_used_mb = total_heap_used / (1024 * 1024)
                        metrics.jvm_heap_max_mb = total_heap_max / (1024 * 1024)
            except:
                pass
            
        except Exception as e:
            logger.error(f"收集资源指标失败: {e}")
        
        # 保存到历史
        with self._lock:
            self._resource_history.append(metrics)
        
        # 检查资源预警
        self._check_resource_alerts(metrics)
        
        return metrics
    
    # ==================== 性能预警 ====================
    
    def _check_job_alerts(self, metrics: JobMetrics):
        """检查作业性能预警"""
        alerts = []
        
        # 检查作业时长
        if metrics.duration_seconds > self.THRESHOLDS['job_duration_seconds']:
            alerts.append(PerformanceAlert(
                alert_id=f"slow_job_{metrics.job_id}_{int(time.time())}",
                alert_type='slow_job',
                severity='medium',
                message=f"作业 {metrics.job_name} 执行时间过长: {metrics.duration_seconds:.1f}秒",
                metric_name='job_duration_seconds',
                current_value=metrics.duration_seconds,
                threshold=self.THRESHOLDS['job_duration_seconds'],
                timestamp=datetime.now().isoformat(),
                job_id=metrics.job_id
            ))
        
        # 检查任务失败率
        if metrics.num_tasks > 0:
            failure_rate = metrics.failed_tasks / metrics.num_tasks
            if failure_rate > self.THRESHOLDS['task_failure_rate']:
                severity = 'critical' if failure_rate > 0.3 else 'high'
                alerts.append(PerformanceAlert(
                    alert_id=f"task_failure_{metrics.job_id}_{int(time.time())}",
                    alert_type='high_task_failure',
                    severity=severity,
                    message=f"作业 {metrics.job_name} 任务失败率过高: {failure_rate*100:.1f}%",
                    metric_name='task_failure_rate',
                    current_value=failure_rate,
                    threshold=self.THRESHOLDS['task_failure_rate'],
                    timestamp=datetime.now().isoformat(),
                    job_id=metrics.job_id
                ))
        
        with self._lock:
            self._alerts.extend(alerts)
    
    def _check_resource_alerts(self, metrics: ResourceMetrics):
        """检查资源使用预警"""
        alerts = []
        
        # 检查内存使用
        if metrics.memory_percent > self.THRESHOLDS['memory_percent']:
            severity = 'critical' if metrics.memory_percent > 95 else 'high'
            alerts.append(PerformanceAlert(
                alert_id=f"high_memory_{int(time.time())}",
                alert_type='high_memory',
                severity=severity,
                message=f"内存使用率过高: {metrics.memory_percent:.1f}%",
                metric_name='memory_percent',
                current_value=metrics.memory_percent,
                threshold=self.THRESHOLDS['memory_percent'],
                timestamp=metrics.timestamp
            ))
        
        # 检查CPU使用
        if metrics.cpu_percent > self.THRESHOLDS['cpu_percent']:
            alerts.append(PerformanceAlert(
                alert_id=f"high_cpu_{int(time.time())}",
                alert_type='high_cpu',
                severity='medium',
                message=f"CPU使用率过高: {metrics.cpu_percent:.1f}%",
                metric_name='cpu_percent',
                current_value=metrics.cpu_percent,
                threshold=self.THRESHOLDS['cpu_percent'],
                timestamp=metrics.timestamp
            ))
        
        with self._lock:
            self._alerts.extend(alerts)
    
    # ==================== 监控控制 ====================
    
    def start_monitoring(self, interval: int = 5):
        """
        启动后台监控
        
        Args:
            interval: 采集间隔（秒）
        """
        if self._monitoring:
            logger.warning("监控已在运行")
            return
        
        self._monitoring = True
        
        def monitor_loop():
            while self._monitoring:
                try:
                    self.collect_resource_metrics()
                except Exception as e:
                    logger.error(f"监控循环错误: {e}")
                time.sleep(interval)
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"监控已启动，采集间隔: {interval}秒")
    
    def stop_monitoring(self):
        """停止后台监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self._save_data()
        logger.info("监控已停止")
    
    # ==================== 数据查询 ====================
    
    def get_job_metrics(self, job_id: str = None) -> List[Dict]:
        """获取作业指标"""
        with self._lock:
            if job_id:
                if job_id in self._job_metrics:
                    return [self._job_metrics[job_id].to_dict()]
                return []
            return [m.to_dict() for m in self._job_metrics.values()]
    
    def get_resource_history(self, minutes: int = 60) -> List[Dict]:
        """获取资源历史"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            result = []
            for metrics in self._resource_history:
                try:
                    ts = datetime.fromisoformat(metrics.timestamp)
                    if ts >= cutoff:
                        result.append(metrics.to_dict())
                except:
                    pass
            return result
    
    def get_alerts(self, severity: str = None, limit: int = 50) -> List[Dict]:
        """获取预警列表"""
        with self._lock:
            alerts = self._alerts[-limit:]
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            return [a.to_dict() for a in alerts]
    
    def get_current_status(self) -> Dict:
        """获取当前状态概览"""
        with self._lock:
            # 最新资源指标
            latest_resource = self._resource_history[-1].to_dict() if self._resource_history else {}
            
            # 运行中的作业
            running_jobs = [m for m in self._job_metrics.values() if m.status == 'running']
            
            # 最近完成的作业
            completed_jobs = sorted(
                [m for m in self._job_metrics.values() if m.status == 'completed'],
                key=lambda x: x.end_time or '',
                reverse=True
            )[:5]
            
            # 活跃报警
            recent_alerts = [a for a in self._alerts[-20:] if a.severity in ['high', 'critical']]
            
            return {
                'monitoring': self._monitoring,
                'resource': latest_resource,
                'running_jobs': len(running_jobs),
                'completed_jobs_today': len([
                    m for m in self._job_metrics.values()
                    if m.end_time and m.end_time.startswith(datetime.now().strftime('%Y-%m-%d'))
                ]),
                'active_alerts': len(recent_alerts),
                'recent_jobs': [m.to_dict() for m in completed_jobs],
                'alerts': [a.to_dict() for a in recent_alerts]
            }
    
    def get_performance_summary(self) -> Dict:
        """获取性能摘要"""
        with self._lock:
            completed_jobs = [m for m in self._job_metrics.values() if m.status == 'completed']
            
            if not completed_jobs:
                return {
                    'avg_duration': 0,
                    'avg_throughput': 0,
                    'total_records_processed': 0,
                    'total_bytes_processed': 0,
                    'job_count': 0
                }
            
            return {
                'avg_duration': sum(j.duration_seconds for j in completed_jobs) / len(completed_jobs),
                'avg_throughput': sum(j.records_per_second for j in completed_jobs) / len(completed_jobs),
                'total_records_processed': sum(j.output_records for j in completed_jobs),
                'total_bytes_processed': sum(j.output_bytes for j in completed_jobs),
                'job_count': len(completed_jobs)
            }
    
    def generate_optimization_suggestions(self) -> List[str]:
        """生成性能优化建议"""
        suggestions = []
        
        with self._lock:
            # 基于资源使用
            if self._resource_history:
                avg_memory = sum(r.memory_percent for r in self._resource_history) / len(self._resource_history)
                avg_cpu = sum(r.cpu_percent for r in self._resource_history) / len(self._resource_history)
                
                if avg_memory > 80:
                    suggestions.append("内存使用率较高，建议增加executor内存或减少并行度")
                if avg_cpu < 30:
                    suggestions.append("CPU利用率较低，可以考虑增加并行度提高效率")
            
            # 基于作业性能
            completed_jobs = [m for m in self._job_metrics.values() if m.status == 'completed']
            if completed_jobs:
                avg_duration = sum(j.duration_seconds for j in completed_jobs) / len(completed_jobs)
                if avg_duration > 120:
                    suggestions.append("平均作业时间较长，建议检查数据分区策略")
                
                # 检查Shuffle
                high_shuffle_jobs = [j for j in completed_jobs if j.shuffle_read_bytes > j.input_bytes * 0.5]
                if len(high_shuffle_jobs) > len(completed_jobs) * 0.3:
                    suggestions.append("Shuffle数据量较大，建议优化Join策略或使用广播变量")
            
            # 基于报警
            failure_alerts = [a for a in self._alerts if a.alert_type == 'high_task_failure']
            if len(failure_alerts) > 3:
                suggestions.append("任务失败率较高，建议检查数据质量和资源配置")
        
        if not suggestions:
            suggestions.append("当前性能表现良好，继续保持")
        
        return suggestions


# 全局单例
_monitor: Optional[SparkMonitor] = None


def get_monitor() -> SparkMonitor:
    """获取监控器单例"""
    global _monitor
    if _monitor is None:
        _monitor = SparkMonitor()
    return _monitor


# ==================== Flask API ====================

def create_monitor_api():
    """创建监控API蓝图"""
    from flask import Blueprint, jsonify, request
    
    monitor_bp = Blueprint('spark_monitor', __name__, url_prefix='/api/spark/monitor')
    
    @monitor_bp.route('/status', methods=['GET'])
    def get_status():
        """获取当前状态"""
        monitor = get_monitor()
        return jsonify({
            'code': 200,
            'data': monitor.get_current_status()
        })
    
    @monitor_bp.route('/jobs', methods=['GET'])
    def get_jobs():
        """获取作业列表"""
        monitor = get_monitor()
        job_id = request.args.get('job_id')
        return jsonify({
            'code': 200,
            'data': monitor.get_job_metrics(job_id)
        })
    
    @monitor_bp.route('/resources', methods=['GET'])
    def get_resources():
        """获取资源历史"""
        monitor = get_monitor()
        minutes = request.args.get('minutes', 60, type=int)
        return jsonify({
            'code': 200,
            'data': monitor.get_resource_history(minutes)
        })
    
    @monitor_bp.route('/alerts', methods=['GET'])
    def get_alerts():
        """获取报警列表"""
        monitor = get_monitor()
        severity = request.args.get('severity')
        limit = request.args.get('limit', 50, type=int)
        return jsonify({
            'code': 200,
            'data': monitor.get_alerts(severity, limit)
        })
    
    @monitor_bp.route('/summary', methods=['GET'])
    def get_summary():
        """获取性能摘要"""
        monitor = get_monitor()
        return jsonify({
            'code': 200,
            'data': monitor.get_performance_summary()
        })
    
    @monitor_bp.route('/suggestions', methods=['GET'])
    def get_suggestions():
        """获取优化建议"""
        monitor = get_monitor()
        return jsonify({
            'code': 200,
            'data': monitor.generate_optimization_suggestions()
        })
    
    @monitor_bp.route('/start', methods=['POST'])
    def start_monitoring():
        """启动监控"""
        monitor = get_monitor()
        interval = request.json.get('interval', 5) if request.json else 5
        monitor.start_monitoring(interval)
        return jsonify({
            'code': 200,
            'message': '监控已启动'
        })
    
    @monitor_bp.route('/stop', methods=['POST'])
    def stop_monitoring():
        """停止监控"""
        monitor = get_monitor()
        monitor.stop_monitoring()
        return jsonify({
            'code': 200,
            'message': '监控已停止'
        })
    
    return monitor_bp


if __name__ == '__main__':
    # 测试监控器
    monitor = SparkMonitor()
    
    # 启动监控
    monitor.start_monitoring(interval=2)
    
    # 模拟作业
    job_id = f"test_job_{int(time.time())}"
    monitor.collect_job_metrics(job_id, "测试作业")
    
    time.sleep(5)
    
    # 完成作业
    monitor.complete_job(
        job_id,
        status='completed',
        input_records=10000,
        output_records=9500,
        input_bytes=1024*1024*10,
        output_bytes=1024*1024*8
    )
    
    # 打印状态
    print("\n当前状态:")
    print(json.dumps(monitor.get_current_status(), indent=2, ensure_ascii=False))
    
    print("\n性能摘要:")
    print(json.dumps(monitor.get_performance_summary(), indent=2, ensure_ascii=False))
    
    print("\n优化建议:")
    for suggestion in monitor.generate_optimization_suggestions():
        print(f"  - {suggestion}")
    
    # 停止监控
    monitor.stop_monitoring()
