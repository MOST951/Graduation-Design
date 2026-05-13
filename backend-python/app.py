"""
微博情感分析系统 - 后端主应用
Flask + CORS + Swagger (论文 6.2.2 图6-9)
"""
from flask import Flask, jsonify
from flask_cors import CORS

# Swagger UI (论文 6.2.2 图6-9 提到的 Flask 后端 API 文档).
# 用 flasgger 自动从 docstring / 配置生成 OpenAPI 2.0 + UI.
try:
    from flasgger import Swagger
    SWAGGER_AVAILABLE = True
except ImportError:
    SWAGGER_AVAILABLE = False

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
from api.tri_dimension_api import tri_bp
from api.evaluation import evaluation_bp
from api.preprocess import preprocess_bp
from api.propagation import propagation_bp
from api.crawler import crawler_bp
from api.pipeline_api import pipeline_bp
from api.admin import admin_bp
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
        "allow_headers": ["Content-Type", "Authorization", "X-User-Role"],
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
app.register_blueprint(tri_bp)
app.register_blueprint(evaluation_bp)
app.register_blueprint(preprocess_bp)
app.register_blueprint(propagation_bp)
app.register_blueprint(crawler_bp)
app.register_blueprint(pipeline_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(analysis_bp)

# 注册统一API（v2版本）
if UNIFIED_API_AVAILABLE:
    app.register_blueprint(unified_bp)
    logger.info("统一API (v2) 已注册")

# ====================================================================
# 论文 6.2.2 图6-9: Swagger UI 自动 API 文档
# ====================================================================
if SWAGGER_AVAILABLE:
    # 手工声明核心 API (flasgger 默认只扫有 docstring YAML 的 view, 此处直接在
    # template.paths 里列出, 确保 /apidocs 有实质内容, 对应论文 6.2.2 图6-9).
    _auth_tag    = ["auth"]
    _crawl_tag   = ["crawler"]
    _sent_tag    = ["sentiment"]
    _tri_tag     = ["tri-dimension"]
    _pipe_tag    = ["pipeline"]
    _mon_tag     = ["monitor"]
    _dash_tag    = ["dashboard"]
    _adm_tag     = ["admin"]
    _spark_tag   = ["spark"]

    _ok = {"200": {"description": "成功, code=200, data=<业务数据>"}}
    _bearer = [{"Bearer": []}]

    _paths = {
        # -------- auth (大部分已切到 Java, Flask 留 register/send-code) --------
        "/api/auth/send-code": {
            "post": {"tags": _auth_tag, "summary": "发送邮箱验证码 (注册/找回)",
                     "parameters": [{"name": "body", "in": "body", "required": True,
                        "schema": {"type": "object",
                                   "properties": {"email": {"type": "string"},
                                                  "type":  {"type": "string",
                                                            "enum": ["register", "reset"]}},
                                   "required": ["email", "type"]}}],
                     "responses": _ok}
        },
        "/api/auth/register": {
            "post": {"tags": _auth_tag, "summary": "邮箱验证码注册",
                     "parameters": [{"name": "body", "in": "body", "required": True,
                        "schema": {"type": "object",
                                   "properties": {"email": {"type": "string"},
                                                  "code":  {"type": "string"},
                                                  "username": {"type": "string"},
                                                  "password": {"type": "string"}}}}],
                     "responses": _ok}
        },

        # -------- 数据采集 (论文 6.1.1) --------
        "/api/weibo/crawl/start": {
            "post": {"tags": _crawl_tag, "summary": "启动采集任务 (严格校验+数据源透明)",
                     "description": "论文 6.1.1: keywords ≤20 × 64char, pages 1-50, max_count 1-50000, mode=auto/real/synthetic",
                     "parameters": [{"name": "body", "in": "body", "required": True,
                        "schema": {"type": "object",
                                   "properties": {
                                       "keywords":  {"type": "array", "items": {"type": "string"}},
                                       "pages":     {"type": "integer", "default": 3},
                                       "crawl_hot": {"type": "boolean", "default": True},
                                       "max_count": {"type": "integer"},
                                       "mode":      {"type": "string",
                                                     "enum": ["auto", "real", "synthetic"]}
                                   }}}],
                     "responses": {"200": {"description": "任务已启动"},
                                   "400": {"description": "入参非法"}}}
        },
        "/api/weibo/crawl/status/{task_id}": {
            "get": {"tags": _crawl_tag, "summary": "查询采集任务进度 + 数据源分类",
                    "parameters": [{"name": "task_id", "in": "path", "required": True,
                                    "type": "string"}],
                    "responses": _ok}
        },
        "/api/weibo/crawl/tasks": {
            "get": {"tags": _crawl_tag, "summary": "采集任务历史列表",
                    "responses": _ok}
        },

        # -------- 情感分析 (论文 4.2.1 + 6.3.3) --------
        "/api/sentiment/analyze": {
            "post": {"tags": _sent_tag, "summary": "单条文本情感分析 (词典+BERT 级联)",
                     "parameters": [{"name": "body", "in": "body", "required": True,
                        "schema": {"type": "object",
                                   "properties": {"text": {"type": "string"},
                                                  "method": {"type": "string",
                                                             "enum": ["lexicon","bert","hybrid"]}}}}],
                     "responses": _ok}
        },
        "/api/sentiment/batch": {
            "post": {"tags": _sent_tag,
                     "summary": "批量情感分析 (论文 6.3.3 Spark foreachPartition 入口)",
                     "description": "Spark Executor 从此接口拉取批量推理结果, 写回 MySQL.",
                     "parameters": [{"name": "body", "in": "body", "required": True,
                        "schema": {"type": "object",
                                   "properties": {"texts":  {"type": "array", "items": {"type": "string"}},
                                                  "method": {"type": "string", "default": "hybrid"},
                                                  "batch_size": {"type": "integer", "default": 32}}}}],
                     "responses": _ok}
        },

        # -------- 三维度排序 (论文 4.2.2) --------
        "/api/tri-dimension/rank": {
            "post": {"tags": _tri_tag,
                     "summary": "三维度加权排序 (情感α/热度β/时效γ)",
                     "responses": _ok}
        },

        # -------- Spark 大数据 (论文 6.3) --------
        "/api/weibo/spark/jobs": {
            "get": {"tags": _spark_tag, "summary": "Spark 作业列表 + 统计", "responses": _ok}
        },
        "/api/weibo/spark/jobs/{job_id}": {
            "get": {"tags": _spark_tag, "summary": "Spark 作业状态详情",
                    "parameters": [{"name": "job_id", "in": "path", "required": True,
                                    "type": "string"}],
                    "responses": _ok}
        },
        "/api/weibo/spark/submit/clean": {
            "post": {"tags": _spark_tag,
                     "summary": "论文 6.3.2: 提交 PySpark 清洗作业到 Standalone 集群",
                     "description": "HDFS /raw/dt=YYYY-MM-DD/*.json -> regexp_replace + UDF -> Parquet /cleaned/dt=YYYY-MM-DD",
                     "parameters": [{"name": "body", "in": "body",
                        "schema": {"type": "object",
                                   "properties": {"input":  {"type": "string"},
                                                  "output": {"type": "string"}}}}],
                     "responses": _ok}
        },
        "/api/weibo/spark/submit/sentiment": {
            "post": {"tags": _spark_tag,
                     "summary": "论文 6.3.3: 提交 PySpark 分布式情感分析 (foreachPartition -> Flask -> MySQL)",
                     "parameters": [{"name": "body", "in": "body",
                        "schema": {"type": "object",
                                   "properties": {"input": {"type": "string"},
                                                  "flask_url": {"type": "string"}}}}],
                     "responses": _ok}
        },

        # -------- 数据流水线 (论文 6.1.6) --------
        "/api/pipeline/run": {
            "post": {"tags": _pipe_tag, "summary": "一键运行数据流水线 (采集→清洗→情感→排序)",
                     "responses": _ok}
        },

        # -------- 监控/仪表盘 --------
        "/api/monitor/overview":  {"get": {"tags": _mon_tag,  "summary": "实时舆情监控概览", "responses": _ok}},
        "/api/dashboard/overview":{"get": {"tags": _dash_tag, "summary": "仪表盘聚合数据",   "responses": _ok}},

        # -------- 管理员 (需 JWT role=admin) --------
        "/api/admin/users":           {"get": {"tags": _adm_tag, "summary": "用户列表 (需 admin)",
                                               "security": _bearer, "responses": _ok}},
        "/api/admin/system/metrics":  {"get": {"tags": _adm_tag, "summary": "系统指标 CPU/内存/磁盘 (需 admin)",
                                               "security": _bearer, "responses": _ok}},
    }

    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "微博舆情情感分析系统 - Flask 后端 API",
            "description": (
                "基于 Spark 伪集群的微博舆情情感分析系统 - Python Flask 后端\n\n"
                "**论文 6.2.2**: 负责爬虫、情感分析、三维度排序、数据流水线、Spark 作业调度.\n\n"
                "**双后端协同 (论文 6.2.3)**: 登录/任务管理走 Java (8081); 其余走本服务 (5000)."
            ),
            "version": "2.0.0",
            "contact": {"name": "罗森 / 2022407443"},
        },
        "basePath": "/",
        "schemes": ["http", "https"],
        "tags": [
            {"name": "auth",          "description": "认证 (login/register/info)"},
            {"name": "crawler",       "description": "数据采集 (论文 6.1.1)"},
            {"name": "sentiment",     "description": "情感分析 - 词典+BERT 级联融合 (论文 4.2.1)"},
            {"name": "tri-dimension", "description": "三维度排序 - 情感/热度/时效 (论文 4.2.2)"},
            {"name": "spark",         "description": "Spark 大数据作业 (论文 6.3)"},
            {"name": "pipeline",      "description": "数据流水线 (论文 6.1.6)"},
            {"name": "monitor",       "description": "实时舆情监控 (论文 6.1.5)"},
            {"name": "dashboard",     "description": "可视化仪表盘 (论文 6.1.7)"},
            {"name": "admin",         "description": "系统管理 (论文 6.1.8)"},
        ],
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT 形如: 'Bearer <token>'",
            }
        },
        "paths": _paths,
    }
    swagger_config = {
        "headers": [],
        "specs": [{
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/apidocs/",       # 论文 6.2.2 图6-9 的 Swagger UI 入口
    }
    Swagger(app, template=swagger_template, config=swagger_config)
    logger.info("Swagger UI 已注册: http://<host>:5000/apidocs/")
else:
    logger.warning("flasgger 未安装, Swagger UI 不可用 (pip install flasgger)")

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
            '情感-热度三维度排序模型',
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
                'tri_dimension': '/api/tri-dimension',
                'evaluation': '/api/evaluation',
                'analysis': '/api/analysis',
            },
            'v2': {
                'unified': '/api/v2',
                'crawl': '/api/v2/crawl/start',
                'sentiment': '/api/v2/sentiment/analyze',
                'ranking': '/api/v2/ranking/tri-dimension',
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
