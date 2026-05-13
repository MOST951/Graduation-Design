"""
数据流水线 API
==============
提供端到端流水线的触发、状态查询、统计接口

端点:
- POST /api/pipeline/run         — 同步执行流水线
- POST /api/pipeline/run-async   — 异步执行流水线
- GET  /api/pipeline/status      — 查询流水线状态
- GET  /api/pipeline/stats       — 查询数据库统计
- GET  /api/pipeline/ranking     — 查询最新排序结果
"""

from flask import Blueprint, request, jsonify
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from services.pipeline_service import get_pipeline_service
from services.database_service import get_db_service
from utils.redis_cache import redis_cache

pipeline_bp = Blueprint('pipeline', __name__, url_prefix='/api/pipeline')
logger = logging.getLogger(__name__)


@pipeline_bp.route('/run', methods=['POST'])
def run_pipeline():
    """
    同步执行完整流水线:
    采集数据(MySQL) → 情感分析(级联策略) → 三维度排序 → 结果入库
    """
    try:
        data = request.get_json(silent=True) or {}
        limit = data.get('limit', 500)

        pipeline = get_pipeline_service()
        result = pipeline.run_pipeline(limit=limit)

        return jsonify({
            'code': 200,
            'message': '流水线执行完成',
            'data': result,
        })
    except Exception as e:
        logger.error(f'Pipeline run failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': f'流水线执行失败: {str(e)}',
        }), 500


@pipeline_bp.route('/run-async', methods=['POST'])
def run_pipeline_async():
    """异步执行流水线（后台运行），支持从指定阶段断点续跑"""
    try:
        data = request.get_json(silent=True) or {}
        limit = data.get('limit', 500)
        resume_from = data.get('resume_from')  # 如 'sentiment' / 'ranking'
        batch_id = data.get('batch_id')

        pipeline = get_pipeline_service()
        result = pipeline.run_pipeline_async(limit=limit, resume_from=resume_from, batch_id=batch_id)

        return jsonify({
            'code': 200,
            'message': result['message'],
            'data': result,
        })
    except Exception as e:
        logger.error(f'Pipeline async start failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@pipeline_bp.route('/status', methods=['GET'])
def get_pipeline_status():
    """查询流水线运行状态"""
    try:
        pipeline = get_pipeline_service()
        status = pipeline.get_status()
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': status,
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@pipeline_bp.route('/stats', methods=['GET'])
@redis_cache('pipeline:stats', ttl=30)
def get_database_stats():
    """查询数据库统计（各表数据量、情感分布等）"""
    try:
        db = get_db_service()
        stats = db.get_graduation_statistics()
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': stats,
        })
    except Exception as e:
        logger.error(f'Stats query failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@pipeline_bp.route('/ranking', methods=['GET'])
@redis_cache('pipeline:ranking', ttl=30,
             key_fn=lambda req: f"l={req.args.get('limit','20')}|b={req.args.get('batch_id','')}")
def get_latest_ranking():
    """
    查询最新三维度排序结果
    
    参数: ?limit=20&batch_id=xxx
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        batch_id = request.args.get('batch_id', None)

        db = get_db_service()

        if batch_id:
            sql = """
                SELECT r.*, w.content, w.user_name, w.created_at as weibo_created_at
                FROM tri_dimension_ranking r
                JOIN weibo_core_data w ON r.weibo_id = w.weibo_id
                WHERE r.batch_id = %s
                ORDER BY r.ranking_position ASC
                LIMIT %s
            """
            params = (batch_id, limit)
        else:
            sql = """
                SELECT r.*, w.content, w.user_name, w.created_at as weibo_created_at
                FROM tri_dimension_ranking r
                JOIN weibo_core_data w ON r.weibo_id = w.weibo_id
                WHERE r.batch_id = (
                    SELECT batch_id FROM tri_dimension_ranking 
                    ORDER BY calculation_time DESC LIMIT 1
                )
                ORDER BY r.ranking_position ASC
                LIMIT %s
            """
            params = (limit,)

        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()

        # 序列化 datetime 对象
        for row in rows:
            for key, val in row.items():
                if hasattr(val, 'isoformat'):
                    row[key] = val.isoformat()
                elif isinstance(val, bytes):
                    row[key] = val.decode('utf-8', errors='replace')

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total': len(rows),
                'items': rows,
            },
        })
    except Exception as e:
        logger.error(f'Ranking query failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500


@pipeline_bp.route('/health', methods=['GET'])
def pipeline_health():
    """流水线健康检查"""
    try:
        db = get_db_service()
        table_status = db.check_tables_status()

        pipeline = get_pipeline_service()
        status = pipeline.get_status()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'pipeline_running': status['running'],
                'bert_available': status['bert_available'],
                'database': table_status,
            },
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e),
            'data': {'healthy': False},
        }), 500


@pipeline_bp.route('/history', methods=['GET'])
@redis_cache('pipeline:history', ttl=30,
             key_fn=lambda req: f"l={req.args.get('limit','50')}")
def get_pipeline_history():
    """查询历史运行记录（从crawl_batch_log）"""
    try:
        db = get_db_service()
        limit = request.args.get('limit', 50, type=int)
        
        sql = """
            SELECT batch_id, status, total_weibos, success_count, failure_count,
                   start_time, end_time, created_at, student_id
            FROM crawl_batch_log
            ORDER BY created_at DESC
            LIMIT %s
        """
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (limit,))
                rows = cursor.fetchall()
        
        for row in rows:
            for key, val in row.items():
                if hasattr(val, 'isoformat'):
                    row[key] = val.isoformat()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': rows,
        })
    except Exception as e:
        logger.error(f'History query failed: {e}', exc_info=True)
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': [],
        })
