"""
Task Queue Management for Data Collection
Controls concurrent task execution with Redis/database backend
"""
import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import queue
import logging

from config import config
from utils.logger import get_logger, log_operation, log_task_progress

logger = get_logger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class QueueTask:
    id: str
    name: str
    config: Dict[str, Any]
    status: TaskStatus
    priority: int = 1
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    retry_delays: List[float] = None
    error_message: Optional[str] = None
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.retry_delays is None:
            self.retry_delays = [1.0, 2.0, 4.0]  # Exponential backoff
    
    @property
    def next_retry_delay(self) -> float:
        """Get next retry delay based on retry count"""
        if self.retry_count < len(self.retry_delays):
            return self.retry_delays[self.retry_count]
        return self.retry_delays[-1]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime objects to strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
            elif isinstance(value, TaskStatus):
                data[key] = value.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueueTask':
        """Create from dictionary"""
        # Convert string status back to enum
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = TaskStatus(data['status'])
        
        # Convert string datetime back to datetime object
        for key in ['created_at', 'started_at', 'completed_at']:
            if key in data and data[key]:
                data[key] = datetime.fromisoformat(data[key])
        
        return cls(**data)


class TaskQueue:
    """Thread-safe task queue with concurrent execution limits"""
    
    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, QueueTask] = {}
        self.pending_queue = queue.PriorityQueue()
        self.running_tasks: Dict[str, QueueTask] = {}
        self.lock = threading.Lock()
        self.worker_threads: List[threading.Thread] = []
        self.shutdown_event = threading.Event()
        self.task_callbacks: Dict[str, callable] = {}
        
        # Start worker threads
        self._start_workers()
    
    def _start_workers(self):
        """Start worker threads for task execution"""
        for i in range(self.max_concurrent):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"TaskWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self.worker_threads.append(worker)
            logger.info(f"Started worker thread: {worker.name}")
    
    def _worker_loop(self):
        """Main worker loop for processing tasks"""
        while not self.shutdown_event.is_set():
            try:
                # Get task from queue with timeout
                priority, task_id = self.pending_queue.get(timeout=1.0)
                
                with self.lock:
                    if task_id not in self.tasks:
                        continue  # Task was removed
                    
                    task = self.tasks[task_id]
                    if task.status != TaskStatus.PENDING:
                        continue  # Task status changed
                    
                    # Mark as running
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now()
                    self.running_tasks[task_id] = task
                
                # Execute task
                self._execute_task(task)
                
            except queue.Empty:
                continue  # No tasks available
            except Exception as e:
                logger.error(f"Worker thread error: {e}", exc_info=True)
    
    def _execute_task(self, task: QueueTask):
        """Execute a single task with retry logic"""
        try:
            logger.info(f"Executing task: {task.id} - {task.name}")
            log_task_progress(task.id, "started")
            
            # Get task callback
            callback = self.task_callbacks.get(task.id)
            if not callback:
                raise ValueError(f"No callback registered for task {task.id}")
            
            # Execute the task
            result = callback(task.config)
            
            # Mark as completed
            with self.lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.progress = 100.0
                task.result = result
                
                # Remove from running tasks
                self.running_tasks.pop(task.id, None)
            
            logger.info(f"Task completed successfully: {task.id}")
            log_task_progress(task.id, "completed", 100.0)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Task execution failed: {task.id} - {error_msg}")
            
            with self.lock:
                task.error_message = error_msg
                
                # Check if we should retry
                if task.retry_count < task.max_retries:
                    task.status = TaskStatus.RETRYING
                    task.retry_count += 1
                    
                    # Remove from running tasks
                    self.running_tasks.pop(task.id, None)
                    
                    # Schedule retry
                    retry_delay = task.next_retry_delay
                    logger.info(f"Scheduling retry for task {task.id} in {retry_delay}s (attempt {task.retry_count})")
                    
                    threading.Timer(
                        retry_delay,
                        self._schedule_retry,
                        args=[task]
                    ).start()
                    
                else:
                    # Max retries exceeded, mark as failed
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    
                    # Remove from running tasks
                    self.running_tasks.pop(task.id, None)
                    
                    logger.error(f"Task failed after {task.max_retries} retries: {task.id}")
                    log_task_progress(task.id, "failed")
    
    def _schedule_retry(self, task: QueueTask):
        """Schedule a task for retry"""
        with self.lock:
            if task.id in self.tasks and task.status == TaskStatus.RETRYING:
                task.status = TaskStatus.PENDING
                # Add back to queue with same priority
                self.pending_queue.put((task.priority, task.id))
                logger.info(f"Task {task.id} scheduled for retry")
    
    def add_task(self, task: QueueTask, callback: callable) -> bool:
        """Add a new task to the queue"""
        with self.lock:
            if task.id in self.tasks:
                logger.warning(f"Task {task.id} already exists")
                return False
            
            self.tasks[task.id] = task
            self.task_callbacks[task.id] = callback
            
            # Add to priority queue (negative priority for max-heap behavior)
            self.pending_queue.put((-task.priority, task.id))
            
            logger.info(f"Task added to queue: {task.id} - {task.name}")
            return True
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
            
            if task.status == TaskStatus.RUNNING:
                # Cannot cancel running tasks immediately
                task.status = TaskStatus.CANCELLED
                logger.warning(f"Cannot cancel running task {task_id}, marked as cancelled")
                return False
            
            # Remove from queue
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            
            # Remove from running tasks if present
            self.running_tasks.pop(task_id, None)
            
            logger.info(f"Task cancelled: {task_id}")
            return True
    
    def get_task_status(self, task_id: str) -> Optional[QueueTask]:
        """Get task status"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[QueueTask]:
        """Get all tasks"""
        with self.lock:
            return list(self.tasks.values())
    
    def get_running_tasks(self) -> List[QueueTask]:
        """Get currently running tasks"""
        with self.lock:
            return list(self.running_tasks.values())
    
    def get_pending_tasks(self) -> List[QueueTask]:
        """Get pending tasks"""
        with self.lock:
            return [task for task in self.tasks.values() 
                   if task.status == TaskStatus.PENDING]
    
    def clear_completed_tasks(self, older_than_hours: int = 24):
        """Clear completed tasks older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        
        with self.lock:
            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] 
                    and task.completed_at 
                    and task.completed_at < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
                self.task_callbacks.pop(task_id, None)
            
            logger.info(f"Cleared {len(tasks_to_remove)} completed tasks")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self.lock:
            stats = {
                'total_tasks': len(self.tasks),
                'pending': len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
                'running': len(self.running_tasks),
                'completed': len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]),
                'failed': len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED]),
                'cancelled': len([t for t in self.tasks.values() if t.status == TaskStatus.CANCELLED]),
                'max_concurrent': self.max_concurrent,
                'worker_threads': len(self.worker_threads),
            }
            return stats
    
    def shutdown(self):
        """Shutdown the task queue"""
        logger.info("Shutting down task queue...")
        
        # Cancel all pending tasks
        with self.lock:
            for task in self.tasks.values():
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Wait for workers to finish
        for worker in self.worker_threads:
            worker.join(timeout=5.0)
        
        logger.info("Task queue shutdown complete")


# Global task queue instance
task_queue = TaskQueue(max_concurrent=config.crawler.max_concurrent_requests)
