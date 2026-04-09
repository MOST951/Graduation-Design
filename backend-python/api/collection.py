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
import logging

# 添加路径以导入爬虫模块
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 导入微博爬虫
try:
    from crawler.weibo_crawler import WeiboCrawler
    CRAWLER_AVAILABLE = True
except ImportError as e:
    CRAWLER_AVAILABLE = False
    logging.warning(f"爬虫模块导入失败: {e}")

# 导入数据库服务
try:
    from services.database_service import get_db_service
    DB_AVAILABLE = True
except ImportError as e:
    DB_AVAILABLE = False
    logging.warning(f"数据库服务导入失败: {e}")

# 创建蓝图
collection_bp = Blueprint('collection', __name__, url_prefix='/api/collection')

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        self.thread: Optional[threading.Thread] = None
        self.batch_id: Optional[str] = None
        self._weibo_buffer: List[Dict] = []  # 批量入库缓冲
        self._buffer_size = 50  # 每50条刷入MySQL
        
    def start(self):
        """启动任务"""
        if self.is_running:
            return False
            
        self.is_running = True
        self.status = 'running'
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        return True
        
    def pause(self):
        """暂停任务"""
        self.is_running = False
        self.status = 'paused'
        
    def stop(self):
        """停止任务"""
        self.is_running = False
        self.status = 'stopped'
        
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
                    if not self.is_running:
                        break
                    
                    self._log('info', f'正在搜索关键词: {keyword}')
                    
                    try:
                        # 搜索微博
                        page = 1
                        while self.is_running and self.collected < max_count and page <= 5:
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
            
            # 任务完成
            if self.collected >= max_count:
                self.status = 'completed'
                self.progress = 100
                self._log('success', f'任务完成，共采集 {self.collected} 条数据，已入库MySQL')
            elif self.collected > 0:
                self.status = 'completed'
                self.progress = 100
                self._log('success', f'任务完成，共采集 {self.collected} 条数据，已入库MySQL')
            else:
                self.status = 'failed'
                self._log('error', f'未采集到数据')
                
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
                    'updatedAt': datetime.now().isoformat(),
                })


# ==================== API路由 ====================

@collection_bp.route('/tasks', methods=['GET'])
def get_tasks():
    """获取任务列表"""
    try:
        task_list = list(tasks.values())
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


# 健康检查
@collection_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'code': 200,
        'message': 'Collection service is running',
        'timestamp': datetime.now().isoformat(),
    })
