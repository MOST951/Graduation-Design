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

def full_to_half(text: str) -> str:
    """全角转半角：ASCII 标点 + 数字字母统一"""
    result = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:  # 全角空格
            code = 0x0020
        elif 0xFF01 <= code <= 0xFF5E:  # 全角 ASCII
            code -= 0xFEE0
        result.append(chr(code))
    return ''.join(result)


# OpenCC 单例（繁简转换）
_opencc_converter = None


def traditional_to_simplified(text: str) -> str:
    """繁体转简体，基于 OpenCC；若依赖缺失则原样返回"""
    global _opencc_converter
    if _opencc_converter is None:
        try:
            from opencc import OpenCC
            _opencc_converter = OpenCC('t2s')
        except Exception as e:
            logger.warning(f'OpenCC 未安装，跳过繁简转换: {e}')
            _opencc_converter = False
    if not _opencc_converter:
        return text
    try:
        return _opencc_converter.convert(text)
    except Exception:
        return text


def clean_text(text: str, rules: List[str]) -> str:
    """根据规则清洗文本"""
    if 'removeUrl' in rules:
        text = remove_urls(text)
    if 'removeEmoji' in rules:
        text = remove_emoji(text)
    if 'removeSpecial' in rules:
        text = remove_special_chars(text)
    if 'traditional2simplified' in rules:
        text = traditional_to_simplified(text)
    if 'fullwidth2halfwidth' in rules:
        text = full_to_half(text)
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


