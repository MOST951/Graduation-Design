# ====================================================================
# 微博情感分析系统 - Flask 后端 Dockerfile
# ====================================================================

FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
        && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY backend/requirements.txt .

# 安装Python依赖
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install gunicorn

# 复制应用代码
COPY backend/ ./backend/
COPY config/ ./config/

# 创建非root用户
RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

# 创建必要目录
RUN mkdir -p logs model_cache

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# 启动命令
CMD ["gunicorn", \
    "--bind", "0.0.0.0:5000", \
    "--workers", "2", \
    "--threads", "2", \
    "--timeout", "120", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "--chdir", "backend", \
    "app:app"]
