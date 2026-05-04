"""
数据采集模块API
提供微博数据采集的完整功能
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import threading
import time
import random
import os
import sys
from typing import Dict, List, Optional

# 
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 
try:
    from crawler.weibo_crawler import WeiboCrawler
    CRAWLER_AVAILABLE = True
except ImportError as e:
    CRAWLER_AVAILABLE = False
    from utils.logger import get_logger
    get_logger(__name__).warning(f"crawl module import failed: {e}")

# 
try:
    from services.database_service import get_db_service
    DB_AVAILABLE = True
except ImportError as e:
    DB_AVAILABLE = False
    from utils.logger import get_logger
    get_logger(__name__).warning(f"database service import failed: {e}")

try:
    from spark.sentiment_analyzer import SentimentLexicon
    SENTIMENT_AVAILABLE = True
except ImportError as e:
    SENTIMENT_AVAILABLE = False
    from utils.logger import get_logger
    get_logger(__name__).warning(f"sentiment module import failed: {e}")

# 
from utils.logger import get_logger, log_operation, log_api_call, log_data_collection
from services.task_queue import task_queue, QueueTask, TaskStatus
from services.cookie_pool import cookie_pool
collection_bp = Blueprint('collection', __name__, url_prefix='/api/collection')
logger = get_logger(__name__)

# 全局任务存储（实际应用中应使用数据库）
tasks: Dict[str, Dict] = {}
task_logs: Dict[str, List[Dict]] = {}
task_data: Dict[str, List[Dict]] = {}

# 任务锁
task_lock = threading.Lock()


class CrawlerTask:
    """爬虫任务类"""
    
    def __init__(self, task_id: str, config: Dict):
        self.task_id = task_id
        self.config = config
        self.status = 'waiting'
        self.progress = 0
        self.collected = 0
        self.failed = 0
        self.is_running = False
        self._pause_event = threading.Event()  # 用于真正的暂停挂起
        self._pause_event.set()  # 初始为非暂停状态
        self._terminated = False  # 终止标志（不可恢复）
        self.thread: Optional[threading.Thread] = None
        self.batch_id: Optional[str] = None
        self._weibo_buffer: List[Dict] = []  # 批量入库缓冲
        self._buffer_size = 50  # 每50条刷入MySQL
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.summary: Dict = {}  # 完成汇总
        
    def start(self):
        """启动任务"""
        if self.is_running:
            return False
            
        self.is_running = True
        self.status = 'running'
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        return True
        
    def pause(self):
        """暂停任务 - 线程挂起，不退出"""
        self._pause_event.clear()  # 阻塞线程
        self.status = 'paused'
        self._log('warn', '任务已暂停，线程挂起等待恢复')
        self._update_task_status()
        
    def stop(self):
        """终止任务 - 不可恢复"""
        self._terminated = True
        self._pause_event.set()  # 确保线程不在等待中
        self.is_running = False
        self.status = 'stopped'

    def resume(self):
        """恢复暂停的任务 - 唤醒挂起线程"""
        if self.status != 'paused':
            return False
        self.status = 'running'
        self._pause_event.set()  # 唤醒线程
        self._log('info', '任务已恢复，线程继续执行')
        self._update_task_status()
        return True
        
    def _run(self):
        """执行采集任务"""
        try:
            self._log('info', f'任务开始执行: {self.config["name"]}')
            
            keywords = self.config.get('keywords', [])
            data_sources = self.config.get('dataSources', ['weibo'])
            max_count = self.config.get('maxCount', 10000)
            request_interval = self.config.get('requestInterval', 3)
            
            keyword_list = [k['word'] for k in keywords] if keywords else []
            self._log('info', f'关键词: {", ".join(keyword_list) if keyword_list else "无"}')
            self._log('info', f'数据源: {", ".join(data_sources)}')
            self._log('info', f'目标数量: {max_count}')
            
            # 初始化数据库批次
            if DB_AVAILABLE:
                try:
                    db = get_db_service()
                    self.batch_id = db.create_crawl_batch(
                        task_name=self.config.get('name', self.task_id),
                        task_type='keyword_search',
                        keywords=keyword_list
                    )
                    self._log('info', f'数据库批次已创建: {self.batch_id}')
                except Exception as e:
                    self._log('warn', f'数据库批次创建失败: {e}，数据将仅存内存')
                    self.batch_id = None
            
            # 使用真实爬虫采集数据
            if CRAWLER_AVAILABLE and 'weibo' in data_sources:
                self._log('info', '使用微博爬虫采集真实数据...')
                crawler = WeiboCrawler()
                
                for keyword in keyword_list:
                    if not self.is_running or self._terminated:
                        break
                    
                    # 暂停检查点：线程在此挂起等待恢复
                    self._pause_event.wait()
                    if self._terminated:
                        break
                    
                    self._log('info', f'正在搜索关键词: {keyword}')
                    
                    try:
                        # 搜索微博
                        page = 1
                        while self.is_running and not self._terminated and self.collected < max_count and page <= 5:
                            # 每页采集前检查暂停
                            self._pause_event.wait()
                            if self._terminated:
                                break
                            
                            weibo_list = list(crawler.search_weibo(keyword, page, 'all'))
                            
                            if not weibo_list:
                                self._log('warn', f'关键词 "{keyword}" 第 {page} 页无数据')
                                break
                            
                            for weibo in weibo_list:
                                if self.collected >= max_count:
                                    break
                                
                                # 保留原始weibo dict用于MySQL入库
                                weibo['keyword'] = keyword
                                self._save_data_to_db(weibo)
                                
                                # 同时保存转换格式到内存（供API即时查询）
                                data = self._convert_weibo_data(weibo, keyword)
                                self._save_data(data)
                                self.collected += 1
                                self.progress = min(100, int((self.collected / max_count) * 100))
                            
                            self._log('info', f'成功采集 {len(weibo_list)} 条数据 (关键词: {keyword}, 页码: {page})')
                            self._update_task_status()
                            
                            page += 1
                            time.sleep(request_interval)
                            
                    except Exception as e:
                        self._log('error', f'采集关键词 "{keyword}" 失败: {str(e)}')
                        self.failed += 1
                        
            else:
                self._log('warn', '爬虫模块不可用，无法采集数据')
                self.status = 'failed'
                self._log('error', '请检查爬虫模块配置')
            
            # 刷入剩余缓冲数据到MySQL
            self._flush_buffer()
            
            # 更新数据库批次状态
            if DB_AVAILABLE and self.batch_id:
                try:
                    db = get_db_service()
                    db.complete_crawl_batch(
                        self.batch_id, self.collected, self.collected, self.failed
                    )
                except Exception as e:
                    self._log('warn', f'更新批次状态失败: {e}')
            
            # 如果是终止退出，保留stopped状态
            if self._terminated:
                self.end_time = time.time()
                self._log('warn', f'任务已终止，已采集 {self.collected} 条数据已保留')
                return

            # 任务完成
            self.end_time = time.time()
            elapsed = self.end_time - (self.start_time or self.end_time)
            success_rate = round(self.collected / max(self.collected + self.failed, 1) * 100, 1)
            self.summary = {
                'total_collected': self.collected,
                'total_failed': self.failed,
                'elapsed_seconds': round(elapsed, 1),
                'elapsed_display': f'{int(elapsed // 60)}分{int(elapsed % 60)}秒',
                'success_rate': success_rate,
                'avg_speed': round(self.collected / max(elapsed, 1), 2),
            }

            if self.collected > 0:
                self.status = 'completed'
                self.progress = 100
                self._log('success',
                    f'任务完成 | 采集 {self.collected} 条 | 耗时 {self.summary["elapsed_display"]}'
                    f' | 成功率 {success_rate}% | 速率 {self.summary["avg_speed"]} 条/s')
            else:
                self.status = 'failed'
                self._log('error', '未采集到数据')
                
        except Exception as e:
            self.status = 'failed'
            self._log('error', f'任务执行失败: {str(e)}')
            logger.error(f'Task {self.task_id} failed: {e}', exc_info=True)
        finally:
            self.is_running = False
            self._update_task_status()
    
    def _convert_weibo_data(self, weibo: Dict, keyword: str) -> Dict:
        """转换微博数据格式"""
        return {
            'id': weibo.get('id', f'{self.task_id}_{self.collected}'),
            'content': weibo.get('text', ''),
            'source': 'weibo',
            'keyword': keyword,
            'author': weibo.get('user', {}).get('screen_name', ''),
            'author_id': weibo.get('user', {}).get('id', ''),
            'likes': weibo.get('attitudes_count', 0),
            'comments': weibo.get('comments_count', 0),
            'shares': weibo.get('reposts_count', 0),
            'timestamp': weibo.get('created_at', datetime.now().isoformat()),
            'crawl_time': datetime.now().isoformat(),
        }
    
    def _save_data(self, data: Dict):
        """保存采集数据到内存（供API即时查询）"""
        if self.task_id not in task_data:
            task_data[self.task_id] = []
        task_data[self.task_id].append(data)
    
    def _save_data_to_db(self, weibo_raw: Dict):
        """缓冲并批量入库MySQL"""
        self._weibo_buffer.append(weibo_raw)
        if len(self._weibo_buffer) >= self._buffer_size:
            self._flush_buffer()
    
    def _flush_buffer(self):
        """将缓冲数据刷入MySQL"""
        if not self._weibo_buffer or not DB_AVAILABLE:
            return
        try:
            db = get_db_service()
            result = db.bulk_insert_weibos(self._weibo_buffer, self.batch_id)
            self._log('info', f'MySQL入库: 成功{result["inserted"]}条, 跳过{result["skipped"]}条')
        except Exception as e:
            self._log('warn', f'MySQL入库失败: {e}')
        finally:
            self._weibo_buffer.clear()
    
    def _log(self, level: str, message: str):
        """记录日志"""
        log_entry = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'level': level,
            'message': message,
        }
        
        if self.task_id not in task_logs:
            task_logs[self.task_id] = []
        task_logs[self.task_id].append(log_entry)
        
        # 限制日志数量
        if len(task_logs[self.task_id]) > 100:
            task_logs[self.task_id].pop(0)
    
    def _update_task_status(self):
        """更新任务状态"""
        with task_lock:
            if self.task_id in tasks:
                tasks[self.task_id].update({
                    'status': self.status,
                    'progress': self.progress,
                    'collected': self.collected,
                    'failed': self.failed,
                    'batch_id': self.batch_id,
                    'updatedAt': datetime.now().isoformat(),
                    'summary': self.summary,
                })


# ==================== API路由 ====================

@collection_bp.route('/tasks', methods=['GET'])
@log_api_call('/api/collection/tasks', 'GET')
def get_tasks():
    """获取任务列表"""
    try:
        task_list = list(tasks.values())
        logger.info(f"Retrieved {len(task_list)} tasks")
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': task_list,
        })
    except Exception as e:
        logger.error(f'Get tasks failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@collection_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """获取任务详情"""
    try:
        if task_id not in tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在',
            }), 404
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': tasks[task_id],
        })
    except Exception as e:
        logger.error(f'Get task failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@collection_bp.route('/tasks', methods=['POST'])
def create_task():
    """创建任务"""
    try:
        data = request.json
        
        # 验证必填字段
        if not data.get('name'):
            return jsonify({
                'code': 400,
                'message': '任务名称不能为空',
            }), 400
        
        if not data.get('keywords'):
            return jsonify({
                'code': 400,
                'message': '关键词不能为空',
            }), 400
        
        # 生成任务ID
        task_id = f'task_{int(time.time() * 1000)}'
        
        # 创建任务
        task = {
            'id': task_id,
            'name': data['name'],
            'keywords': data['keywords'],
            'config': data,
            'status': 'waiting',
            'progress': 0,
            'collected': 0,
            'failed': 0,
            'createdAt': datetime.now().isoformat(),
            'updatedAt': datetime.now().isoformat(),
        }
        
        with task_lock:
            tasks[task_id] = task
        
        logger.info(f'Task created: {task_id}')
        
        return jsonify({
            'code': 200,
            'message': '任务创建成功',
            'data': task,
        })
    except Exception as e:
        logger.error(f'Create task failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@collection_bp.route('/tasks/<task_id>', methods=['PUT'])
def update_task(task_id: str):
    """更新任务"""
    try:
        if task_id not in tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在',
            }), 404
        
        data = request.json
        
        with task_lock:
            tasks[task_id].update({
                'name': data.get('name', tasks[task_id]['name']),
                'keywords': data.get('keywords', tasks[task_id]['keywords']),
                'config': data.get('config', tasks[task_id]['config']),
                'updatedAt': datetime.now().isoformat(),
            })
        
        logger.info(f'Task updated: {task_id}')
        
        return jsonify({
            'code': 200,
            'message': '任务更新成功',
            'data': tasks[task_id],
        })
    except Exception as e:
        logger.error(f'Update task failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@collection_bp.route('/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id: str):
    """删除任务"""
    try:
        if task_id not in tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在',
            }), 404
        
        # 停止任务
        if task_id in tasks and tasks[task_id].get('crawler'):
            tasks[task_id]['crawler'].stop()
        
        with task_lock:
            del tasks[task_id]
            if task_id in task_logs:
                del task_logs[task_id]
            if task_id in task_data:
                del task_data[task_id]
        
        logger.info(f'Task deleted: {task_id}')
        
        return jsonify({
            'code': 200,
            'message': '任务删除成功',
        })
    except Exception as e:
        logger.error(f'Delete task failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@collection_bp.route('/tasks/<task_id>/start', methods=['POST'])
def start_task(task_id: str):
    """启动任务"""
    try:
        if task_id not in tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在',
            }), 404
        
        task = tasks[task_id]
        
        # 创建爬虫实例
        crawler = CrawlerTask(task_id, task['config'])
        task['crawler'] = crawler
        
        # 启动任务
        if crawler.start():
            logger.info(f'Task started: {task_id}')
            return jsonify({
                'code': 200,
                'message': '任务已启动',
            })
        else:
            return jsonify({
                'code': 400,
                'message': '任务已在运行中',
            }), 400
    except Exception as e:
        logger.error(f'Start task failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@collection_bp.route('/tasks/<task_id>/pause', methods=['POST'])
def pause_task(task_id: str):
    """暂停任务"""
    try:
        if task_id not in tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在',
            }), 404
        
        task = tasks[task_id]
        if 'crawler' in task:
            task['crawler'].pause()
            logger.info(f'Task paused: {task_id}')
            return jsonify({
                'code': 200,
                'message': '任务已暂停',
            })
        else:
            return jsonify({
                'code': 400,
                'message': '任务未运行',
            }), 400
    except Exception as e:
        logger.error(f'Pause task failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@collection_bp.route('/tasks/<task_id>/stop', methods=['POST'])
def stop_task(task_id: str):
    """停止任务"""
    try:
        if task_id not in tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在',
            }), 404
        
        task = tasks[task_id]
        if 'crawler' in task:
            task['crawler'].stop()
            logger.info(f'Task stopped: {task_id}')
            return jsonify({
                'code': 200,
                'message': '任务已停止',
            })
        else:
            return jsonify({
                'code': 400,
                'message': '任务未运行',
            }), 400
    except Exception as e:
        logger.error(f'Stop task failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@collection_bp.route('/tasks/<task_id>/resume', methods=['POST'])
def resume_task(task_id: str):
    """恢复暂停的任务"""
    try:
        if task_id not in tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在',
            }), 404
        
        task = tasks[task_id]
        if 'crawler' in task and task['crawler'].status == 'paused':
            task['crawler'].resume()
            logger.info(f'Task resumed: {task_id}')
            return jsonify({
                'code': 200,
                'message': '任务已恢复',
            })
        else:
            return jsonify({
                'code': 400,
                'message': '任务未处于暂停状态',
            }), 400
    except Exception as e:
        logger.error(f'Resume task failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@collection_bp.route('/tasks/<task_id>/logs', methods=['GET'])
def get_task_logs(task_id: str):
    """获取任务日志"""
    try:
        if task_id not in tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在',
            }), 404
        
        logs = task_logs.get(task_id, [])
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': logs,
        })
    except Exception as e:
        logger.error(f'Get task logs failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@collection_bp.route('/tasks/<task_id>/data', methods=['GET'])
def get_task_data(task_id: str):
    """获取任务采集的数据"""
    try:
        if task_id not in tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在',
            }), 404
        
        data = task_data.get(task_id, [])
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 20, type=int)
        
        if not data and DB_AVAILABLE:
            batch_id = None
            task = tasks.get(task_id, {})
            crawler = task.get('crawler') if isinstance(task, dict) else None
            if crawler:
                batch_id = getattr(crawler, 'batch_id', None)
            batch_id = batch_id or task.get('batch_id') if isinstance(task, dict) else None
            
            if batch_id:
                try:
                    db_data = get_db_service().get_weibos_by_batch(batch_id, page, page_size)
                    return jsonify({
                        'code': 200,
                        'message': 'success',
                        'data': db_data,
                    })
                except Exception as e:
                    logger.warning(f'Get task data from MySQL failed: {e}')
        
        start = (page - 1) * page_size
        end = start + page_size
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'list': data[start:end],
                'total': len(data),
                'page': page,
                'pageSize': page_size,
            },
        })
    except Exception as e:
        logger.error(f'Get task data failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@collection_bp.route('/tasks/<task_id>/analyze', methods=['POST'])
def analyze_task_data(task_id: str):
    """分析指定采集任务已入库的数据"""
    try:
        if task_id not in tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在',
            }), 404
        
        if not DB_AVAILABLE:
            return jsonify({
                'code': 503,
                'message': '数据库服务不可用',
            }), 503
        
        if not SENTIMENT_AVAILABLE:
            return jsonify({
                'code': 503,
                'message': '情感分析模块不可用',
            }), 503
        
        data = request.json or {}
        limit = data.get('limit', 500)
        task = tasks.get(task_id, {})
        crawler = task.get('crawler') if isinstance(task, dict) else None
        batch_id = getattr(crawler, 'batch_id', None) if crawler else None
        batch_id = batch_id or task.get('batch_id') if isinstance(task, dict) else None
        
        if not batch_id:
            return jsonify({
                'code': 400,
                'message': '任务暂无数据库批次，无法按任务分析',
            }), 400
        
        db = get_db_service()
        unprocessed = db.get_unprocessed_weibos(limit=limit, batch_id=batch_id)
        if not unprocessed:
            return jsonify({
                'code': 200,
                'message': '该任务无未分析微博',
                'data': {
                    'task_id': task_id,
                    'batch_id': batch_id,
                    'analyzed': 0,
                    'saved': 0,
                    'errors': 0,
                },
            })
        
        results = []
        for weibo in unprocessed:
            label, score = SentimentLexicon.analyze(weibo.get('content', ''))
            results.append({
                'weibo_id': weibo['weibo_id'],
                'hybrid_score': score,
                'dict_score': score,
                'bert_score': None,
                'sentiment_class': label,
                'confidence': abs(score),
                'analysis_method': 'lexicon',
                'model_version': 'v2.0.0',
                'processing_time_ms': 0,
            })
        
        save_result = db.save_sentiment_results(results)
        return jsonify({
            'code': 200,
            'message': f'任务情感分析完成，处理{save_result["saved"]}条',
            'data': {
                'task_id': task_id,
                'batch_id': batch_id,
                'input_count': len(unprocessed),
                'saved': save_result['saved'],
                'errors': save_result['errors'],
            },
        })
    except Exception as e:
        logger.error(f'Analyze task data failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@collection_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """获取统计信息"""
    try:
        total_tasks = len(tasks)
        running_tasks = sum(1 for t in tasks.values() if t['status'] == 'running')
        completed_tasks = sum(1 for t in tasks.values() if t['status'] == 'completed')
        failed_tasks = sum(1 for t in tasks.values() if t['status'] == 'failed')
        total_collected = sum(t.get('collected', 0) for t in tasks.values())
        total_failed = sum(t.get('failed', 0) for t in tasks.values())
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'totalTasks': total_tasks,
                'runningTasks': running_tasks,
                'completedTasks': completed_tasks,
                'failedTasks': failed_tasks,
                'totalCollected': total_collected,
                'totalFailed': total_failed,
                'successRate': round((total_collected / (total_collected + total_failed) * 100), 2) if (total_collected + total_failed) > 0 else 0,
            },
        })
    except Exception as e:
        logger.error(f'Get statistics failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@collection_bp.route('/update-cookie', methods=['POST'])
@log_api_call('/api/collection/update-cookie', 'POST')
def update_cookies():
    """Update cookie pool"""
    try:
        data = request.json
        cookies = data.get('cookies', [])
        
        if not cookies:
            return jsonify({
                'code': 400,
                'message': 'No cookies provided',
            }), 400
        
        # Update cookie pool
        results = cookie_pool.update_cookies(cookies)
        
        logger.info(f"Cookie pool updated: {results}")
        
        return jsonify({
            'code': 200,
            'message': 'Cookie pool updated successfully',
            'data': results,
        })
    except Exception as e:
        logger.error(f'Update cookies failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@collection_bp.route('/cookie-stats', methods=['GET'])
@log_api_call('/api/collection/cookie-stats', 'GET')
def get_cookie_stats():
    """Get cookie pool statistics"""
    try:
        stats = cookie_pool.get_stats()
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': stats,
        })
    except Exception as e:
        logger.error(f'Get cookie stats failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


# 健康检查
@collection_bp.route('/status', methods=['GET'])
def get_collection_status():
    """获取当前采集任务状态"""
    try:
        with task_lock:
            running_tasks = [
                {
                    'task_id': tid,
                    'status': t.get('status', 'unknown'),
                    'keyword': t.get('config', {}).get('keyword', ''),
                    'progress': t.get('progress', 0),
                }
                for tid, t in tasks.items()
                if isinstance(t, dict) and t.get('status') == 'running'
            ]
            # Also check CrawlerTask instances stored as objects
            for tid, t in tasks.items():
                if isinstance(t, CrawlerTask) and t.status == 'running':
                    running_tasks.append({
                        'task_id': tid,
                        'status': 'running',
                        'keyword': t.config.get('keyword', ''),
                        'progress': t.progress,
                    })

        status = 'running' if running_tasks else 'idle'
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'status': status,
                'active_tasks': running_tasks,
                'active_count': len(running_tasks),
            },
        })
    except Exception as e:
        logger.error(f"collection/status 异常: {e}", exc_info=True)
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'status': 'idle', 'active_tasks': [], 'active_count': 0},
        })


@collection_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'code': 200,
        'message': 'Collection service is running',
        'timestamp': datetime.now().isoformat(),
    })
