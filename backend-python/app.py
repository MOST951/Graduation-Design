"""
微博情感分析系统 - 后端主应用
Flask + CORS支持
"""
from flask import Flask, jsonify
from flask_cors import CORS

# 
from config import config
from utils.logger import get_logger
logger = get_logger(__name__)

from api.collection import collection_bp
from api.sentiment import sentiment_bp
from api.topics import topics_bp
from api.behavior import behavior_bp
from api.monitor import monitor_bp
from api.auth import auth_bp
from api.dashboard import dashboard_bp
from api.weibo_api import weibo_bp
from api.dual_dimension_api import dual_bp
from api.evaluation import evaluation_bp
from api.preprocess import preprocess_bp
from api.propagation import propagation_bp
from api.crawler import crawler_bp
from api.pipeline_api import pipeline_bp
from routes.analysis_routes import analysis_bp
from models.model_manager import preload_models_on_startup, ModelManager

# 导入统一API
try:
    from api.unified_api import unified_bp
    UNIFIED_API_AVAILABLE = True
except ImportError as e:
    UNIFIED_API_AVAILABLE = False

# 旧的分析流水线API已被 pipeline_api 替代
ANALYSIS_PIPELINE_AVAILABLE = False

# 创建Flask应用
app = Flask(__name__)

# 
app.config['SECRET_KEY'] = config.flask.secret_key
app.config['DEBUG'] = config.flask.debug

# 
cors_origins = config.flask.cors_origins

CORS(app, resources={
    r"/api/*": {
        "origins": cors_origins,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
    }
})

logger.info(f"CORS配置完成，允许的源: {cors_origins}")

# 注册蓝图
app.register_blueprint(collection_bp)
app.register_blueprint(sentiment_bp)
app.register_blueprint(topics_bp)
app.register_blueprint(behavior_bp)
app.register_blueprint(monitor_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(weibo_bp)
app.register_blueprint(dual_bp)
app.register_blueprint(evaluation_bp)
app.register_blueprint(preprocess_bp)
app.register_blueprint(propagation_bp)
app.register_blueprint(crawler_bp)
app.register_blueprint(pipeline_bp)
app.register_blueprint(analysis_bp)

# 注册统一API（v2版本）
if UNIFIED_API_AVAILABLE:
    app.register_blueprint(unified_bp)
    logger.info("统一API (v2) 已注册")

# 注册分析流水线API
if ANALYSIS_PIPELINE_AVAILABLE:
    app.register_blueprint(analysis_pipeline_bp, url_prefix='/api/pipeline')
    logger.info("分析流水线API已注册")

# 根路由
@app.route('/')
def index():
    return jsonify({
        'message': '微博情感分析系统API',
        'version': '2.0.0',
        'description': '基于Spark的分布式微博情感分析系统',
        'features': [
            '微博数据采集与清洗',
            '基于Spark的分布式处理',
            '词典+ChineseBERT混合情感分析',
            '情感-热度双维度排序模型',
            '实时可视化监控',
        ],
        'endpoints': {
            'v1': {
                'collection': '/api/collection',
                'sentiment': '/api/sentiment',
                'topics': '/api/topics',
                'behavior': '/api/behavior',
                'monitor': '/api/monitor',
                'weibo': '/api/weibo',
                'dual_dimension': '/api/dual',
                'evaluation': '/api/evaluation',
                'analysis': '/api/analysis',
            },
            'v2': {
                'unified': '/api/v2',
                'crawl': '/api/v2/crawl/start',
                'sentiment': '/api/v2/sentiment/analyze',
                'ranking': '/api/v2/ranking/dual-dimension',
                'stats': '/api/v2/stats/overview',
                'health': '/api/v2/health',
            }
        },
        'health_checks': {
            'v1': '/api/sentiment/health',
            'v2': '/api/v2/health',
        }
    })

# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'code': 404,
        'message': '正在努力加载中，请稍后再试',
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f'Internal error: {error}', exc_info=True)
    return jsonify({
        'code': 500,
        'message': '服务器内部错误',
    }), 500

@app.route('/api/models/status', methods=['GET'])
def get_models_status():
    """获取模型加载状态"""
    manager = ModelManager()
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': manager.get_status()
    })


@app.route('/api/models/preload', methods=['POST'])
def preload_models():
    """手动触发模型预加载"""
    try:
        manager = ModelManager()
        manager.preload_essential()
        manager.warmup_all()
        return jsonify({
            'code': 200,
            'message': '模型预加载完成',
            'data': manager.get_status()
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


if __name__ == '__main__':
    logger.info('Starting Weibo Sentiment Analysis Backend...')
    
    # 
    preload_models_on_startup()
    
    # 
    app.run(
        host=config.flask.host,
        port=config.flask.port,
        debug=config.flask.debug,
        threaded=True
    )
