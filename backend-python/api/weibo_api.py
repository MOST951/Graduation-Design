"""
微博数据采集与分析API
整合真实爬虫和Spark情感分析
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import threading
import time
import os
import json
from typing import Dict, List
import logging

# 导入爬虫和分析模块
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from crawler.weibo_crawler import WeiboCrawler, WeiboCrawlerTask
from spark.sentiment_analyzer import (
    SparkSentimentAnalyzer, 
    SentimentLexicon,
    SparkClusterManager,
    analyze_weibo_sentiment
)
from spark.tri_dimension_model import (
    TriDimensionRankingModel,
    TriDimensionConfig,
    rank_weibo_data,
    WeiboItem
)
from spark.bert_sentiment import (
    ChineseBERTSentimentAnalyzer,
    HybridSentimentAnalyzer,
    analyze_sentiment_bert,
    analyze_sentiment_hybrid
)

# 创建蓝图
weibo_bp = Blueprint('weibo', __name__, url_prefix='/api/weibo')

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据存储目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# 元数据文件路径 (模拟MySQL元数据表)
METADATA_FILE = os.path.join(DATA_DIR, 'metadata_tasks.json')
ANALYSIS_META_FILE = os.path.join(DATA_DIR, 'metadata_analysis.json')

# 全局状态
crawl_tasks: Dict[str, Dict] = {}
analysis_results: Dict[str, Dict] = {}
task_lock = threading.Lock()

def load_metadata():
    """加载元数据 (系统启动时调用)"""
    global crawl_tasks, analysis_results
    try:
        if os.path.exists(METADATA_FILE):
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                crawl_tasks = json.load(f)
            logger.info(f"已加载 {len(crawl_tasks)} 条采集任务记录")
            
            # 将服务重启前未完成的任务标记为失败
            interrupted = 0
            for tid, task in crawl_tasks.items():
                if task.get('status') in ('crawling', 'processing', 'running'):
                    task['status'] = 'failed'
                    task['error'] = '服务重启，任务中断'
                    task['end_time'] = datetime.now().isoformat()
                    # 同步更新 phases 中正在运行的阶段
                    for phase in task.get('phases', {}).values():
                        if phase.get('status') == 'running':
                            phase['status'] = 'failed'
                    interrupted += 1
            if interrupted:
                logger.warning(f"已将 {interrupted} 个中断任务标记为失败")
                save_metadata()
            
        if os.path.exists(ANALYSIS_META_FILE):
            with open(ANALYSIS_META_FILE, 'r', encoding='utf-8') as f:
                analysis_results = json.load(f)
            logger.info(f"已加载 {len(analysis_results)} 条分析结果记录")
    except Exception as e:
        logger.error(f"加载元数据失败: {e}")

def save_metadata():
    """保存元数据 (数据变更时调用)"""
    try:
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(crawl_tasks, f, ensure_ascii=False, indent=2)
            
        with open(ANALYSIS_META_FILE, 'w', encoding='utf-8') as f:
            # 分析结果可能很大，元数据只存摘要信息，这里简化处理直接存
            # 实际生产环境应存数据库
            json.dump(analysis_results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存元数据失败: {e}")

def _sync_metadata_to_memory():
    """将磁盘上已持久化但内存中缺失的任务合并回 crawl_tasks。
    仅添加缺失的 key，不覆盖正在运行的任务的内存状态。"""
    try:
        if not os.path.exists(METADATA_FILE):
            return
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            disk_tasks = json.load(f)
        merged = 0
        with task_lock:
            for tid, tinfo in disk_tasks.items():
                if tid not in crawl_tasks:
                    crawl_tasks[tid] = tinfo
                    merged += 1
        if merged:
            logger.info(f"从磁盘合并了 {merged} 个缺失任务到内存")
    except Exception as e:
        logger.warning(f"_sync_metadata_to_memory 失败: {e}")

# 初始化时加载元数据
load_metadata()


# ==================== 热搜相关API ====================

@weibo_bp.route('/hotsearch', methods=['GET'])
def get_hot_search():
    """
    获取微博热搜榜
    真实从微博爬取数据
    """
    try:
        crawler = WeiboCrawler()
        hot_list = crawler.get_hot_search()
        
        if not hot_list:
            # 如果爬取失败，返回缓存数据
            cache_file = os.path.join(DATA_DIR, 'hotsearch_cache.json')
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    hot_list = json.load(f)
            else:
                return jsonify({
                    'code': 500,
                    'message': '获取热搜失败，请稍后重试',
                    'data': []
                }), 500
        else:
            # 缓存数据
            cache_file = os.path.join(DATA_DIR, 'hotsearch_cache.json')
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(hot_list, f, ensure_ascii=False)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': hot_list,
            'crawl_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f'获取热搜失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
            'data': []
        }), 500


# ==================== 微博搜索API ====================

@weibo_bp.route('/search', methods=['GET'])
def search_weibo():
    """
    搜索微博
    
    Query参数:
        keyword: 搜索关键词
        page: 页码 (默认1)
        type: 搜索类型 (all/hot/ori)
        analyze: 是否进行情感分析 (true/false)
    """
    try:
        keyword = request.args.get('keyword', '')
        page = int(request.args.get('page', 1))
        search_type = request.args.get('type', 'all')
        do_analyze = request.args.get('analyze', 'true').lower() == 'true'
        
        if not keyword:
            return jsonify({
                'code': 400,
                'message': '关键词不能为空',
                'data': []
            }), 400
        
        crawler = WeiboCrawler()
        weibo_list = list(crawler.search_weibo(keyword, page, search_type))
        
        # 情感分析
        if do_analyze and weibo_list:
            for weibo in weibo_list:
                sentiment, score = SentimentLexicon.analyze(weibo.get('text', ''))
                weibo['sentiment'] = sentiment
                weibo['sentiment_score'] = score
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': weibo_list,
            'total': len(weibo_list),
            'keyword': keyword,
            'page': page
        })
        
    except Exception as e:
        logger.error(f'搜索微博失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
            'data': []
        }), 500


# ==================== 话题微博API ====================

@weibo_bp.route('/topic', methods=['GET'])
def get_topic_weibo():
    """
    获取话题微博
    
    Query参数:
        topic: 话题名称
        page: 页码 (默认1)
        analyze: 是否进行情感分析
    """
    try:
        topic = request.args.get('topic', '')
        page = int(request.args.get('page', 1))
        do_analyze = request.args.get('analyze', 'true').lower() == 'true'
        
        if not topic:
            return jsonify({
                'code': 400,
                'message': '话题不能为空',
                'data': []
            }), 400
        
        crawler = WeiboCrawler()
        weibo_list = list(crawler.get_topic_weibo(topic, page))
        
        # 情感分析
        if do_analyze and weibo_list:
            for weibo in weibo_list:
                sentiment, score = SentimentLexicon.analyze(weibo.get('text', ''))
                weibo['sentiment'] = sentiment
                weibo['sentiment_score'] = score
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': weibo_list,
            'total': len(weibo_list),
            'topic': topic,
            'page': page
        })
        
    except Exception as e:
        logger.error(f'获取话题微博失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
            'data': []
        }), 500


# ==================== 批量采集任务API ====================

# 论文 6.1.1 + 3.3.1 性能要求: 单批最多 50000 条, 关键词每个 ≤64 字符, 关键词条数 ≤20.
MAX_KEYWORDS = 20
MAX_KEYWORD_LEN = 64
MAX_PAGES = 50
MAX_COUNT = 50000


def _validate_crawl_params(data: dict):
    """启动采集任务的入参校验. 返回 (cleaned_dict, error_msg_or_None).

    论文 6.1.1: 关键词为空 / 采集数量 > 50000 → 阻止提交.
    后端做硬校验, 不依赖前端 (任何客户端直接 POST 都会被拦截).
    """
    if not isinstance(data, dict):
        return None, '请求体必须是 JSON 对象'

    keywords = data.get('keywords', [])
    pages = data.get('pages', 50)
    crawl_hot = bool(data.get('crawl_hot', True))
    max_count = data.get('max_count', 0)
    mode = (data.get('mode') or 'auto').lower()

    # keywords
    if not isinstance(keywords, list):
        return None, 'keywords 必须是数组'
    keywords = [str(k).strip() for k in keywords if str(k).strip()]
    if not keywords and not crawl_hot:
        return None, 'keywords 不能为空 (除非同时开启 crawl_hot)'
    if len(keywords) > MAX_KEYWORDS:
        return None, f'keywords 数量超过上限 {MAX_KEYWORDS}'
    for kw in keywords:
        if len(kw) > MAX_KEYWORD_LEN:
            return None, f'关键词过长 (>{MAX_KEYWORD_LEN}字符): {kw[:30]}...'

    # pages
    try:
        pages = int(pages)
    except (TypeError, ValueError):
        return None, 'pages 必须是整数'
    if pages < 1 or pages > MAX_PAGES:
        return None, f'pages 必须在 1-{MAX_PAGES} 之间'

    # max_count (可选)
    if max_count:
        try:
            max_count = int(max_count)
        except (TypeError, ValueError):
            return None, 'max_count 必须是整数'
        if max_count < 1 or max_count > MAX_COUNT:
            return None, f'max_count 必须在 1-{MAX_COUNT} 之间'
    else:
        max_count = 0

    # mode
    if mode not in ('auto', 'real', 'synthetic'):
        return None, "mode 必须是 'auto' | 'real' | 'synthetic'"

    return {
        'keywords': keywords,
        'pages': pages,
        'crawl_hot': crawl_hot,
        'max_count': max_count,
        'mode': mode,
    }, None


def _classify_data_source(rows: list) -> dict:
    """识别数据来源: 真爬 vs 模板合成.

    `_generate_keyword_data` 给合成数据打的 id 形如 `gen_<ts>_<i>`,
    据此区分; 答辩演示时透明显示数据来源, 论文 2.2.1 称 "API 为主, 爬虫为辅",
    无 cookies 时回落到合成是允许的, 但要让用户知情.
    """
    real = sum(1 for d in rows if not str(d.get('id', '')).startswith('gen_'))
    syn = len(rows) - real
    if not rows:
        source = 'empty'
    elif syn == 0:
        source = 'real'
    elif real == 0:
        source = 'synthetic'
    else:
        source = 'mixed'
    return {'data_source': source, 'real_count': real, 'synthetic_count': syn}


@weibo_bp.route('/crawl/cookie/status', methods=['GET'])
def cookie_status():
    """获取当前Cookie状态"""
    try:
        from crawler.cookie_grabber import get_cookie_status
        status = get_cookie_status()
        return jsonify({'code': 200, **status})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500


@weibo_bp.route('/crawl/cookie/grab', methods=['POST'])
def cookie_grab():
    """阶段1: 启动Selenium扫码，返回session_id和二维码"""
    try:
        data = request.json or {}
        timeout = min(int(data.get('timeout', 120)), 180)

        from crawler.cookie_grabber import start_qr_session
        result = start_qr_session(timeout=timeout)
        return jsonify({'code': 200, **result})
    except Exception as e:
        logger.error(f"Cookie抓取异常: {e}", exc_info=True)
        return jsonify({'code': 500, 'status': 'error', 'message': str(e)}), 500


@weibo_bp.route('/crawl/cookie/poll', methods=['GET'])
def cookie_poll():
    """阶段2: 前端轮询扫码状态"""
    session_id = request.args.get('session_id', '')
    if not session_id:
        return jsonify({'code': 400, 'status': 'error', 'message': '缺少session_id'}), 400

    from crawler.cookie_grabber import poll_qr_session
    result = poll_qr_session(session_id)
    return jsonify({'code': 200, **result})


@weibo_bp.route('/crawl/cookie/refresh', methods=['POST'])
def cookie_refresh():
    """用已有Cookie刷新/续期"""
    try:
        from crawler.cookie_grabber import refresh_cookies
        result = refresh_cookies()
        code = 200 if result['success'] else 400
        return jsonify({'code': code, **result}), 200
    except Exception as e:
        return jsonify({'code': 500, 'success': False, 'message': str(e)}), 500


@weibo_bp.route('/crawl/cookie/save', methods=['POST'])
def cookie_save():
    """手动保存用户粘贴的Cookie字符串"""
    try:
        data = request.json or {}
        cookie_str = data.get('cookie', '').strip()
        if not cookie_str:
            return jsonify({'code': 400, 'success': False, 'message': 'Cookie为空'}), 400

        # 解析 "key=value; key2=value2" 格式
        cookie_dict = {}
        for part in cookie_str.split(';'):
            part = part.strip()
            if '=' in part:
                k, v = part.split('=', 1)
                cookie_dict[k.strip()] = v.strip()

        if 'SUB' not in cookie_dict:
            return jsonify({'code': 400, 'success': False,
                            'message': 'Cookie缺少SUB字段，请确保复制了完整的微博Cookie'})

        from crawler.cookie_grabber import save_cookies
        save_cookies(cookie_dict)
        return jsonify({
            'code': 200, 'success': True,
            'message': f'Cookie已保存（{len(cookie_dict)}个字段）',
            'fields': list(cookie_dict.keys()),
        })
    except Exception as e:
        return jsonify({'code': 500, 'success': False, 'message': str(e)}), 500


@weibo_bp.route('/crawl/validate-cookie', methods=['POST'])
def validate_cookie():
    """验证Cookie是否有效（含SUB且未过期）"""
    try:
        data = request.json or {}
        cookie = data.get('cookie', '').strip()
        if not cookie:
            return jsonify({'code': 400, 'valid': False, 'message': 'Cookie为空'}), 400
        if 'SUB=' not in cookie:
            return jsonify({'code': 200, 'valid': False,
                            'message': 'Cookie缺少SUB字段，请从weibo.com完整复制Cookie'})

        # 用该Cookie请求一个轻量API验证是否过期
        import requests as req
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://weibo.com/',
            'Cookie': cookie,
        }
        xsrf = ''
        for part in cookie.split(';'):
            p = part.strip()
            if p.startswith('XSRF-TOKEN='):
                xsrf = p.split('=', 1)[1]
                break
        if xsrf:
            headers['X-XSRF-TOKEN'] = xsrf

        resp = req.get('https://weibo.com/ajax/side/hotSearch', headers=headers, timeout=10)
        rdata = resp.json()
        if 'data' in rdata and 'realtime' in rdata.get('data', {}):
            count = len(rdata['data']['realtime'])
            return jsonify({'code': 200, 'valid': True,
                            'message': f'Cookie有效，热搜API返回{count}条结果'})
        else:
            return jsonify({'code': 200, 'valid': False,
                            'message': 'Cookie已失效，请重新登录weibo.com获取'})
    except Exception as e:
        return jsonify({'code': 500, 'valid': False, 'message': f'验证异常: {str(e)}'}), 500


@weibo_bp.route('/crawl/start', methods=['POST'])
def start_crawl_task():
    """
    启动批量采集任务

    Body 参数:
        keywords:    关键词列表 (最多 20 个, 每个 ≤64 字符)
        pages:       每个关键词爬取页数 (1-50, 默认 3)
        crawl_hot:   是否爬取热搜话题 (默认 true)
        max_count:   单批最大采集条数, 1-50000, 0 表示不限 (论文 6.1.1)
        mode:        'auto'(默认, 真爬+合成兜底) | 'real'(只真爬) | 'synthetic'(纯合成,演示用)
    """
    try:
        cleaned, err = _validate_crawl_params(request.json or {})
        if err:
            return jsonify({'code': 400, 'message': err}), 400

        keywords  = cleaned['keywords']
        pages     = cleaned['pages']
        crawl_hot = cleaned['crawl_hot']
        max_count = cleaned['max_count']
        mode      = cleaned['mode']
        cookie    = (request.json or {}).get('cookie', '').strip() or None

        # 创建任务ID
        task_id = f"crawl_{int(time.time() * 1000)}"

        # 创建任务记录
        task_info = {
            'id': task_id,
            'status': 'running',
            'keywords': keywords,
            'pages': pages,
            'crawl_hot': crawl_hot,
            'max_count': max_count,
            'mode': mode,
            'progress': 0,
            'collected': 0,
            'data_source': None,   # real / synthetic / mixed / empty (run_crawl 完成后填充)
            'real_count': 0,
            'synthetic_count': 0,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'result_file': None,
            'error': None,
        }
        
        with task_lock:
            crawl_tasks[task_id] = task_info
            save_metadata()  # 保存任务记录
        
        # 在后台线程执行爬取
        def run_crawl():
            crawler_task = None
            try:
                crawler_task = WeiboCrawlerTask(os.path.join(DATA_DIR, 'weibo_raw'), cookie=cookie)
                all_data = []

                # ---- mode='synthetic': 跳过网络, 直接生成模板数据 (演示场景, 论文 2.2.1) ----
                if mode == 'synthetic':
                    task_info['progress'] = 30
                    target_kws = keywords or ['热门话题']
                    for kw in target_kws:
                        all_data.extend(crawler_task._generate_keyword_data(kw, count=pages * 10))
                    task_info['progress'] = 80
                else:
                    # ---- mode='real' / 'auto': 优先真爬虫 ----
                    if crawl_hot:
                        task_info['progress'] = 10
                        try:
                            crawler_task.crawl_hot_search(save=True)
                            task_info['progress'] = 20
                            hot_weibo = crawler_task.crawl_hot_topics(
                                top_n=5, pages_per_topic=pages, save=True
                            )
                            all_data.extend(hot_weibo)
                            task_info['progress'] = 50
                        except Exception as e:
                            logger.warning(f"[{task_id}] 热搜爬取部分失败: {e}")

                    if keywords:
                        try:
                            # 每页实时回调: 把已爬条数 + 数据快照写入 task_info, 让 /crawl/data API
                            # 在运行中也能向前端返回中间数据 (用户在"本次采集任务数据预览"卡片实时看到累积)
                            def _on_page(kw, page_idx, total_pages, partial):
                                try:
                                    snapshot = list(all_data) + list(partial)
                                    task_info['partial_data'] = snapshot
                                    task_info['collected'] = len(snapshot)
                                    # 关键词阶段占 progress 30~80, 按页推进
                                    pct = 30 + int(min(page_idx, total_pages) / max(total_pages, 1) * 50)
                                    task_info['progress'] = min(pct, 79)
                                except Exception:
                                    pass

                            kw_weibo = crawler_task.crawl_by_keywords(
                                keywords, pages=pages, save=True,
                                progress_callback=_on_page,
                            )
                            all_data.extend(kw_weibo)
                        except Exception as e:
                            logger.warning(f"[{task_id}] 关键词爬取部分失败: {e}")

                    task_info['progress'] = 80

                    # ---- mode='real' 严格模式: 拒绝合成兜底, 直接报错让用户配 cookies ----
                    if mode == 'real':
                        # WeiboCrawlerTask.crawl_by_keywords 内部已有合成兜底,
                        # 这里通过 id 前缀判断是否被兜底, 若是则视为真爬失败.
                        info = _classify_data_source(all_data)
                        if info['real_count'] == 0:
                            raise RuntimeError(
                                f"mode=real 要求真爬数据, 但实际获取 0 条真实数据, "
                                f"{info['synthetic_count']} 条合成数据已丢弃. "
                                f"请检查 cookies/网络. 演示场景请改用 mode=auto 或 mode=synthetic."
                            )
                        # 过滤掉合成数据, 只保留真爬
                        all_data = [d for d in all_data if not str(d.get('id', '')).startswith('gen_')]

                # ---- max_count 截断 ----
                if max_count and len(all_data) > max_count:
                    logger.info(f"[{task_id}] 采集 {len(all_data)} 条 > max_count={max_count}, 截断")
                    all_data = all_data[:max_count]

                # ---- 数据来源分类 (透明化, 答辩可解释) ----
                src_info = _classify_data_source(all_data)
                task_info.update(src_info)
                logger.info(f"[{task_id}] 数据来源: {src_info}")

                if not all_data:
                    logger.warning(f"[{task_id}] 爬取数据为空, 请检查网络/Cookie 配置")
                    task_info['note'] = '未获取到数据，请检查爬虫配置'

                task_info['collected'] = len(all_data)
                
                # 保存汇总数据
                result_file = os.path.join(
                    DATA_DIR, 
                    f'crawl_result_{task_id}.json'
                )
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2)
                
                task_info['result_file'] = result_file
                task_info['progress'] = 90

                # 论文 5.1: 按日期分区上传到 HDFS /raw/dt=YYYY-MM-DD/
                try:
                    from utils.hdfs_client import upload_raw_to_hdfs_partitioned
                    hdfs_path = upload_raw_to_hdfs_partitioned(result_file, task_id)
                    if hdfs_path:
                        task_info['hdfs_path'] = hdfs_path
                        logger.info(f"[{task_id}] HDFS 同步成功: {hdfs_path}")
                    else:
                        task_info['hdfs_path'] = None
                        logger.warning(f"[{task_id}] HDFS 同步失败/跳过, 仅本地保存")
                except Exception as e:
                    # HDFS 同步失败不影响采集任务整体成功
                    logger.warning(f"[{task_id}] HDFS 同步异常: {e}")
                    task_info['hdfs_path'] = None

                task_info['status'] = 'completed'
                task_info['progress'] = 100
                task_info['end_time'] = datetime.now().isoformat()
                save_metadata()  # 任务完成后保存状态
                
            except Exception as e:
                logger.error(f'爬取任务失败: {e}', exc_info=True)
                task_info['status'] = 'failed'
                task_info['error'] = str(e)
                task_info['end_time'] = datetime.now().isoformat()
                save_metadata()  # 任务失败保存状态
            finally:
                # 释放 Selenium 浏览器等资源
                if crawler_task:
                    try:
                        crawler_task.close()
                    except Exception:
                        pass
        
        thread = threading.Thread(target=run_crawl)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'code': 200,
            'message': '采集任务已启动',
            'data': task_info
        })
        
    except Exception as e:
        logger.error(f'启动采集任务失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/crawl/status/<task_id>', methods=['GET'])
def get_crawl_status(task_id: str):
    """获取采集任务状态"""
    try:
        if task_id not in crawl_tasks:
            _sync_metadata_to_memory()   # 尝试从磁盘恢复
        if task_id not in crawl_tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在'
            }), 404
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': crawl_tasks[task_id]
        })
        
    except Exception as e:
        logger.error(f'获取任务状态失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/crawl/tasks', methods=['GET'])
def get_crawl_tasks():
    """获取所有采集任务列表"""
    try:
        # 安全网: 将磁盘上已持久化但内存中缺失的任务合并回来
        # (解决 gunicorn 多 worker / 服务重启后内存丢失问题)
        _sync_metadata_to_memory()

        # 获取任务列表，按时间倒序
        tasks_list = list(crawl_tasks.values())
        tasks_list.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'tasks': tasks_list,
                'total': len(tasks_list),
                'completed': sum(1 for t in tasks_list if t['status'] == 'completed'),
                'running': sum(1 for t in tasks_list if t['status'] == 'running')
            }
        })
        
    except Exception as e:
        logger.error(f'获取任务列表失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/crawl/data/<task_id>', methods=['GET'])
def get_crawl_data(task_id: str):
    """获取采集任务的数据"""
    try:
        if task_id not in crawl_tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在'
            }), 404
        
        task_info = crawl_tasks[task_id]

        # 运行中任务: 返回内存中的中间快照 (progress_callback 实时写入)
        if task_info.get('status') != 'completed':
            partial = task_info.get('partial_data') or []
            page = request.args.get('page', 1, type=int)
            page_size = request.args.get('page_size', 50, type=int)
            total = len(partial)
            start = (page - 1) * page_size
            paginated = partial[start: start + page_size]
            return jsonify({
                'code': 200,
                'message': '任务进行中, 返回当前已采集的中间数据',
                'data': {
                    'items': paginated,
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'is_partial': True,
                    'task_info': {
                        'id': task_info.get('id'),
                        'keywords': task_info.get('keywords'),
                        'collected': task_info.get('collected', 0),
                        'progress': task_info.get('progress', 0),
                        'status': task_info.get('status'),
                        'start_time': task_info.get('start_time'),
                    }
                }
            })

        result_file = task_info.get('result_file')
        if not result_file or not os.path.exists(result_file):
            return jsonify({
                'code': 404,
                'message': '数据文件不存在'
            }), 404
        
        # 读取数据
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 支持分页
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_data = data[start:end]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'items': paginated_data,
                'total': total,
                'page': page,
                'page_size': page_size,
                'task_info': {
                    'id': task_info['id'],
                    'keywords': task_info['keywords'],
                    'collected': task_info['collected'],
                    'start_time': task_info['start_time'],
                    'end_time': task_info.get('end_time')
                }
            }
        })
        
    except Exception as e:
        logger.error(f'获取任务数据失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== Spark分析API ====================

@weibo_bp.route('/analyze', methods=['POST'])
def analyze_data():
    """
    使用Spark进行情感分析
    
    Body参数:
        task_id: 采集任务ID (可选，使用已采集的数据)
        data: 微博数据列表 (可选，直接分析)
        use_spark: 是否使用Spark (默认true)
    """
    try:
        data = request.json or {}
        task_id = data.get('task_id')
        weibo_data = data.get('data', [])
        use_spark = data.get('use_spark', True)
        
        # 如果指定了任务ID，从文件加载数据
        if task_id and task_id in crawl_tasks:
            result_file = crawl_tasks[task_id].get('result_file')
            if result_file and os.path.exists(result_file):
                with open(result_file, 'r', encoding='utf-8') as f:
                    weibo_data = json.load(f)
        
        if not weibo_data:
            return jsonify({
                'code': 400,
                'message': '没有可分析的数据'
            }), 400
        
        # 创建分析任务ID
        analysis_id = f"analysis_{int(time.time() * 1000)}"
        
        # 执行分析
        analyzer = SparkSentimentAnalyzer()
        analyzed_data = analyzer.analyze_batch(weibo_data)
        stats = analyzer.get_statistics(analyzed_data)
        keyword_stats = analyzer.get_keyword_sentiment(analyzed_data)
        time_series = analyzer.get_time_series(analyzed_data)
        
        # 保存分析结果
        result = {
            'id': analysis_id,
            'data': analyzed_data,
            'statistics': stats,
            'keyword_stats': keyword_stats,
            'time_series': time_series,
            'analysis_time': datetime.now().isoformat()
        }
        
        analysis_results[analysis_id] = result
        save_metadata()  # 保存分析结果记录
        
        # 保存到文件
        result_file = os.path.join(DATA_DIR, f'analysis_{analysis_id}.json')
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'code': 200,
            'message': '分析完成',
            'data': {
                'id': analysis_id,
                'results': analyzed_data,  # 返回分析后的数据列表
                'statistics': stats,
                'keyword_stats': keyword_stats,
                'time_series': time_series,
                'total_analyzed': len(analyzed_data)
            }
        })
        
    except Exception as e:
        logger.error(f'分析失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/analyze/<analysis_id>', methods=['GET'])
def get_analysis_result(analysis_id: str):
    """获取分析结果"""
    try:
        if analysis_id in analysis_results:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': analysis_results[analysis_id]
            })
        
        # 尝试从文件加载
        result_file = os.path.join(DATA_DIR, f'analysis_{analysis_id}.json')
        if os.path.exists(result_file):
            with open(result_file, 'r', encoding='utf-8') as f:
                result = json.load(f)
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': result
            })
        
        return jsonify({
            'code': 404,
            'message': '分析结果不存在'
        }), 404
        
    except Exception as e:
        logger.error(f'获取分析结果失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== Spark集群信息API ====================

@weibo_bp.route('/spark/info', methods=['GET'])
def get_spark_info():
    """获取Spark集群信息"""
    try:
        manager = SparkClusterManager()
        info = manager.get_cluster_info()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': info
        })
        
    except Exception as e:
        logger.error(f'获取Spark信息失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 数据统计API ====================

@weibo_bp.route('/stats/overview', methods=['GET'])
def get_overview_stats():
    """获取数据概览统计"""
    try:
        # 统计已采集的数据
        raw_dir = os.path.join(DATA_DIR, 'weibo_raw')
        total_files = 0
        total_records = 0
        
        if os.path.exists(raw_dir):
            for filename in os.listdir(raw_dir):
                if filename.endswith('.json'):
                    total_files += 1
                    filepath = os.path.join(raw_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            total_records += len(data) if isinstance(data, list) else 1
                    except:
                        pass
        
        # 统计分析结果
        total_analyses = len(analysis_results)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total_crawl_tasks': len(crawl_tasks),
                'total_data_files': total_files,
                'total_records': total_records,
                'total_analyses': total_analyses,
                'active_tasks': sum(1 for t in crawl_tasks.values() if t['status'] == 'running'),
                'update_time': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f'获取统计信息失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 实时分析API ====================

@weibo_bp.route('/realtime/analyze', methods=['POST'])
def realtime_analyze():
    """
    实时分析单条文本
    
    Body参数:
        text: 要分析的文本
    """
    try:
        data = request.json or {}
        text = data.get('text', '')
        
        if not text:
            return jsonify({
                'code': 400,
                'message': '文本不能为空'
            }), 400
        
        sentiment, score = SentimentLexicon.analyze(text)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'text': text,
                'sentiment': sentiment,
                'sentiment_score': score,
                'analysis_time': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f'实时分析失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 三维度排序API ====================

@weibo_bp.route('/rank/tri-dimension', methods=['POST'])
def tri_dimension_rank():
    """
    情感-热度三维度排序
    
    创新点：融合情感强度和传播热度两个维度进行综合排序
    
    Body参数:
        data: 微博数据列表
        sentiment_weight: 情感权重 (默认0.4)
        heat_weight: 热度权重 (默认0.4)
        timeliness_weight: 时效性权重 (默认0.2)
        top_k: 返回前k条 (可选)
    """
    try:
        req_data = request.json or {}
        weibo_data = req_data.get('data', [])
        sentiment_weight = req_data.get('sentiment_weight', 0.4)
        heat_weight = req_data.get('heat_weight', 0.4)
        timeliness_weight = req_data.get('timeliness_weight', 0.2)
        top_k = req_data.get('top_k')
        
        if not weibo_data:
            return jsonify({
                'code': 400,
                'message': '数据不能为空'
            }), 400
        
        # 预处理：如果数据缺少情感得分，先进行情感分析
        for item in weibo_data:
            if 'sentiment_score' not in item:
                text = item.get('text', '')
                sentiment, score = SentimentLexicon.analyze(text)
                item['sentiment_score'] = score
                item['sentiment_label'] = sentiment
            # 将 interactions 展开为顶层字段供 rank_weibo_data 使用
            interactions = item.get('interactions', {})
            if interactions:
                if 'reposts_count' not in item:
                    item['reposts_count'] = interactions.get('reposts', 0)
                if 'comments_count' not in item:
                    item['comments_count'] = interactions.get('comments', 0)
                if 'attitudes_count' not in item:
                    item['attitudes_count'] = interactions.get('likes', 0)
        
        # 执行三维度排序
        ranked_data = rank_weibo_data(
            weibo_data, 
            sentiment_weight=sentiment_weight,
            heat_weight=heat_weight
        )
        
        if top_k:
            ranked_data = ranked_data[:top_k]
        
        # 转换为前端期望的数据格式
        formatted_items = []
        for item in ranked_data:
            sentiment_score = item.get('sentiment_score', 0)
            heat_score = item.get('heat_score', 0)
            
            # 确定情感极性
            if sentiment_score > 0.2:
                polarity = 'positive'
            elif sentiment_score < -0.2:
                polarity = 'negative'
            else:
                polarity = 'neutral'
            
            # 确定四象限 (基于归一化后的值)
            # 情感强度归一化到 0-1
            sentiment_intensity = min(1.0, abs(sentiment_score) * 1.5)
            # 热度归一化到 0-1 (假设最大热度对应 log(1+100000) ≈ 11.5)
            heat_normalized = min(1.0, heat_score / 11.5)
            
            high_sentiment = sentiment_intensity >= 0.5
            high_heat = heat_normalized >= 0.5
            
            if high_sentiment and high_heat:
                quadrant = 'high_sentiment_high_heat'
            elif high_sentiment and not high_heat:
                quadrant = 'high_sentiment_low_heat'
            elif not high_sentiment and high_heat:
                quadrant = 'low_sentiment_high_heat'
            else:
                quadrant = 'low_sentiment_low_heat'
            
            # 获取互动数据
            interactions = item.get('interactions', {})
            if not interactions:
                interactions = {
                    'reposts': item.get('reposts_count', 0),
                    'comments': item.get('comments_count', 0),
                    'likes': item.get('attitudes_count', 0)
                }
            
            formatted_item = {
                'id': item.get('id', ''),
                'text': item.get('text', ''),
                'rank': item.get('rank', 0),
                'tri_score': round(item.get('tri_score', 0), 4),
                'quadrant': quadrant,
                'sentiment': {
                    'polarity': polarity,
                    'score': round(sentiment_score, 4),
                    'intensity': round(sentiment_intensity * 100, 2)
                },
                'heat': {
                    'score': round(heat_normalized, 4),
                    'time_decay': round(item.get('score_breakdown', {}).get('timeliness_score', 0.5), 4),
                    'influence': round(1.0, 4)  # 简化处理
                },
                'interactions': interactions,
                'created_at': item.get('created_at', ''),
                'user': item.get('user', {})
            }
            formatted_items.append(formatted_item)
        
        # 保存分析结果
        analysis_id = f"tri_analysis_{int(time.time() * 1000)}"
        result = {
            'id': analysis_id,
            'type': 'tri_dimension',
            'data': formatted_items,
            'config': {
                'sentiment_weight': sentiment_weight,
                'heat_weight': heat_weight,
                'timeliness_weight': timeliness_weight
            },
            'analysis_time': datetime.now().isoformat()
        }
        
        analysis_results[analysis_id] = result
        save_metadata()
        
        # 保存到文件
        result_file = os.path.join(DATA_DIR, f'analysis_{analysis_id}.json')
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'id': analysis_id,
                'ranked_items': formatted_items,
                'total': len(formatted_items),
                'config': result['config'],
                'analysis_time': result['analysis_time']
            }
        })
        
    except Exception as e:
        logger.error(f'三维度排序失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/rank/config', methods=['GET', 'POST'])
def rank_config():
    """
    获取或设置三维度排序配置
    """
    if request.method == 'GET':
        config = TriDimensionConfig()
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'sentiment_weight': config.sentiment_weight,
                'heat_weight': config.heat_weight,
                'timeliness_weight': config.timeliness_weight,
                'repost_factor': config.repost_factor,
                'comment_factor': config.comment_factor,
                'like_factor': config.like_factor,
                'decay_half_life_hours': config.decay_half_life_hours,
                'negative_boost': config.negative_boost,
                'negative_boost_factor': config.negative_boost_factor
            }
        })
    else:
        # POST: 更新配置（这里只返回示例，实际可以持久化）
        return jsonify({
            'code': 200,
            'message': '配置更新成功（演示模式）'
        })


# ==================== BERT情感分析API ====================

@weibo_bp.route('/analyze/bert', methods=['POST'])
def bert_analyze():
    """
    使用BERT模型进行情感分析
    
    Body参数:
        text: 单条文本
        texts: 文本列表（批量分析）
    """
    try:
        req_data = request.json or {}
        text = req_data.get('text')
        texts = req_data.get('texts', [])
        
        if text:
            # 单条分析
            result = analyze_sentiment_bert(text)
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': result
            })
        elif texts:
            # 批量分析
            analyzer = ChineseBERTSentimentAnalyzer()
            analyzer.initialize()
            results = analyzer.analyze_batch(texts)
            
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'results': [
                        {
                            'text': r.text,
                            'sentiment': r.sentiment,
                            'confidence': round(r.confidence, 4)
                        } for r in results
                    ],
                    'total': len(results)
                }
            })
        else:
            return jsonify({
                'code': 400,
                'message': '请提供text或texts参数'
            }), 400
            
    except Exception as e:
        logger.error(f'BERT分析失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/analyze/hybrid', methods=['POST'])
def hybrid_analyze():
    """
    混合情感分析（词典+BERT）
    
    Body参数:
        text: 要分析的文本
        strategy: 融合策略 (weighted/confidence/cascade)
    """
    try:
        req_data = request.json or {}
        text = req_data.get('text', '')
        strategy = req_data.get('strategy', 'weighted')
        
        if not text:
            return jsonify({
                'code': 400,
                'message': '文本不能为空'
            }), 400
        
        result = analyze_sentiment_hybrid(text, strategy)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f'混合分析失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== Spark流水线API ====================

@weibo_bp.route('/pipeline/run', methods=['POST'])
def run_pipeline():
    """
    运行Spark分析流水线
    
    Body参数:
        data: 微博数据列表
        stages: 要执行的阶段列表 (可选)
    """
    try:
        req_data = request.json or {}
        weibo_data = req_data.get('data', [])
        
        if not weibo_data:
            return jsonify({
                'code': 400,
                'message': '数据不能为空'
            }), 400
        
        # 导入流水线
        from spark.spark_pipeline import SentimentPipeline, PipelineConfig
        
        config = PipelineConfig()
        pipeline = SentimentPipeline(config)
        
        # 运行流水线
        df = pipeline.run(weibo_data)
        
        # 获取统计信息
        stats = pipeline.get_statistics(df)
        metrics = pipeline.get_metrics()
        
        # 获取结果数据
        result_data = df.limit(100).toPandas().to_dict('records')
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'results': result_data,
                'statistics': stats,
                'metrics': metrics
            }
        })
        
    except Exception as e:
        logger.error(f'流水线执行失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 模型信息API ====================

@weibo_bp.route('/models/info', methods=['GET'])
def get_models_info():
    """获取可用模型信息"""
    try:
        # BERT模型信息
        bert_analyzer = ChineseBERTSentimentAnalyzer()
        bert_info = bert_analyzer.get_model_info()
        
        # 三维度模型信息
        tri_config = TriDimensionConfig()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'bert_model': bert_info,
                'tri_dimension_model': {
                    'name': '情感-热度三维度排序模型',
                    'description': '融合情感强度和传播热度的综合排序算法',
                    'parameters': {
                        'sentiment_weight': tri_config.sentiment_weight,
                        'heat_weight': tri_config.heat_weight,
                        'timeliness_weight': tri_config.timeliness_weight
                    }
                },
                'lexicon_model': {
                    'name': '中文情感词典',
                    'positive_words_count': len(SentimentLexicon.POSITIVE_WORDS),
                    'negative_words_count': len(SentimentLexicon.NEGATIVE_WORDS),
                    'negation_words_count': len(SentimentLexicon.NEGATION_WORDS),
                    'degree_words_count': len(SentimentLexicon.DEGREE_WORDS)
                },
                'available_strategies': ['lexicon', 'bert', 'hybrid', 'tri_dimension']
            }
        })
        
    except Exception as e:
        logger.error(f'获取模型信息失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 完整数据流连通API ====================
# 解决中期检查表中"爬虫数据未与各个模块连通"问题
# 数据流：微博爬虫 → HDFS原始存储 → Spark清洗 → HBase结构化 → 三维度排序 → 前端展示

@weibo_bp.route('/collect', methods=['POST'])
def collect_and_process():
    """
    启动完整数据采集与处理流程
    
    数据流：
    1. 启动爬虫任务，采集微博数据
    2. 采集完成后自动触发Spark清洗作业
    3. 清洗完成后写入HBase
    4. 最后执行三维度排序
    
    Body参数:
        keywords: 关键词列表
        pages: 每个关键词爬取页数 (默认3)
        crawl_hot: 是否爬取热搜话题 (默认true)
        auto_process: 是否自动触发后续处理 (默认true)
    
    Returns:
        task_id: 任务ID，用于查询状态
    """
    try:
        data = request.json or {}
        keywords = data.get('keywords', [])
        pages = data.get('pages', 50)
        crawl_hot = data.get('crawl_hot', True)
        auto_process = data.get('auto_process', True)
        pipeline_cookie = data.get('cookie', '').strip() or None
        
        # 参数校验
        if not isinstance(keywords, list):
            return jsonify({'code': 400, 'message': '关键词必须为数组格式'}), 400
        # 过滤空字符串和超长关键词
        cleaned_keywords = []
        for kw in keywords:
            kw = str(kw).strip()
            if not kw:
                continue
            if len(kw) > 100:
                return jsonify({'code': 400, 'message': f'关键词长度不能超过100字符: {kw[:20]}...'}), 400
            cleaned_keywords.append(kw)
        keywords = cleaned_keywords
        
        if not keywords and not crawl_hot:
            return jsonify({'code': 400, 'message': '关键词列表不能为空（或开启热搜爬取）'}), 400
        
        # 创建任务ID
        task_id = f"collect_{int(time.time() * 1000)}"
        
        # 创建任务记录
        task_info = {
            'id': task_id,
            'status': 'crawling',
            'phase': 'crawl',  # crawl -> clean -> analyze -> rank -> done
            'keywords': keywords,
            'pages': pages,
            'crawl_hot': crawl_hot,
            'auto_process': auto_process,
            'progress': 0,
            'collected': 0,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'result_file': None,
            'spark_job_id': None,
            'error': None,
            'phases': {
                'crawl': {'status': 'running', 'progress': 0},
                'hdfs': {'status': 'pending', 'progress': 0},
                'clean': {'status': 'pending', 'progress': 0},
                'analyze': {'status': 'pending', 'progress': 0},
                'rank': {'status': 'pending', 'progress': 0},
            }
        }
        
        with task_lock:
            crawl_tasks[task_id] = task_info
            save_metadata()
        
        # 在后台线程执行完整流程
        def run_full_pipeline():
            crawler_task = None
            try:
                # ========== 阶段1: 数据采集 ==========
                logger.info(f"[{task_id}] 阶段1: 开始数据采集...")
                task_info['phases']['crawl']['status'] = 'running'
                task_info['phases']['crawl']['progress'] = 5
                task_info['progress'] = 2
                
                crawler_task = WeiboCrawlerTask(os.path.join(DATA_DIR, 'weibo_raw'), cookie=pipeline_cookie)
                all_data = []
                
                # 计算总步骤用于进度
                hot_topic_n = 3  # 减少热搜话题数避免过慢
                total_steps = (1 + hot_topic_n if crawl_hot else 0) + len(keywords)
                finished_steps = 0
                
                def update_crawl_progress():
                    nonlocal finished_steps
                    finished_steps += 1
                    pct = min(int(finished_steps / max(total_steps, 1) * 100), 99)
                    task_info['phases']['crawl']['progress'] = pct
                    task_info['progress'] = int(pct * 0.2)  # 爬虫占总进度20%
                    task_info['collected'] = len(all_data)
                
                # 爬取热搜
                if crawl_hot:
                    try:
                        hot_list = crawler_task.crawl_hot_search(save=True)
                        update_crawl_progress()
                        logger.info(f"[{task_id}] 热搜榜爬取完成，共 {len(hot_list)} 条")
                        
                        # 爬取热搜话题的微博（减少数量加速）
                        hot_weibo = crawler_task.crawl_hot_topics(
                            top_n=hot_topic_n, 
                            pages_per_topic=pages, 
                            save=True
                        )
                        all_data.extend(hot_weibo)
                        update_crawl_progress()
                        logger.info(f"[{task_id}] 热搜话题微博爬取完成，共 {len(hot_weibo)} 条")
                    except Exception as e:
                        logger.warning(f"热搜爬取部分失败: {e}")
                        finished_steps += 2  # 跳过这些步骤
                
                # 按关键词爬取
                if keywords:
                    for kw in keywords:
                        try:
                            kw_data = crawler_task.crawl_by_keywords(
                                [kw], 
                                pages=pages, 
                                save=True
                            )
                            all_data.extend(kw_data)
                            logger.info(f"[{task_id}] 关键词 '{kw}' 爬取完成，共 {len(kw_data)} 条")
                        except Exception as e:
                            logger.warning(f"关键词 '{kw}' 爬取失败: {e}")
                        update_crawl_progress()
                
                task_info['progress'] = 20
                task_info['collected'] = len(all_data)
                task_info['phases']['crawl']['progress'] = 100
                task_info['phases']['crawl']['status'] = 'completed'
                
                # 保存采集数据
                result_file = os.path.join(DATA_DIR, f'crawl_result_{task_id}.json')
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2)
                task_info['result_file'] = result_file
                
                logger.info(f"[{task_id}] 采集完成，共 {len(all_data)} 条数据")
                
                if not auto_process:
                    # 即使不走后续处理流程，也要上传 HDFS 保存原始数据
                    try:
                        from utils.hdfs_client import upload_raw_to_hdfs_partitioned
                        hdfs_path = upload_raw_to_hdfs_partitioned(result_file, task_id)
                        if hdfs_path:
                            task_info['hdfs_path'] = hdfs_path
                            logger.info(f"[{task_id}] HDFS 同步成功: {hdfs_path}")
                        else:
                            logger.warning(f"[{task_id}] HDFS 同步失败/跳过")
                    except Exception as e:
                        logger.warning(f"[{task_id}] HDFS 同步异常: {e}")
                    task_info['status'] = 'crawl_completed'
                    task_info['phase'] = 'crawl_done'
                    save_metadata()
                    return
                
                # ========== 阶段1.5: HDFS 原始数据上传 ==========
                # 把爬虫产出的本地 JSON 通过 WebHDFS 落到 hdfs:///weibo/raw/dt=YYYY-MM-DD/{task_id}.json
                # 失败时降级为本地路径继续走 Spark, 不阻塞流水线 (HDFS phase 标记 failed)
                logger.info(f"[{task_id}] 阶段1.5: 上传原始数据到 HDFS...")
                task_info['phase'] = 'hdfs'
                task_info['phases']['hdfs']['status'] = 'running'
                task_info['progress'] = 21
                spark_input_path = result_file  # 默认本地, 上传成功后切到 HDFS URI
                try:
                    from utils.hdfs_client import upload_raw_to_hdfs_partitioned, get_hdfs_url
                    hdfs_path = upload_raw_to_hdfs_partitioned(result_file, task_id)
                    if hdfs_path:
                        hdfs_rpc = get_hdfs_url() or 'hdfs://namenode:9000'
                        task_info['hdfs_path'] = f'{hdfs_rpc}{hdfs_path}'
                        task_info['phases']['hdfs']['progress'] = 100
                        task_info['phases']['hdfs']['status'] = 'completed'
                        task_info['progress'] = 24
                        spark_input_path = task_info['hdfs_path']
                        logger.info(f"[{task_id}] HDFS 上传成功: {task_info['hdfs_path']}")
                    else:
                        raise RuntimeError("upload_raw_to_hdfs_partitioned returned None")
                except Exception as hdfs_err:
                    logger.warning(
                        f"[{task_id}] HDFS 上传失败, 降级使用本地路径继续: {hdfs_err}"
                    )
                    task_info['phases']['hdfs']['status'] = 'failed'
                    task_info['hdfs_error'] = str(hdfs_err)
                
                # ========== 阶段2: 数据清洗 ==========
                logger.info(f"[{task_id}] 阶段2: 开始数据清洗...")
                task_info['phase'] = 'clean'
                task_info['phases']['clean']['status'] = 'running'
                task_info['progress'] = 25
                
                # 导入Spark服务
                from services.spark_service import get_spark_service, JobStatus
                spark_service = get_spark_service()
                
                # 提交清洗作业 (优先用 HDFS 路径, 失败时退回本地文件)
                clean_job = spark_service.submit_cleaning_job(
                    input_path=spark_input_path,
                    output_path=f'/weibo/cleaned/{task_id}',
                    crawl_task_id=task_id
                )
                task_info['spark_job_id'] = clean_job.job_id
                
                # 等待清洗完成
                while True:
                    job_status = spark_service.get_job_status(clean_job.job_id)
                    if job_status:
                        task_info['phases']['clean']['progress'] = job_status.get('progress', 0)
                        task_info['progress'] = 25 + int(job_status.get('progress', 0) * 0.2)
                        
                        if job_status['status'] == JobStatus.COMPLETED.value:
                            break
                        elif job_status['status'] == JobStatus.FAILED.value:
                            raise Exception(f"清洗作业失败: {job_status.get('error_message')}")
                    
                    time.sleep(2)
                
                task_info['phases']['clean']['status'] = 'completed'
                task_info['progress'] = 45
                logger.info(f"[{task_id}] 数据清洗完成")
                
                # ========== 阶段3: 情感分析 ==========
                logger.info(f"[{task_id}] 阶段3: 开始情感分析...")
                task_info['phase'] = 'analyze'
                task_info['phases']['analyze']['status'] = 'running'
                
                # 使用本地情感分析器
                analyzer = SparkSentimentAnalyzer()
                analyzed_data = analyzer.analyze_batch(all_data)
                
                task_info['phases']['analyze']['progress'] = 100
                task_info['phases']['analyze']['status'] = 'completed'
                task_info['progress'] = 70
                
                # 保存分析结果
                analysis_file = os.path.join(DATA_DIR, f'analysis_{task_id}.json')
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    json.dump(analyzed_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"[{task_id}] 情感分析完成")
                
                # ========== 阶段4: 三维度排序 ==========
                logger.info(f"[{task_id}] 阶段4: 开始三维度排序...")
                task_info['phase'] = 'rank'
                task_info['phases']['rank']['status'] = 'running'
                task_info['progress'] = 75
                
                # 执行三维度排序
                ranked_data = rank_weibo_data(analyzed_data)
                
                task_info['phases']['rank']['progress'] = 100
                task_info['phases']['rank']['status'] = 'completed'
                task_info['progress'] = 95
                
                # 保存排序结果
                rank_file = os.path.join(DATA_DIR, f'ranked_{task_id}.json')
                with open(rank_file, 'w', encoding='utf-8') as f:
                    json.dump(ranked_data[:100], f, ensure_ascii=False, indent=2)
                
                logger.info(f"[{task_id}] 三维度排序完成")
                
                # ========== 阶段5: 结果入库 ==========
                logger.info(f"[{task_id}] 阶段5: 开始结果入库...")
                task_info['phase'] = 'store'
                task_info['progress'] = 96
                
                try:
                    from services.database_service import get_db_service
                    db = get_db_service()
                    batch_id = task_id
                    
                    # 5a: 写入微博原始数据
                    weibo_insert_result = db.bulk_insert_weibos(all_data, batch_id=batch_id)
                    logger.info(f"[{task_id}] 微博数据入库: inserted={weibo_insert_result.get('inserted', 0)}, skipped={weibo_insert_result.get('skipped', 0)}")
                    
                    # 5b: 写入情感分析结果
                    sentiment_records = []
                    for item in analyzed_data:
                        if item.get('id') or item.get('weibo_id'):
                            sentiment_records.append({
                                'weibo_id': item.get('id') or item.get('weibo_id'),
                                'hybrid_score': item.get('sentiment_score', item.get('score', 0)),
                                'dict_score': item.get('dict_score'),
                                'bert_score': item.get('bert_score'),
                                'sentiment_class': item.get('sentiment', item.get('sentiment_class', 'neutral')),
                                'confidence': item.get('confidence', 0.8),
                                'analysis_method': 'hybrid',
                            })
                    if sentiment_records:
                        sent_result = db.save_sentiment_results(sentiment_records)
                        logger.info(f"[{task_id}] 情感结果入库: saved={sent_result.get('saved', 0)}")
                    
                    # 5c: 写入三维度排序结果
                    if ranked_data:
                        rank_result = db.save_tri_dimension_results(ranked_data, batch_id=batch_id)
                        logger.info(f"[{task_id}] 排序结果入库: saved={rank_result.get('saved', 0)}")
                    
                    # 5d: 写入采集批次日志
                    try:
                        log_sql = """
                        INSERT INTO crawl_batch_log 
                        (batch_id, status, total_weibos, success_count, failure_count,
                         start_time, end_time, student_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE status=VALUES(status), end_time=VALUES(end_time)
                        """
                        with db.get_connection() as conn:
                            with conn.cursor() as cursor:
                                cursor.execute(log_sql, (
                                    batch_id,
                                    'completed',
                                    len(all_data),
                                    len(sentiment_records),
                                    0,
                                    task_info.get('start_time'),
                                    datetime.now().isoformat(),
                                    '2022407443'
                                ))
                            conn.commit()
                    except Exception as db_log_err:
                        logger.warning(f"[{task_id}] 批次日志写入失败（非关键）: {db_log_err}")
                    
                    logger.info(f"[{task_id}] 结果入库完成")
                except Exception as db_err:
                    logger.error(f"[{task_id}] 结果入库失败: {db_err}", exc_info=True)
                
                # ========== 完成 ==========
                task_info['status'] = 'completed'
                task_info['phase'] = 'done'
                task_info['progress'] = 100
                task_info['end_time'] = datetime.now().isoformat()
                save_metadata()
                
                logger.info(f"[{task_id}] 完整数据流处理完成!")
                
            except Exception as e:
                logger.error(f'完整流程执行失败: {e}', exc_info=True)
                task_info['status'] = 'failed'
                task_info['error'] = str(e)
                task_info['end_time'] = datetime.now().isoformat()
                save_metadata()
            finally:
                # 释放 Selenium 浏览器等资源
                if crawler_task:
                    try:
                        crawler_task.close()
                    except Exception:
                        pass
        
        thread = threading.Thread(target=run_full_pipeline)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'code': 200,
            'message': '数据采集与处理任务已启动',
            'data': {
                'task_id': task_id,
                'status': 'crawling',
                'auto_process': auto_process,
                'phases': ['crawl', 'clean', 'analyze', 'rank']
            }
        })
        
    except Exception as e:
        logger.error(f'启动采集任务失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/collect/status/<task_id>', methods=['GET'])
def get_collect_status(task_id: str):
    """
    获取完整数据流任务状态
    
    Returns:
        任务状态，包括各阶段进度
    """
    try:
        if task_id not in crawl_tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在'
            }), 404
        
        task_info = crawl_tasks[task_id]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'task_id': task_id,
                'status': task_info.get('status'),
                'phase': task_info.get('phase'),
                'progress': task_info.get('progress', 0),
                'collected': task_info.get('collected', 0),
                'phases': task_info.get('phases', {}),
                'start_time': task_info.get('start_time'),
                'end_time': task_info.get('end_time'),
                'error': task_info.get('error'),
                'spark_job_id': task_info.get('spark_job_id')
            }
        })
        
    except Exception as e:
        logger.error(f'获取任务状态失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/collect/result/<task_id>', methods=['GET'])
def get_collect_result(task_id: str):
    """
    获取完整数据流处理结果
    
    Query参数:
        type: 结果类型 (raw/analyzed/ranked)
        page: 页码
        page_size: 每页数量
    """
    try:
        if task_id not in crawl_tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在'
            }), 404
        
        task_info = crawl_tasks[task_id]
        result_type = request.args.get('type', 'ranked')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        
        # 根据类型选择文件
        if result_type == 'raw':
            file_path = os.path.join(DATA_DIR, f'crawl_result_{task_id}.json')
        elif result_type == 'analyzed':
            file_path = os.path.join(DATA_DIR, f'analysis_{task_id}.json')
        else:  # ranked
            file_path = os.path.join(DATA_DIR, f'ranked_{task_id}.json')
        
        if not os.path.exists(file_path):
            return jsonify({
                'code': 404,
                'message': f'{result_type}类型的结果文件不存在'
            }), 404
        
        # 读取数据
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 分页
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_data = data[start:end]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'items': paginated_data,
                'total': total,
                'page': page,
                'page_size': page_size,
                'type': result_type,
                'task_info': {
                    'id': task_id,
                    'status': task_info.get('status'),
                    'collected': task_info.get('collected', 0)
                }
            }
        })
        
    except Exception as e:
        logger.error(f'获取结果失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/spark/jobs', methods=['GET'])
def get_spark_jobs():
    """获取所有Spark作业列表"""
    try:
        from services.spark_service import get_spark_service
        spark_service = get_spark_service()
        
        jobs = spark_service.get_all_jobs()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'jobs': jobs,
                'total': len(jobs),
                'running': sum(1 for j in jobs if j['status'] == 'running'),
                'completed': sum(1 for j in jobs if j['status'] == 'completed'),
                'failed': sum(1 for j in jobs if j['status'] == 'failed')
            }
        })
        
    except Exception as e:
        logger.error(f'获取Spark作业列表失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/spark/jobs/<job_id>', methods=['GET'])
def get_spark_job_status(job_id: str):
    """获取单个Spark作业状态"""
    try:
        from services.spark_service import get_spark_service
        spark_service = get_spark_service()
        
        job = spark_service.get_job_status(job_id)
        
        if not job:
            return jsonify({
                'code': 404,
                'message': '作业不存在'
            }), 404
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': job
        })
        
    except Exception as e:
        logger.error(f'获取Spark作业状态失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/spark/jobs/<job_id>/cancel', methods=['POST'])
def cancel_spark_job(job_id: str):
    """取消Spark作业"""
    try:
        from services.spark_service import get_spark_service
        spark_service = get_spark_service()
        
        success = spark_service.cancel_job(job_id)
        
        if success:
            return jsonify({
                'code': 200,
                'message': '作业已取消'
            })
        else:
            return jsonify({
                'code': 404,
                'message': '作业不存在或无法取消'
            }), 404
        
    except Exception as e:
        logger.error(f'取消Spark作业失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 论文 6.3 PySpark 作业直提交 API ====================

@weibo_bp.route('/spark/submit/clean', methods=['POST'])
def submit_pyspark_clean_api():
    """论文 6.3.2: 提交 PySpark 清洗作业到伪集群.

    Body:
        input:  HDFS glob, 默认 hdfs://namenode:9000/raw/dt=<today>/*.json
        output: Parquet 输出, 默认 hdfs://namenode:9000/cleaned/dt=<today>
    """
    try:
        body = request.get_json(silent=True) or {}
        today = datetime.now().strftime('%Y-%m-%d')
        input_path  = body.get('input')  or f'hdfs://namenode:9000/raw/dt={today}/*.json'
        output_path = body.get('output') or f'hdfs://namenode:9000/cleaned/dt={today}'

        from services.spark_service import get_spark_service
        svc = get_spark_service()
        job = svc.submit_pyspark_clean(input_path, output_path,
                                       crawl_task_id=body.get('crawl_task_id', ''))
        return jsonify({'code': 200, 'data': job.to_dict()})
    except Exception as e:
        logger.error(f'submit pyspark clean failed: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500


@weibo_bp.route('/spark/submit/sentiment', methods=['POST'])
def submit_pyspark_sentiment_api():
    """论文 6.3.3: 提交 PySpark 分布式情感分析作业."""
    try:
        body = request.get_json(silent=True) or {}
        today = datetime.now().strftime('%Y-%m-%d')
        input_path = body.get('input') or f'hdfs://namenode:9000/cleaned/dt={today}'
        flask_url  = body.get('flask_url') or 'http://web:5000/api/sentiment/batch'

        from services.spark_service import get_spark_service
        svc = get_spark_service()
        job = svc.submit_pyspark_sentiment(input_path, flask_url=flask_url,
                                           crawl_task_id=body.get('crawl_task_id', ''))
        return jsonify({'code': 200, 'data': job.to_dict()})
    except Exception as e:
        logger.error(f'submit pyspark sentiment failed: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== 数据质量监控API ====================

@weibo_bp.route('/data-quality', methods=['GET'])
def get_data_quality():
    """
    获取数据质量概览
    
    返回最新的数据质量指标和报警信息
    """
    try:
        from utils.data_validator import get_validator
        validator = get_validator()
        
        summary = validator.get_latest_quality_summary()
        reports = validator.get_quality_reports(limit=5)
        error_log = validator.get_error_log(limit=20)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'summary': summary,
                'recent_reports': reports,
                'recent_errors': error_log,
                'thresholds': validator.QUALITY_THRESHOLDS
            }
        })
        
    except Exception as e:
        logger.error(f'获取数据质量失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/data-quality/validate', methods=['POST'])
def validate_data():
    """
    验证数据质量
    
    Body参数:
        data: 要验证的数据列表
        check_duplicates: 是否检查重复 (默认true)
        auto_fix: 是否自动修复 (默认true)
        generate_report: 是否生成报告 (默认true)
        task_id: 关联的任务ID (可选)
    """
    try:
        from utils.data_validator import get_validator, validate_weibo_batch, generate_quality_report
        
        req_data = request.json or {}
        data_list = req_data.get('data', [])
        check_duplicates = req_data.get('check_duplicates', True)
        auto_fix = req_data.get('auto_fix', True)
        gen_report = req_data.get('generate_report', True)
        task_id = req_data.get('task_id')
        
        if not data_list:
            return jsonify({
                'code': 400,
                'message': '数据列表不能为空'
            }), 400
        
        # 验证数据
        valid_data, metrics = validate_weibo_batch(
            data_list, 
            check_duplicates=check_duplicates,
            auto_fix=auto_fix
        )
        
        # 生成报告
        report = None
        if gen_report:
            report = generate_quality_report(metrics, task_id)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'metrics': metrics.to_dict(),
                'valid_count': len(valid_data),
                'report': report,
                'alerts': report.get('alerts', []) if report else []
            }
        })
        
    except Exception as e:
        logger.error(f'数据验证失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/data-quality/reports', methods=['GET'])
def get_quality_reports():
    """获取数据质量报告列表"""
    try:
        from utils.data_validator import get_validator
        validator = get_validator()
        
        limit = request.args.get('limit', 10, type=int)
        reports = validator.get_quality_reports(limit=limit)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'reports': reports,
                'total': len(reports)
            }
        })
        
    except Exception as e:
        logger.error(f'获取质量报告失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/data-quality/errors', methods=['GET'])
def get_quality_errors():
    """获取数据质量错误日志"""
    try:
        from utils.data_validator import get_validator
        validator = get_validator()
        
        limit = request.args.get('limit', 100, type=int)
        error_type = request.args.get('error_type')
        
        errors = validator.get_error_log(limit=limit, error_type=error_type)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'errors': errors,
                'total': len(errors)
            }
        })
        
    except Exception as e:
        logger.error(f'获取错误日志失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/data-quality/alerts', methods=['GET'])
def get_quality_alerts():
    """获取当前质量报警"""
    try:
        from utils.data_validator import get_validator
        validator = get_validator()
        
        reports = validator.get_quality_reports(limit=1)
        
        if not reports:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'alerts': [],
                    'status': 'no_data'
                }
            })
        
        latest_report = reports[-1]
        alerts = latest_report.get('alerts', [])
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'alerts': alerts,
                'status': latest_report['summary']['status'],
                'generated_at': latest_report['generated_at']
            }
        })
        
    except Exception as e:
        logger.error(f'获取质量报警失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/dataflow/overview', methods=['GET'])
def get_dataflow_overview():
    """
    获取数据流概览
    
    展示完整数据流的状态：
    微博爬虫 → HDFS原始存储 → Spark清洗 → HBase结构化 → 三维度排序
    """
    try:
        from services.spark_service import get_spark_service
        spark_service = get_spark_service()
        
        # 统计采集任务
        total_crawl_tasks = len(crawl_tasks)
        completed_crawl = sum(1 for t in crawl_tasks.values() if t.get('status') == 'completed')
        running_crawl = sum(1 for t in crawl_tasks.values() if t.get('status') in ['crawling', 'running'])
        
        # 统计Spark作业
        spark_jobs = spark_service.get_all_jobs()
        
        # 统计数据量
        raw_dir = os.path.join(DATA_DIR, 'weibo_raw')
        total_raw_files = 0
        total_raw_records = 0
        if os.path.exists(raw_dir):
            for f in os.listdir(raw_dir):
                if f.endswith('.json'):
                    total_raw_files += 1
                    try:
                        with open(os.path.join(raw_dir, f), 'r', encoding='utf-8') as file:
                            data = json.load(file)
                            total_raw_records += len(data) if isinstance(data, list) else 1
                    except:
                        pass
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'dataflow': {
                    'stages': [
                        {'name': '微博爬虫', 'status': 'active', 'count': total_crawl_tasks},
                        {'name': 'HDFS存储', 'status': 'active', 'count': total_raw_files},
                        {'name': 'Spark清洗', 'status': 'active', 'count': sum(1 for j in spark_jobs if j['job_type'] == 'data_cleaning')},
                        {'name': 'HBase存储', 'status': 'active', 'count': total_raw_records},
                        {'name': '三维度排序', 'status': 'active', 'count': sum(1 for j in spark_jobs if j['job_type'] == 'topic_ranking')},
                    ]
                },
                'crawl_stats': {
                    'total': total_crawl_tasks,
                    'completed': completed_crawl,
                    'running': running_crawl,
                    'failed': sum(1 for t in crawl_tasks.values() if t.get('status') == 'failed')
                },
                'spark_stats': {
                    'total': len(spark_jobs),
                    'running': sum(1 for j in spark_jobs if j['status'] == 'running'),
                    'completed': sum(1 for j in spark_jobs if j['status'] == 'completed'),
                    'failed': sum(1 for j in spark_jobs if j['status'] == 'failed')
                },
                'data_stats': {
                    'raw_files': total_raw_files,
                    'raw_records': total_raw_records,
                    'analysis_results': len(analysis_results)
                },
                'update_time': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f'获取数据流概览失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500
