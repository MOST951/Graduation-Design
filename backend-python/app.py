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

    _preproc_tag = ["preprocess"]
    _eval_tag    = ["evaluation"]
    _behavior_tag = ["behavior"]

    _paths = {
        # ==================== 认证 (论文 6.1.8) ====================
        "/api/auth/register":   {"post": {"tags": _auth_tag, "summary": "邮箱验证码注册",
            "parameters": [{"name": "body", "in": "body", "required": True,
                "schema": {"type": "object", "properties": {
                    "email": {"type": "string"}, "code": {"type": "string"},
                    "username": {"type": "string"}, "password": {"type": "string"}}}}],
            "responses": _ok}},
        "/api/auth/login":      {"post": {"tags": _auth_tag, "summary": "用户登录 (返回JWT)",
            "parameters": [{"name": "body", "in": "body", "required": True,
                "schema": {"type": "object", "properties": {
                    "username": {"type": "string"}, "password": {"type": "string"}}}}],
            "responses": _ok}},
        "/api/auth/send-code":  {"post": {"tags": _auth_tag, "summary": "发送邮箱验证码",
            "parameters": [{"name": "body", "in": "body", "required": True,
                "schema": {"type": "object", "properties": {
                    "email": {"type": "string"}, "type": {"type": "string", "enum": ["register","reset"]}}}}],
            "responses": _ok}},
        "/api/auth/info":       {"get": {"tags": _auth_tag, "summary": "获取当前登录用户信息", "security": _bearer, "responses": _ok}},
        "/api/auth/health":     {"get": {"tags": _auth_tag, "summary": "认证服务健康检查", "responses": _ok}},

        # ==================== 数据采集 (论文 6.1.1) ====================
        "/api/weibo/crawl/start": {"post": {"tags": _crawl_tag, "summary": "启动微博采集任务",
            "description": "论文 6.1.1: 支持关键词搜索+热搜采集, keywords≤20, pages 1-50, mode=auto/real/synthetic",
            "parameters": [{"name": "body", "in": "body", "required": True,
                "schema": {"type": "object", "properties": {
                    "keywords": {"type": "array", "items": {"type": "string"}},
                    "pages": {"type": "integer", "default": 3},
                    "crawl_hot": {"type": "boolean", "default": True},
                    "max_count": {"type": "integer"},
                    "mode": {"type": "string", "enum": ["auto","real","synthetic"]}}}}],
            "responses": _ok}},
        "/api/weibo/crawl/status/{task_id}": {"get": {"tags": _crawl_tag, "summary": "查询采集任务进度",
            "parameters": [{"name": "task_id", "in": "path", "required": True, "type": "string"}],
            "responses": _ok}},
        "/api/weibo/crawl/data/{task_id}": {"get": {"tags": _crawl_tag, "summary": "获取采集任务原始数据",
            "parameters": [{"name": "task_id", "in": "path", "required": True, "type": "string"}],
            "responses": _ok}},
        "/api/weibo/crawl/tasks":           {"get": {"tags": _crawl_tag, "summary": "采集任务历史列表", "responses": _ok}},
        "/api/weibo/crawl/cookie/status":   {"get": {"tags": _crawl_tag, "summary": "Cookie池状态", "responses": _ok}},
        "/api/weibo/crawl/cookie/save":     {"post": {"tags": _crawl_tag, "summary": "手动保存Cookie",
            "parameters": [{"name": "body", "in": "body", "schema": {"type": "object", "properties": {"cookie": {"type": "string"}}}}],
            "responses": _ok}},
        "/api/weibo/crawl/validate-cookie": {"post": {"tags": _crawl_tag, "summary": "验证Cookie有效性", "responses": _ok}},
        "/api/collection/tasks":            {"get": {"tags": _crawl_tag, "summary": "采集任务管理列表", "responses": _ok}},
        "/api/collection/tasks/{task_id}":  {"get": {"tags": _crawl_tag, "summary": "采集任务详情",
            "parameters": [{"name": "task_id", "in": "path", "required": True, "type": "string"}],
            "responses": _ok}},
        "/api/collection/statistics":       {"get": {"tags": _crawl_tag, "summary": "采集统计总览", "responses": _ok}},
        "/api/weibo/hotsearch":             {"get": {"tags": _crawl_tag, "summary": "微博热搜实时数据", "responses": _ok}},

        # ==================== 数据预处理 (论文 6.3.2) ====================
        "/api/preprocess/tasks": {
            "get": {"tags": _preproc_tag, "summary": "预处理任务列表", "responses": _ok},
            "post": {"tags": _preproc_tag, "summary": "创建预处理任务 (清洗+分词+Spark分布式)",
                "description": "论文 6.3.2: 本地清洗+同时提交Spark作业到集群 (regexp_replace+UDF → Parquet)",
                "parameters": [{"name": "body", "in": "body", "required": True,
                    "schema": {"type": "object", "properties": {
                        "name": {"type": "string"},
                        "cleanRules": {"type": "array", "items": {"type": "string",
                            "enum": ["removeUrl","removeEmoji","removeSpecial","traditional2simplified","fullwidth2halfwidth"]}}}}}],
                "responses": _ok}},
        "/api/preprocess/tasks/{task_id}":      {"get": {"tags": _preproc_tag, "summary": "预处理任务详情",
            "parameters": [{"name": "task_id", "in": "path", "required": True, "type": "string"}], "responses": _ok}},
        "/api/preprocess/tasks/{task_id}/data":  {"get": {"tags": _preproc_tag, "summary": "预处理后数据预览",
            "parameters": [{"name": "task_id", "in": "path", "required": True, "type": "string"}], "responses": _ok}},
        "/api/preprocess/preview":  {"post": {"tags": _preproc_tag, "summary": "清洗规则预览 (不入库)", "responses": _ok}},
        "/api/preprocess/stopwords": {
            "get": {"tags": _preproc_tag, "summary": "获取停用词列表", "responses": _ok},
            "post": {"tags": _preproc_tag, "summary": "保存自定义停用词", "responses": _ok}},

        # ==================== 情感分析 (论文 4.2.1 + 6.3.3) ====================
        "/api/sentiment/analyze": {"post": {"tags": _sent_tag, "summary": "单条文本情感分析 (词典+BERT级联)",
            "description": "论文 4.2.1: 先词典θ阈值筛选, 不确定样本送BERT精调模型",
            "parameters": [{"name": "body", "in": "body", "required": True,
                "schema": {"type": "object", "properties": {
                    "text": {"type": "string"}, "method": {"type": "string", "enum": ["lexicon","bert","hybrid"]}}}}],
            "responses": _ok}},
        "/api/sentiment/batch-analyze": {"post": {"tags": _sent_tag, "summary": "批量情感分析 (支持Spark调用)",
            "description": "论文 6.3.3: Spark foreachPartition → Flask批量推理 → MySQL",
            "parameters": [{"name": "body", "in": "body", "required": True,
                "schema": {"type": "object", "properties": {
                    "texts": {"type": "array", "items": {"type": "string"}},
                    "method": {"type": "string", "default": "hybrid"},
                    "batch_size": {"type": "integer", "default": 32}}}}],
            "responses": _ok}},
        "/api/sentiment/run-db":       {"post": {"tags": _sent_tag, "summary": "对MySQL中微博执行批量情感分析", "responses": _ok}},
        "/api/sentiment/distribution": {"get": {"tags": _sent_tag, "summary": "情感分布统计 (positive/neutral/negative)", "responses": _ok}},
        "/api/sentiment/trend":        {"get": {"tags": _sent_tag, "summary": "情感趋势时间序列", "responses": _ok}},
        "/api/sentiment/heatmap":      {"get": {"tags": _sent_tag, "summary": "情感热力图数据", "responses": _ok}},
        "/api/sentiment/results":      {"get": {"tags": _sent_tag, "summary": "情感分析结果列表", "responses": _ok}},
        "/api/sentiment/statistics":   {"get": {"tags": _sent_tag, "summary": "情感分析统计概览", "responses": _ok}},
        "/api/sentiment/bert/info":    {"get": {"tags": _sent_tag, "summary": "BERT模型信息 (版本/路径/设备)", "responses": _ok}},
        "/api/sentiment/health":       {"get": {"tags": _sent_tag, "summary": "情感分析服务健康检查", "responses": _ok}},

        # ==================== 三维度排序 (论文 4.2.2) ====================
        "/api/tri-dimension/analyze":       {"post": {"tags": _tri_tag, "summary": "三维度加权排序 (α·情感+β·热度+γ·时效)",
            "description": "论文 4.2.2: 默认权重 α=0.4, β=0.4, γ=0.2, NDCG@10=0.9051",
            "parameters": [{"name": "body", "in": "body",
                "schema": {"type": "object", "properties": {
                    "data": {"type": "array", "items": {"type": "object"}},
                    "sentiment_weight": {"type": "number", "default": 0.4},
                    "heat_weight": {"type": "number", "default": 0.4},
                    "time_weight": {"type": "number", "default": 0.2}}}}],
            "responses": _ok}},
        "/api/tri-dimension/ranking-from-db": {"get": {"tags": _tri_tag, "summary": "从MySQL读取微博并三维度排序", "responses": _ok}},
        "/api/tri-dimension/run-db":          {"post": {"tags": _tri_tag, "summary": "执行三维度排序并写回数据库", "responses": _ok}},
        "/api/tri-dimension/scatter":         {"post": {"tags": _tri_tag, "summary": "散点图数据 (情感×热度×时效)", "responses": _ok}},
        "/api/tri-dimension/formula":         {"get": {"tags": _tri_tag, "summary": "排序公式说明", "responses": _ok}},
        "/api/tri-dimension/config":  {
            "get": {"tags": _tri_tag, "summary": "获取排序权重配置", "responses": _ok},
            "post": {"tags": _tri_tag, "summary": "保存排序权重配置", "responses": _ok}},
        "/api/tri-dimension/health":          {"get": {"tags": _tri_tag, "summary": "三维度排序服务健康检查", "responses": _ok}},

        # ==================== Spark 大数据 (论文 6.3) ====================
        "/api/weibo/spark/info":    {"get": {"tags": _spark_tag, "summary": "Spark集群连接信息", "responses": _ok}},
        "/api/weibo/spark/jobs":    {"get": {"tags": _spark_tag, "summary": "Spark作业列表+统计", "responses": _ok}},
        "/api/weibo/spark/jobs/{job_id}": {"get": {"tags": _spark_tag, "summary": "Spark作业状态详情",
            "parameters": [{"name": "job_id", "in": "path", "required": True, "type": "string"}],
            "responses": _ok}},
        "/api/weibo/spark/jobs/{job_id}/cancel": {"post": {"tags": _spark_tag, "summary": "取消Spark作业",
            "parameters": [{"name": "job_id", "in": "path", "required": True, "type": "string"}],
            "responses": _ok}},
        "/api/weibo/spark/submit/clean":     {"post": {"tags": _spark_tag,
            "summary": "论文 6.3.2: 提交PySpark清洗作业到Standalone集群",
            "description": "HDFS /raw/dt=YYYY-MM-DD/*.json → regexp_replace+UDF → Parquet /cleaned/dt=YYYY-MM-DD",
            "responses": _ok}},
        "/api/weibo/spark/submit/sentiment": {"post": {"tags": _spark_tag,
            "summary": "论文 6.3.3: 提交PySpark分布式情感分析 (foreachPartition→Flask→MySQL)",
            "responses": _ok}},

        # ==================== 数据流水线 (论文 6.1.6) ====================
        "/api/pipeline/run":      {"post": {"tags": _pipe_tag, "summary": "一键运行数据流水线 (采集→清洗→情感→排序)", "responses": _ok}},
        "/api/pipeline/run-async":{"post": {"tags": _pipe_tag, "summary": "异步运行流水线", "responses": _ok}},
        "/api/pipeline/status":   {"get": {"tags": _pipe_tag, "summary": "流水线运行状态", "responses": _ok}},
        "/api/pipeline/history":  {"get": {"tags": _pipe_tag, "summary": "流水线执行历史", "responses": _ok}},
        "/api/pipeline/stats":    {"get": {"tags": _pipe_tag, "summary": "流水线统计数据", "responses": _ok}},
        "/api/pipeline/ranking":  {"get": {"tags": _pipe_tag, "summary": "流水线排序结果", "responses": _ok}},

        # ==================== 实时监控 (论文 6.1.5) ====================
        "/api/monitor/statistics":     {"get": {"tags": _mon_tag, "summary": "实时舆情监控统计 (5s轮询)", "responses": _ok}},
        "/api/monitor/alerts":         {"get": {"tags": _mon_tag, "summary": "当前活跃告警", "responses": _ok}},
        "/api/monitor/alerts/history": {"get": {"tags": _mon_tag, "summary": "告警历史记录", "responses": _ok}},
        "/api/monitor/alerts/rules":   {
            "get": {"tags": _mon_tag, "summary": "获取告警规则", "responses": _ok},
            "put": {"tags": _mon_tag, "summary": "更新告警规则", "responses": _ok}},
        "/api/monitor/keywords":       {
            "get":    {"tags": _mon_tag, "summary": "监控关键词列表", "responses": _ok},
            "post":   {"tags": _mon_tag, "summary": "添加监控关键词", "responses": _ok},
            "delete": {"tags": _mon_tag, "summary": "删除监控关键词", "responses": _ok}},
        "/api/monitor/metrics":        {"get": {"tags": _mon_tag, "summary": "系统性能指标", "responses": _ok}},
        "/api/monitor/stream":         {"get": {"tags": _mon_tag, "summary": "SSE实时推送数据流", "responses": _ok}},

        # ==================== 可视化仪表盘 (论文 6.1.7) ====================
        "/api/dashboard/overview":                {"get": {"tags": _dash_tag, "summary": "仪表盘聚合数据", "responses": _ok}},
        "/api/dashboard/sentiment-distribution":  {"get": {"tags": _dash_tag, "summary": "情感分布饼图数据", "responses": _ok}},
        "/api/dashboard/hot-topics":              {"get": {"tags": _dash_tag, "summary": "热门话题排行", "responses": _ok}},
        "/api/dashboard/trend":                   {"get": {"tags": _dash_tag, "summary": "趋势折线图数据", "responses": _ok}},
        "/api/dashboard/realtime":                {"get": {"tags": _dash_tag, "summary": "实时数据面板", "responses": _ok}},
        "/api/dashboard/alerts":                  {"get": {"tags": _dash_tag, "summary": "仪表盘告警列表", "responses": _ok}},
        "/api/dashboard/spark/status":            {"get": {"tags": _dash_tag, "summary": "Spark集群状态", "responses": _ok}},
        "/api/dashboard/spark/jobs":              {"get": {"tags": _dash_tag, "summary": "Spark作业概览", "responses": _ok}},

        # ==================== 用户行为分析 ====================
        "/api/behavior/stats":   {"get": {"tags": _behavior_tag, "summary": "用户行为统计", "responses": _ok}},
        "/api/behavior/network": {"get": {"tags": _behavior_tag, "summary": "用户关系网络", "responses": _ok}},
        "/api/behavior/users":   {"get": {"tags": _behavior_tag, "summary": "活跃用户列表", "responses": _ok}},

        # ==================== 传播网络 ====================
        "/api/propagation/network":               {"get": {"tags": _behavior_tag, "summary": "传播网络图数据", "responses": _ok}},
        "/api/propagation/influence-ranking":      {"get": {"tags": _behavior_tag, "summary": "影响力排行", "responses": _ok}},

        # ==================== 模型评估 (论文 5.3) ====================
        "/api/evaluation/sentiment":         {"post": {"tags": _eval_tag, "summary": "情感模型评估 (Acc/F1/混淆矩阵)",
            "description": "论文 5.3: 纯BERT Acc=87.79%, 级联θ=0.7 Acc=85.73%", "responses": _ok}},
        "/api/evaluation/tri-dimension":     {"post": {"tags": _eval_tag, "summary": "三维度排序评估 (NDCG/MAP)",
            "description": "论文 5.3: 本文(0.4,0.4,0.2) NDCG@10=0.9051, 优于仅热度基线46.4%", "responses": _ok}},
        "/api/evaluation/benchmark":         {"post": {"tags": _eval_tag, "summary": "批量推理性能基准测试", "responses": _ok}},

        # ==================== 管理员 (论文 6.1.8, 需 JWT role=admin) ====================
        "/api/admin/users":               {"get": {"tags": _adm_tag, "summary": "用户列表", "security": _bearer, "responses": _ok}},
        "/api/admin/system/metrics":      {"get": {"tags": _adm_tag, "summary": "系统指标 (CPU/内存/磁盘)", "security": _bearer, "responses": _ok}},
        "/api/admin/logs":                {"get": {"tags": _adm_tag, "summary": "操作日志列表", "security": _bearer, "responses": _ok}},
        "/api/admin/config/{scope}":      {"get": {"tags": _adm_tag, "summary": "获取系统配置 (database/email/spark/system)",
            "parameters": [{"name": "scope", "in": "path", "required": True, "type": "string"}],
            "security": _bearer, "responses": _ok}},
        "/api/admin/spark/restart":       {"post": {"tags": _adm_tag, "summary": "重启Spark集群连接", "security": _bearer, "responses": _ok}},

        # ==================== 统一API v2 ====================
        "/api/v2/health":                    {"get": {"tags": _mon_tag, "summary": "系统健康检查 (v2)", "responses": _ok}},
        "/api/v2/stats/overview":            {"get": {"tags": _dash_tag, "summary": "统计总览 (v2)", "responses": _ok}},
        "/api/v2/crawl/start":               {"post": {"tags": _crawl_tag, "summary": "启动采集 (v2)", "responses": _ok}},
        "/api/v2/crawl/hot-search":          {"get": {"tags": _crawl_tag, "summary": "微博热搜数据 (v2)", "responses": _ok}},
        "/api/v2/sentiment/analyze":         {"post": {"tags": _sent_tag, "summary": "情感分析 (v2)", "responses": _ok}},
        "/api/v2/sentiment/distribution":    {"get": {"tags": _sent_tag, "summary": "情感分布 (v2)", "responses": _ok}},
        "/api/v2/ranking/tri-dimension":     {"post": {"tags": _tri_tag, "summary": "三维度排序 (v2)", "responses": _ok}},
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
            {"name": "auth",          "description": "用户认证 - 注册/登录/JWT (论文 6.1.8)"},
            {"name": "crawler",       "description": "数据采集 - 微博爬虫+热搜+Cookie管理 (论文 6.1.1)"},
            {"name": "preprocess",    "description": "数据预处理 - 清洗+分词+Spark分布式清洗 (论文 6.3.2)"},
            {"name": "sentiment",     "description": "情感分析 - 词典+BERT级联融合 (论文 4.2.1, Acc=87.79%)"},
            {"name": "tri-dimension", "description": "三维度排序 - α·情感+β·热度+γ·时效 (论文 4.2.2, NDCG@10=0.9051)"},
            {"name": "spark",         "description": "Spark大数据作业 - 分布式清洗与情感分析 (论文 6.3)"},
            {"name": "pipeline",      "description": "数据流水线 - 一键采集→清洗→分析→排序 (论文 6.1.6)"},
            {"name": "monitor",       "description": "实时舆情监控 - 告警+关键词+SSE推送 (论文 6.1.5)"},
            {"name": "dashboard",     "description": "可视化仪表盘 - 统计+趋势+Spark状态 (论文 6.1.7)"},
            {"name": "behavior",      "description": "用户行为分析 - 关系网络+传播图"},
            {"name": "evaluation",    "description": "模型评估 - 情感/排序指标+基准测试 (论文 5.3)"},
            {"name": "admin",         "description": "系统管理 - 用户/配置/日志 (论文 6.1.8, 需JWT)"},
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

# 根路由: 重定向到 Swagger API 文档 (论文 6.2.2 图6-9)
@app.route('/')
def index():
    from flask import redirect
    if SWAGGER_AVAILABLE:
        return redirect('/apidocs/')
    return jsonify({
        'message': '微博情感分析系统API',
        'version': '2.0.0',
        'description': '基于Spark的分布式微博情感分析系统',
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


_bg_services_started = False

def _start_background_services():
    """启动后台常驻服务（热搜爬虫等），随 Flask 进程自动运行"""
    global _bg_services_started
    if _bg_services_started:
        return
    _bg_services_started = True
    try:
        from services.live_hot_search_service import start_live_hot_search, LiveHotSearchConfig
        hot_cfg = LiveHotSearchConfig(
            refresh_interval=300,
            weibos_per_topic=15,
            top_n_topics=10,
        )
        service = start_live_hot_search(hot_cfg)
        logger.info(f"热搜后台爬虫已启动 (刷新间隔: {hot_cfg.refresh_interval}s)")
    except Exception as e:
        logger.warning(f"热搜后台爬虫启动失败（不影响其他功能）: {e}")

    # 实时 Feed 爬虫: 30s 抓取微博官方"实时"流入库, 供仪表盘使用
    try:
        from services import realtime_feed_crawler
        realtime_feed_crawler.start(interval=30)
        logger.info("实时 Feed 后台爬虫已启动 (interval=30s)")
    except Exception as e:
        logger.warning(f"实时 Feed 爬虫启动失败（不影响其他功能）: {e}")


# 延迟到第一个请求时在 worker 进程中启动后台爬虫
# (gunicorn --preload 在 master 进程执行模块级代码, fork 后 worker 不继承线程)
@app.before_request
def _ensure_bg_services():
    _start_background_services()


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
