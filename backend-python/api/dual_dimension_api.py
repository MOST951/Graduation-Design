"""
情感-热度双维度排序模型 API接口

提供完整的双维度分析功能：
1. 数据分析接口
2. 配置管理接口
3. 四象限统计接口
4. 散点图数据接口

作者：毕业设计
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import logging
import os
import sys

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from spark.dual_dimension_model_v2 import (
    DualDimensionModelV2,
    DualDimensionConfigV2,
    process_weibo_dual_dimension,
    Quadrant
)

# 导入数据库服务
try:
    from services.database_service import get_db_service
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# 导入流水线排序阶段
try:
    from services.pipeline_service import get_pipeline_service
    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False

# 创建蓝图
dual_bp = Blueprint('dual_dimension', __name__, url_prefix='/api/dual')

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 存储配置（实际项目中应该使用数据库）
saved_configs = {
    'default': {
        'name': '默认配置',
        'sentiment_weight': 0.5,
        'heat_weight': 0.5,
        'repost_weight': 1.0,
        'comment_weight': 2.0,
        'like_weight': 1.0,
        'time_decay_enabled': True,
        'decay_half_life_hours': 24.0,
        'influence_enabled': True,
        'verified_bonus': 1.5,
        'sentiment_threshold': 0.5,
        'heat_threshold': 0.5,
    },
    'sentiment_first': {
        'name': '情感优先',
        'sentiment_weight': 0.7,
        'heat_weight': 0.3,
        'repost_weight': 1.0,
        'comment_weight': 2.0,
        'like_weight': 1.0,
        'time_decay_enabled': True,
        'decay_half_life_hours': 24.0,
        'influence_enabled': True,
        'verified_bonus': 1.5,
        'sentiment_threshold': 0.5,
        'heat_threshold': 0.5,
    },
    'heat_first': {
        'name': '热度优先',
        'sentiment_weight': 0.3,
        'heat_weight': 0.7,
        'repost_weight': 1.0,
        'comment_weight': 2.0,
        'like_weight': 1.0,
        'time_decay_enabled': True,
        'decay_half_life_hours': 12.0,
        'influence_enabled': True,
        'verified_bonus': 1.8,
        'sentiment_threshold': 0.5,
        'heat_threshold': 0.5,
    },
}


# ==================== 分析接口 ====================

@dual_bp.route('/analyze', methods=['POST'])
def analyze_dual_dimension():
    """
    双维度分析接口
    
    Body参数:
        data: 微博数据列表
        config: 配置参数（可选）
        config_name: 使用预设配置名称（可选）
        top_k: 返回前k条（可选）
    
    返回:
        ranked_posts: 排序后的微博列表
        quadrant_statistics: 四象限统计
        scatter_data: 散点图数据
    """
    try:
        req_data = request.json or {}
        weibo_data = req_data.get('data', [])
        config = req_data.get('config', {})
        config_name = req_data.get('config_name')
        top_k = req_data.get('top_k')
        
        if not weibo_data:
            return jsonify({
                'code': 400,
                'message': '数据不能为空'
            }), 400
        
        # 使用预设配置
        if config_name and config_name in saved_configs:
            config = {**saved_configs[config_name], **config}
        
        # 执行分析
        result = process_weibo_dual_dimension(weibo_data, config)
        
        # 限制返回数量
        if top_k and top_k > 0:
            result['ranked_posts'] = result['ranked_posts'][:top_k]
            result['scatter_data'] = result['scatter_data'][:top_k]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': result,
            'analysis_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f'双维度分析失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@dual_bp.route('/analyze/single', methods=['POST'])
def analyze_single_post():
    """
    分析单条微博
    
    Body参数:
        text: 微博文本
        reposts_count: 转发数
        comments_count: 评论数
        attitudes_count: 点赞数
        followers_count: 粉丝数
        verified: 是否认证
        verified_type: 认证类型
        created_at: 发布时间
        config: 配置参数
    """
    try:
        req_data = request.json or {}
        
        text = req_data.get('text', '')
        if not text:
            return jsonify({
                'code': 400,
                'message': '文本不能为空'
            }), 400
        
        # 构造数据
        post_data = [{
            'id': '1',
            'text': text,
            'reposts_count': req_data.get('reposts_count', 0),
            'comments_count': req_data.get('comments_count', 0),
            'attitudes_count': req_data.get('attitudes_count', 0),
            'followers_count': req_data.get('followers_count', 0),
            'verified': req_data.get('verified', False),
            'verified_type': req_data.get('verified_type', -1),
            'created_at': req_data.get('created_at', datetime.now().isoformat()),
        }]
        
        config = req_data.get('config', {})
        result = process_weibo_dual_dimension(post_data, config)
        
        if result['ranked_posts']:
            post_result = result['ranked_posts'][0]
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': post_result
            })
        else:
            return jsonify({
                'code': 500,
                'message': '分析失败'
            }), 500
            
    except Exception as e:
        logger.error(f'单条分析失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 配置接口 ====================

@dual_bp.route('/config', methods=['GET'])
def get_config():
    """获取当前配置"""
    config_name = request.args.get('name', 'default')
    
    if config_name in saved_configs:
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': saved_configs[config_name]
        })
    else:
        return jsonify({
            'code': 404,
            'message': f'配置 {config_name} 不存在'
        }), 404


@dual_bp.route('/config/list', methods=['GET'])
def list_configs():
    """获取所有配置列表"""
    configs = []
    for key, value in saved_configs.items():
        configs.append({
            'key': key,
            'name': value.get('name', key),
            'sentiment_weight': value.get('sentiment_weight'),
            'heat_weight': value.get('heat_weight'),
        })
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': configs
    })


@dual_bp.route('/config', methods=['POST'])
def save_config():
    """
    保存配置
    
    Body参数:
        key: 配置键名
        name: 配置名称
        ... 其他配置参数
    """
    try:
        req_data = request.json or {}
        key = req_data.get('key')
        
        if not key:
            return jsonify({
                'code': 400,
                'message': '配置键名不能为空'
            }), 400
        
        # 验证权重
        sentiment_weight = req_data.get('sentiment_weight', 0.5)
        heat_weight = req_data.get('heat_weight', 0.5)
        
        total = sentiment_weight + heat_weight
        if abs(total - 1.0) > 0.001:
            sentiment_weight /= total
            heat_weight /= total
        
        config = {
            'name': req_data.get('name', key),
            'sentiment_weight': sentiment_weight,
            'heat_weight': heat_weight,
            'repost_weight': req_data.get('repost_weight', 1.0),
            'comment_weight': req_data.get('comment_weight', 2.0),
            'like_weight': req_data.get('like_weight', 1.0),
            'time_decay_enabled': req_data.get('time_decay_enabled', True),
            'decay_half_life_hours': req_data.get('decay_half_life_hours', 24.0),
            'influence_enabled': req_data.get('influence_enabled', True),
            'verified_bonus': req_data.get('verified_bonus', 1.5),
            'sentiment_threshold': req_data.get('sentiment_threshold', 0.5),
            'heat_threshold': req_data.get('heat_threshold', 0.5),
        }
        
        saved_configs[key] = config
        
        return jsonify({
            'code': 200,
            'message': '配置保存成功',
            'data': config
        })
        
    except Exception as e:
        logger.error(f'保存配置失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@dual_bp.route('/config/<key>', methods=['DELETE'])
def delete_config(key):
    """删除配置"""
    if key == 'default':
        return jsonify({
            'code': 400,
            'message': '默认配置不能删除'
        }), 400
    
    if key in saved_configs:
        del saved_configs[key]
        return jsonify({
            'code': 200,
            'message': '配置删除成功'
        })
    else:
        return jsonify({
            'code': 404,
            'message': f'配置 {key} 不存在'
        }), 404


# ==================== 四象限接口 ====================

@dual_bp.route('/quadrant/info', methods=['GET'])
def get_quadrant_info():
    """获取四象限说明信息"""
    quadrant_info = {
        'high_sentiment_high_heat': {
            'name': '高情感-高热度',
            'label': '重点关注',
            'description': '情感强烈且传播广泛的内容，需要重点关注和及时响应',
            'color': '#F56C6C',
            'priority': 1,
        },
        'high_sentiment_low_heat': {
            'name': '高情感-低热度',
            'label': '潜在风险',
            'description': '情感强烈但传播有限的内容，可能存在潜在风险',
            'color': '#E6A23C',
            'priority': 2,
        },
        'low_sentiment_high_heat': {
            'name': '低情感-高热度',
            'label': '热门中性',
            'description': '传播广泛但情感平淡的内容，通常为信息类内容',
            'color': '#409EFF',
            'priority': 3,
        },
        'low_sentiment_low_heat': {
            'name': '低情感-低热度',
            'label': '一般内容',
            'description': '情感和传播都较弱的普通内容',
            'color': '#909399',
            'priority': 4,
        },
    }
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': quadrant_info
    })


@dual_bp.route('/quadrant/statistics', methods=['POST'])
def get_quadrant_statistics():
    """
    获取四象限统计
    
    Body参数:
        data: 微博数据列表
        config: 配置参数
    """
    try:
        req_data = request.json or {}
        weibo_data = req_data.get('data', [])
        config = req_data.get('config', {})
        
        if not weibo_data:
            return jsonify({
                'code': 400,
                'message': '数据不能为空'
            }), 400
        
        result = process_weibo_dual_dimension(weibo_data, config)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'statistics': result['quadrant_statistics'],
                'total': result['total'],
                'config': result['config'],
            }
        })
        
    except Exception as e:
        logger.error(f'获取四象限统计失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 散点图数据接口 ====================

@dual_bp.route('/scatter', methods=['POST'])
def get_scatter_data():
    """
    获取散点图数据
    
    Body参数:
        data: 微博数据列表
        config: 配置参数
        limit: 最大返回数量
    """
    try:
        req_data = request.json or {}
        weibo_data = req_data.get('data', [])
        config = req_data.get('config', {})
        limit = req_data.get('limit', 500)
        
        if not weibo_data:
            return jsonify({
                'code': 400,
                'message': '数据不能为空'
            }), 400
        
        result = process_weibo_dual_dimension(weibo_data, config)
        
        # 限制数量
        scatter_data = result['scatter_data'][:limit]
        
        # 添加四象限分界线数据
        threshold_lines = {
            'sentiment_threshold': config.get('sentiment_threshold', 0.5) * 100,
            'heat_threshold': config.get('heat_threshold', 0.5) * 100,
        }
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'scatter_data': scatter_data,
                'threshold_lines': threshold_lines,
                'quadrant_statistics': result['quadrant_statistics'],
                'total': len(scatter_data),
            }
        })
        
    except Exception as e:
        logger.error(f'获取散点图数据失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== MySQL数据排序接口 ====================

@dual_bp.route('/run-db', methods=['POST'])
def run_ranking_on_db():
    """
    对MySQL中已完成情感分析的微博执行双维度排序并写回结果
    
    Body参数:
        limit: 处理数量上限（默认500）
    """
    try:
        if not DB_AVAILABLE:
            return jsonify({'code': 503, 'message': '数据库服务不可用'}), 503

        data = request.get_json(silent=True) or {}
        limit = data.get('limit', 500)

        db = get_db_service()
        unranked = db.get_unranked_weibos(limit=limit)

        if not unranked:
            return jsonify({
                'code': 200,
                'message': '无待排序微博',
                'data': {'ranked': 0},
            })

        # 使用流水线的排序阶段
        if PIPELINE_AVAILABLE:
            pipeline = get_pipeline_service()
            ranked = pipeline.ranking_stage.rank(unranked)
        else:
            return jsonify({'code': 503, 'message': '流水线服务不可用'}), 503

        from datetime import datetime as dt
        batch_id = f"rank_{dt.now().strftime('%Y%m%d%H%M%S')}"
        save_result = db.save_dual_dimension_results(ranked, batch_id)

        return jsonify({
            'code': 200,
            'message': f'双维度排序完成，处理{save_result["saved"]}条',
            'data': {
                'input_count': len(unranked),
                'saved': save_result['saved'],
                'errors': save_result['errors'],
                'batch_id': batch_id,
                'top10': ranked[:10],
            },
        })
    except Exception as e:
        logger.error(f'Run ranking on DB failed: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500


@dual_bp.route('/ranking-from-db', methods=['GET'])
def get_ranking_from_db():
    """从MySQl查询最新排序结果"""
    try:
        if not DB_AVAILABLE:
            return jsonify({'code': 503, 'message': '数据库服务不可用'}), 503

        limit = request.args.get('limit', 50, type=int)
        db = get_db_service()

        sql = """
            SELECT r.weibo_id, r.sentiment_score, r.sentiment_category,
                   r.popularity_score, r.popularity_class, r.time_decay,
                   r.composite_score, r.ranking_position, r.batch_id,
                   r.algorithm_version, w.content, w.user_name,
                   w.reposts_count, w.comments_count, w.attitudes_count,
                   w.created_at as weibo_created_at
            FROM dual_dimension_ranking r
            JOIN weibo_core_data w ON r.weibo_id = w.weibo_id
            WHERE r.batch_id = (
                SELECT batch_id FROM dual_dimension_ranking
                ORDER BY calculation_time DESC LIMIT 1
            )
            ORDER BY r.ranking_position ASC
            LIMIT %s
        """
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (limit,))
                rows = cursor.fetchall()

        # 序列化
        for row in rows:
            for key, val in row.items():
                if hasattr(val, 'isoformat'):
                    row[key] = val.isoformat()
                elif isinstance(val, bytes):
                    row[key] = val.decode('utf-8', errors='replace')

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'total': len(rows), 'items': rows},
        })
    except Exception as e:
        logger.error(f'Get ranking from DB failed: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== 公式说明接口 ====================

@dual_bp.route('/formula', methods=['GET'])
def get_formula_info():
    """获取算法公式说明 (v2.0 级联策略+半衰期)"""
    formula_info = {
        'sentiment_cascade': {
            'name': '公式4-3: 级联情感分析策略',
            'formula': 'S_final = S_dict if |S_dict| > θ else S_bert, θ=0.7',
            'description': '词典置信度超过阈值直接采用，否则调用ChineseBERT',
        },
        'sentiment_normalized': {
            'name': '公式4-4: 情感强度归一化',
            'formula': 'N(S) = (|S| + 1) / 2',
            'description': '将情感得分从[-1,1]映射到[0,1]',
        },
        'heat_score': {
            'name': '公式4-5: 热度得分',
            'formula': 'H_raw = log₁₀(1 + 3R + 2C + L), H_norm = H_raw / max(H_raw)',
            'description': '对数平滑后归一化的热度得分',
            'parameters': {
                'λ_r': '转发权重=3.0',
                'λ_c': '评论权重=2.0',
                'λ_l': '点赞权重=1.0',
            },
        },
        'time_decay': {
            'name': '公式4-6: 时间衰减',
            'formula': 'γ(t) = 2^(-Δt / H), H=12小时',
            'description': '半衰期时间衰减模型，12小时后衰减为原来的50%',
        },
        'composite_score': {
            'name': '公式4-7: 综合排序得分',
            'formula': 'Score = ω₁·N(S) + ω₂·H_norm + ω₃·γ(t)',
            'description': '情感-热度-时效三维度加权综合得分',
            'parameters': {
                'ω₁': '情感权重=0.4',
                'ω₂': '热度权重=0.4',
                'ω₃': '时效权重=0.2',
            },
        },
    }
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': formula_info
    })


# ==================== 健康检查 ====================

@dual_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'status': 'healthy',
            'module': 'dual_dimension',
            'version': '2.0',
            'timestamp': datetime.now().isoformat()
        }
    })