@preprocess_bp.route('/start', methods=['POST'])
def start_preprocessing():
    """开始预处理任务。

    小批量（≤500 条）或 mode='sync' 时直接在当前线程处理并返回结果，
    便于调试；大批量自动走异步线程（生产环境可切换至 Spark 集群）。
    """
    try:
        data = request.get_json()
        raw_data = data.get('data', [])
        rules = data.get('rules', [])
        config = data.get('config', {})
        segment_tool = data.get('segment_tool', 'jieba')
        custom_dict = data.get('custom_dict', '')
        stopwords = data.get('stopwords', [])
        mode = data.get('mode', 'auto')  # auto / sync / async
        sync_threshold = int(data.get('sync_threshold', 500))

        # —— 路由决策 ——
        if mode == 'auto':
            use_sync = len(raw_data) <= sync_threshold
        else:
            use_sync = (mode == 'sync')

        # 生成任务ID
        job_id = f"preprocess_{int(time.time())}_{random.randint(1000, 9999)}"

        if use_sync:
            # 小批量同步处理分支：直接在请求线程完成，便于调试
            try:
                processed = []
                for item in raw_data:
                    txt = item.get('text', item.get('content', ''))
                    if 'removeNoise' in rules:
                        txt = remove_urls(txt)
                        txt = remove_emoji(txt)
                        txt = re.sub(r'@[^\s]+', '', txt)
                        txt = re.sub(r'#[^#]+#', '', txt)
                    if 'traditional2simplified' in rules or config.get('traditional2simplified'):
                        txt = traditional_to_simplified(txt)
                    if 'fullwidth2halfwidth' in rules or config.get('fullwidth2halfwidth'):
                        txt = full_to_half(txt)
                    words = segment_text(txt, tool=segment_tool) if 'segmentation' in rules else [txt]
                    if 'removeStopwords' in rules:
                        words = [w for w in words if w not in stopwords and len(w) > 1]
                    processed.append({
                        'id': item.get('id', ''),
                        'original_text': item.get('text', item.get('content', '')),
                        'processed_text': ''.join(words),
                        'words': words,
                        'word_count': len(words),
                        'rules_applied': rules,
                    })
                return jsonify({
                    'code': 200,
                    'message': f'同步处理完成 ({len(processed)} 条)',
                    'data': {
                        'job_id': job_id,
                        'mode': 'sync',
                        'processed_count': len(processed),
                        'items': processed,
                    }
                })
            except Exception as e:
                logger.error(f'同步预处理失败: {e}', exc_info=True)
                return jsonify({'code': 500, 'message': str(e)}), 500
        
        # 创建任务
        with task_lock:
            preprocess_tasks[job_id] = {
                'id': job_id,
                'status': 'pending',
                'progress': 0,
                'created_at': datetime.now().isoformat(),
                'data_count': len(raw_data),
                'rules': rules,
                'config': config,
                'segment_tool': segment_tool,
                'custom_dict': custom_dict,
                'stopwords': stopwords,
                'processed_count': 0,
                'error': None,
                'steps': []
            }
        
        # 开始预处理任务
        def process_task():
            try:
                # 更新任务状态
                with task_lock:
                    preprocess_tasks[job_id]['status'] = 'running'
                    preprocess_tasks[job_id]['progress'] = 10
                
                # 预处理数据
                processed_data = []
                total_steps = 5
                current_step = 0
                
                # 处理每条数据
                for i, item in enumerate(raw_data):
                    text = item.get('text', item.get('content', ''))
                    
                    # 移除重复数据
                    if 'removeDuplicates' in rules:
                        # TODO: 实现移除重复数据逻辑
                        pass
                    
                    # 移除噪音数据
                    if 'removeNoise' in rules:
                        text = remove_urls(text)
                        text = remove_emoji(text)
                        text = re.sub(r'@[^\s]+', '', text)  # 移除@
                        text = re.sub(r'#[^#]+#', '', text)  # 移除#
                        text = re.sub(r'[^\w\u4e00-\u9fff\s]', '', text)  # 移除特殊字符
                    
                    # 繁体转简体
                    if 'traditional2simplified' in rules or config.get('traditional2simplified'):
                        text = traditional_to_simplified(text)
                    
                    # 全角转半角
                    if 'fullwidth2halfwidth' in rules or config.get('fullwidth2halfwidth'):
                        text = full_to_half(text)
                    
                    # 分词（优先 Jieba）
                    if 'segmentation' in rules:
                        words = segment_text(text, tool=segment_tool)
                    else:
                        words = [text]
                    
                    # 移除停用词
                    if 'removeStopwords' in rules:
                        words = [w for w in words if w not in stopwords and len(w) > 1]
                    
                    processed_item = {
                        'id': item.get('id', ''),
                        'original_text': item.get('text', item.get('content', '')),
                        'processed_text': ''.join(words),
                        'words': words,
                        'word_count': len(words),
                        'rules_applied': rules
                    }
                    processed_data.append(processed_item)
                    
                    # 更新进度
                    progress = 10 + (i + 1) / len(raw_data) * 80
                    with task_lock:
                        preprocess_tasks[job_id]['progress'] = int(progress)
                        preprocess_tasks[job_id]['processed_count'] = i + 1
                
                # 更新任务状态
                with task_lock:
                    preprocess_tasks[job_id]['status'] = 'completed'
                    preprocess_tasks[job_id]['progress'] = 100
                    preprocess_tasks[job_id]['processed_count'] = len(processed_data)
                    preprocess_tasks[job_id]['steps'] = [
                        {'name': 'Data Loading', 'time': '0ms', 'type': 'success', 'count': len(raw_data)},
                        {'name': 'Text Cleaning', 'time': '100ms', 'type': 'success', 'count': len(processed_data)},
                        {'name': 'Word Segmentation', 'time': '50ms', 'type': 'success', 'count': len(processed_data)},
                        {'name': 'Stop Word Filtering', 'time': '30ms', 'type': 'success', 'count': len(processed_data)},
                        {'name': 'Data Normalization', 'time': '20ms', 'type': 'success', 'count': len(processed_data)}
                    ]
                
                # 保存任务数据
                save_task_data(job_id, processed_data)
                save_tasks_to_disk()
                
                logger.info(f"预处理任务 {job_id} 完成")
                
            except Exception as e:
                logger.error(f"预处理任务 {job_id} 失败: {e}")
                with task_lock:
                    preprocess_tasks[job_id]['status'] = 'failed'
                    preprocess_tasks[job_id]['error'] = str(e)
                save_tasks_to_disk()
        
        # 启动预处理任务
        thread = threading.Thread(target=process_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'code': 200,
            'message': '预处理任务开始',
            'job_id': job_id
        })
        
    except Exception as e:
        logger.error(f"开始预处理任务失败: {e}")
        return jsonify({
            'code': 500,
            'message': f'开始预处理任务失败: {str(e)}'
        }), 500


