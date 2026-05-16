# ====================================================================
# 微博情感分析系统 - Flask 后端 Dockerfile
# ====================================================================
# 构建上下文: 项目根目录 (context: ..)
# ====================================================================

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Asia/Shanghai \
    JAVA_HOME=/usr/lib/jvm/default-java \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 安装系统依赖 (含 MySQL 客户端库, 时区数据, chromium for selenium 扫码登录)
RUN (if [ -f /etc/apt/sources.list.d/debian.sources ]; then sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources; fi) \
    && (if [ -f /etc/apt/sources.list ]; then sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list; fi) \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
        procps \
        default-jre-headless \
        default-libmysqlclient-dev \
        pkg-config \
        tzdata \
        chromium \
        chromium-driver \
        fonts-liberation \
        libnss3 \
        libxss1 \
        libasound2 \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件 (注意: 构建上下文为项目根目录)
COPY backend-python/requirements.txt .

# 安装 Python 依赖 (国内镜像加速)
# pip 全局重试/超时配置 (国内镜像偶发 IncompleteRead)
RUN pip config set global.retries 10 \
    && pip config set global.timeout 300 \
    && pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip config set global.trusted-host mirrors.aliyun.com

# 关键: 先装 PyTorch CPU 版 (~200MB), 避免默认拉取 ~2.5GB 的 NVIDIA CUDA 库
# torch 优先用清华源 (阿里云 pytorch-wheels 镜像 IncompleteRead 频繁), 阿里云作 fallback
RUN pip install --upgrade pip \
    && (pip install torch --index-url https://pypi.tuna.tsinghua.edu.cn/simple/ --extra-index-url https://download.pytorch.org/whl/cpu \
        || pip install torch --index-url https://mirrors.aliyun.com/pytorch-wheels/cpu/ \
        || pip install torch) \
    && pip install -r requirements.txt \
    && pip install gunicorn \
    && rm -rf /root/.cache/pip

# 复制应用代码
COPY backend-python/ ./backend/

# 创建非 root 用户
RUN useradd -m -u 1000 appuser \
    && mkdir -p logs model_cache \
    && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -sf http://localhost:5000/api/v2/health || curl -sf http://localhost:5000/ || exit 1

# 启动命令
CMD ["gunicorn", \
    "--bind", "0.0.0.0:5000", \
    "--workers", "1", \
    "--threads", "4", \
    "--timeout", "120", \
    "--preload", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "--chdir", "backend", \
    "app:app"]
