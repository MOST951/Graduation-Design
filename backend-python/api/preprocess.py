"""
数据预处理模块API
提供数据清洗、分词、特征提取等功能
数据持久化存储到文件系统
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import threading
import time
import random
import re
import logging
import json
import os
from typing import Dict, List, Optional

# 创建蓝图
preprocess_bp = Blueprint('preprocess', __name__, url_prefix='/api/preprocess')

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据存储目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'preprocess')
TASKS_FILE = os.path.join(DATA_DIR, 'tasks.json')

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 全局存储
preprocess_tasks: Dict[str, Dict] = {}
processed_data: Dict[str, List[Dict]] = {}
task_lock = threading.Lock()


def load_tasks_from_disk():
    """从磁盘加载任务列表"""
    global preprocess_tasks
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                preprocess_tasks = json.load(f)
            logger.info(f'已从磁盘加载 {len(preprocess_tasks)} 个预处理任务')
        except Exception as e:
            logger.error(f'加载任务列表失败: {e}')
            preprocess_tasks = {}


def save_tasks_to_disk():
    """保存任务列表到磁盘"""
    try:
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(preprocess_tasks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f'保存任务列表失败: {e}')


def get_task_data_file(task_id: str) -> str:
    """获取任务数据文件路径"""
    return os.path.join(DATA_DIR, f'task_{task_id}_data.json')


def save_task_data(task_id: str, data: List[Dict]):
    """保存任务数据到文件"""
    try:
        file_path = get_task_data_file(task_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f'任务 {task_id} 数据已保存到 {file_path}')
    except Exception as e:
        logger.error(f'保存任务数据失败: {e}')


def load_task_data(task_id: str) -> List[Dict]:
    """从文件加载任务数据"""
    file_path = get_task_data_file(task_id)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f'加载任务数据失败: {e}')
    return []


# 启动时加载任务
load_tasks_from_disk()


# ==================== 数据清洗函数 ====================

def remove_urls(text: str) -> str:
    """去除URL"""
    return re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

def remove_emoji(text: str) -> str:
    """去除表情符号"""
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub('', text)

def remove_special_chars(text: str) -> str:
    """去除特殊符号"""
    return re.sub(r'[#@【】\[\]「」『』（）\(\)《》<>""''"\'\`\~\!\@\#\$\%\^\&\*\_\+\=\|\\\{\}\;\:\,\.\?\/]+', ' ', text)

def remove_extra_spaces(text: str) -> str:
    """去除多余空格"""
    return re.sub(r'\s+', ' ', text).strip()

def clean_text(text: str, rules: List[str]) -> str:
    """根据规则清洗文本"""
    if 'removeUrl' in rules:
        text = remove_urls(text)
    if 'removeEmoji' in rules:
        text = remove_emoji(text)
    if 'removeSpecial' in rules:
        text = remove_special_chars(text)
    text = remove_extra_spaces(text)
    return text


# ==================== 分词函数 ====================

def segment_text(text: str, tool: str = 'jieba') -> List[str]:
    """分词"""
    try:
        import jieba
        if tool == 'jieba':
            return list(jieba.cut(text))
    except ImportError:
        pass
    # 简单分词（按空格和标点）
    return [w for w in re.split(r'\s+', text) if w]


# ==================== API路由 ====================

@preprocess_bp.route('/tasks', methods=['GET'])
def get_preprocess_tasks():
    """获取预处理任务列表"""
    try:
        task_list = list(preprocess_tasks.values())
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': task_list,
        })
    except Exception as e:
        logger.error(f'Get preprocess tasks failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@preprocess_bp.route('/tasks', methods=['POST'])
def create_preprocess_task():
    """创建预处理任务"""
    try:
        data = request.json or {}
        
        # 获取参数
        name = data.get('name', f'预处理任务_{int(time.time())}')
        source_task_id = data.get('sourceTaskId')  # 来源采集任务ID
        source_data = data.get('data', [])  # 直接传入的数据
        clean_rules = data.get('cleanRules', ['removeDuplicates', 'removeSpecial'])
        segment_tool = data.get('segmentTool', 'jieba')
        
        # 生成任务ID
        task_id = f'preprocess_{int(time.time() * 1000)}'
        
        # 如果指定了来源任务，从采集任务获取数据
        if source_task_id:
            from api.collection import task_data as collection_data
            source_data = collection_data.get(source_task_id, [])
        
        # 如果没有数据，尝试从爬虫数据加载
        if not source_data:
            source_data = load_weibo_crawl_data()
            if not source_data:
                return jsonify({
                    'code': 400,
                    'message': '没有可用的数据源，请先执行微博采集任务',
                }), 400
        
        # 处理数据
        processed_items = []
        seen_texts = set()
        
        for item in source_data:
            text = item.get('content') or item.get('text', '')
            
            # 去重
            if 'removeDuplicates' in clean_rules:
                if text in seen_texts:
                    continue
                seen_texts.add(text)
            
            # 清洗文本
            cleaned_text = clean_text(text, clean_rules)
            
            # 分词
            words = segment_text(cleaned_text, segment_tool)
            
            processed_item = {
                'id': item.get('id', f'{task_id}_{len(processed_items)}'),
                'original_text': text,
                'cleaned_text': cleaned_text,
                'words': words,
                'word_count': len(words),
                'source': item.get('source', 'unknown'),
                'keyword': item.get('keyword', ''),
                'author': item.get('author', ''),
                'timestamp': item.get('timestamp', datetime.now().isoformat()),
                # 保留原始互动数据
                'likes': item.get('likes', 0),
                'comments': item.get('comments', 0),
                'shares': item.get('shares', 0),
            }
            processed_items.append(processed_item)
        
        # 保存任务和数据
        task = {
            'id': task_id,
            'name': name,
            'sourceTaskId': source_task_id,
            'cleanRules': clean_rules,
            'segmentTool': segment_tool,
            'status': 'completed',
            'totalCount': len(source_data),
            'processedCount': len(processed_items),
            'createdAt': datetime.now().isoformat(),
        }
        
        with task_lock:
            preprocess_tasks[task_id] = task
            processed_data[task_id] = processed_items
            
            # 持久化保存到文件
            save_tasks_to_disk()
            save_task_data(task_id, processed_items)
        
        logger.info(f'Preprocess task created: {task_id}, processed {len(processed_items)} items')
        
        return jsonify({
            'code': 200,
            'message': '预处理任务创建成功',
            'data': task,
        })
        
    except Exception as e:
        logger.error(f'Create preprocess task failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@preprocess_bp.route('/tasks/<task_id>', methods=['GET'])
def get_preprocess_task(task_id: str):
    """获取预处理任务详情"""
    try:
        if task_id not in preprocess_tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在',
            }), 404
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': preprocess_tasks[task_id],
        })
    except Exception as e:
        logger.error(f'Get preprocess task failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@preprocess_bp.route('/tasks/<task_id>/data', methods=['GET'])
def get_preprocess_data(task_id: str):
    """获取预处理后的数据"""
    try:
        if task_id not in preprocess_tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在',
            }), 404
        
        # 优先从内存获取，如果没有则从文件加载
        data = processed_data.get(task_id)
        if data is None:
            data = load_task_data(task_id)
            if data:
                processed_data[task_id] = data  # 缓存到内存
        
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 100, type=int)
        
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
        logger.error(f'Get preprocess data failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@preprocess_bp.route('/tasks/<task_id>', methods=['DELETE'])
def delete_preprocess_task(task_id: str):
    """删除预处理任务"""
    try:
        if task_id not in preprocess_tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在',
            }), 404
        
        with task_lock:
            del preprocess_tasks[task_id]
            if task_id in processed_data:
                del processed_data[task_id]
            
            # 删除文件
            save_tasks_to_disk()
            data_file = get_task_data_file(task_id)
            if os.path.exists(data_file):
                os.remove(data_file)
        
        logger.info(f'Preprocess task deleted: {task_id}')
        
        return jsonify({
            'code': 200,
            'message': '任务删除成功',
        })
    except Exception as e:
        logger.error(f'Delete preprocess task failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@preprocess_bp.route('/preview', methods=['POST'])
def preview_preprocess():
    """预览预处理效果"""
    try:
        data = request.json or {}
        text = data.get('text', '')
        clean_rules = data.get('cleanRules', ['removeSpecial'])
        segment_tool = data.get('segmentTool', 'jieba')
        
        cleaned = clean_text(text, clean_rules)
        words = segment_text(cleaned, segment_tool)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'original': text,
                'cleaned': cleaned,
                'words': words,
                'wordCount': len(words),
            },
        })
    except Exception as e:
        logger.error(f'Preview preprocess failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


def load_weibo_crawl_data() -> List[Dict]:
    """从爬虫数据目录加载真实微博数据"""
    weibo_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    all_data = []
    
    try:
        for filename in os.listdir(weibo_data_dir):
            if filename.startswith('crawl_result_') and filename.endswith('.json'):
                filepath = os.path.join(weibo_data_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            # 转换为预处理所需格式
                            for item in data:
                                all_data.append({
                                    'id': item.get('id', ''),
                                    'content': item.get('text', ''),
                                    'source': 'weibo',
                                    'keyword': '',
                                    'author': item.get('user', {}).get('screen_name', ''),
                                    'likes': item.get('attitudes_count', 0),
                                    'comments': item.get('comments_count', 0),
                                    'shares': item.get('reposts_count', 0),
                                    'timestamp': item.get('crawl_time', datetime.now().isoformat()),
                                })
                except Exception as e:
                    logger.warning(f"加载文件 {filename} 失败: {e}")
        
        logger.info(f"从爬虫数据加载了 {len(all_data)} 条记录")
        return all_data
        
    except Exception as e:
        logger.error(f"加载爬虫数据失败: {e}")
        return []


# 健康检查
@preprocess_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'code': 200,
        'message': 'Preprocess service is running',
        'timestamp': datetime.now().isoformat(),
    })