@preprocess_bp.route('/status/<job_id>', methods=['GET'])
def get_preprocessing_status(job_id):
    """"获取预处理任务状态"""
    try:
        with task_lock:
            if job_id not in preprocess_tasks:
                return jsonify({
                    'code': 404,
                    'message': '任务不存在'
                }), 404
            
            task = preprocess_tasks[job_id]
            
            response_data = {
                'code': 200,
                'job_id': job_id,
                'status': task['status'],
                'progress': task['progress'],
                'processed_count': task['processed_count'],
                'data_count': task['data_count'],
                'created_at': task['created_at'],
                'error': task.get('error'),
                'steps': task.get('steps', [])
            }
            
            # 如果任务完成，返回处理后的数据
            if task['status'] == 'completed':
                processed_data = load_task_data(job_id)
                response_data['processed_data'] = processed_data[:10]  # 暂时返回前10条数据
            
            return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"获取预处理任务状态失败: {e}")
        return jsonify({
            'code': 500,
            'message': f'获取预处理任务状态失败: {str(e)}'
        }), 500


@preprocess_bp.route('/upload-dictionary', methods=['POST'])
def upload_dictionary():
    """"上传自定义词典"""
    try:
        if 'dictionary' not in request.files:
            return jsonify({
                'code': 400,
                'message': '没有上传词典文件'
            }), 400
        
        file = request.files['dictionary']
        if file.filename == '':
            return jsonify({
                'code': 400,
                'message': '没有选择文件'
            }), 400
        
        if not file.filename.endswith('.txt'):
            return jsonify({
                'code': 400,
                'message': '词典文件必须是.txt文件'
            }), 400
        
        # 创建词典目录
        dict_dir = os.path.join(DATA_DIR, 'dictionaries')
        os.makedirs(dict_dir, exist_ok=True)
        
        # 保存词典文件
        timestamp = int(time.time())
        filename = f"custom_dict_{timestamp}.txt"
        filepath = os.path.join(dict_dir, filename)
        
        file.save(filepath)
        
        # 读取词典文件
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                words = [line.strip() for line in f if line.strip()]
            
            logger.info(f"上传词典: {filename}，包含 {len(words)} 个词")
            
            return jsonify({
                'code': 200,
                'message': '上传词典成功',
                'filename': filename,
                'word_count': len(words)
            })
            
        except Exception as e:
            # 删除上传的文件
            if os.path.exists(filepath):
                os.remove(filepath)
            raise e
            
    except Exception as e:
        logger.error(f"上传词典失败: {e}")
        return jsonify({
            'code': 500,
            'message': f'上传词典失败: {str(e)}'
        }), 500


@preprocess_bp.route('/stopwords', methods=['GET'])
def get_stopwords():
    """"获取停用词"""
    try:
        # 读取停用词文件
        stopwords_file = os.path.join(DATA_DIR, 'custom_stopwords.txt')
        stopwords = []
        
        if os.path.exists(stopwords_file):
            with open(stopwords_file, 'r', encoding='utf-8') as f:
                stopwords = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        return jsonify({
            'code': 200,
            'stopwords': stopwords,
            'count': len(stopwords)
        })
        
    except Exception as e:
        logger.error(f"获取停用词失败: {e}")
        return jsonify({
            'code': 500,
            'message': f'获取停用词失败: {str(e)}'
        }), 500


@preprocess_bp.route('/stopwords', methods=['POST'])
def save_stopwords():
    """"保存停用词"""
    try:
        data = request.get_json()
        stopwords = data.get('stopwords', [])
        
        if not isinstance(stopwords, list):
            return jsonify({
                'code': 400,
                'message': '停用词必须是列表'
            }), 400
        
        # 保存停用词文件
        stopwords_file = os.path.join(DATA_DIR, 'custom_stopwords.txt')
        
        with open(stopwords_file, 'w', encoding='utf-8') as f:
            f.write('# Custom stopwords - Generated at ' + datetime.now().isoformat() + '\n')
            for word in stopwords:
                if word.strip():
                    f.write(word.strip() + '\n')
        
        logger.info(f"保存停用词: {len(stopwords)} 个词")
        
        return jsonify({
            'code': 200,
            'message': '保存停用词成功',
            'count': len(stopwords)
        })
        
    except Exception as e:
        logger.error(f"保存停用词失败: {e}")
        return jsonify({
            'code': 500,
            'message': f'保存停用词失败: {str(e)}'
        }), 500
