#!/bin/bash
# ====================================================================
# 微博情感分析系统 - Ubuntu 24 本地开发启动脚本
# ====================================================================
# 使用方法: chmod +x start-dev.sh && ./start-dev.sh
# 停止方法: Ctrl+C (会自动清理所有子进程)
# 参数:
#   --skip-java       跳过Java后端
#   --skip-python     跳过Python后端
#   --skip-frontend   跳过前端
#   --build-java      强制重新构建Java后端
#   --install-deps    安装系统依赖 (需要sudo)
#   --cascade-mode    启用 cascade 级联情感分析 (词典→BERT自动升级)
#   --restart-spark   仅重启 Spark 服务 (参数变更后使用)
# ====================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PIDS=()

SKIP_JAVA=false
SKIP_PYTHON=false
SKIP_FRONTEND=false
BUILD_JAVA=false
INSTALL_DEPS=false
CASCADE_MODE=false
RESTART_SPARK_ONLY=false

# PID 文件 (用于 stop-dev.sh 定点终止)
PID_FILE="${PROJECT_ROOT}/.dev-pids"

# 解析参数
for arg in "$@"; do
    case $arg in
        --skip-java)      SKIP_JAVA=true ;;
        --skip-python)    SKIP_PYTHON=true ;;
        --skip-frontend)  SKIP_FRONTEND=true ;;
        --build-java)     BUILD_JAVA=true ;;
        --install-deps)   INSTALL_DEPS=true ;;
        --cascade-mode)   CASCADE_MODE=true ;;
        --restart-spark)  RESTART_SPARK_ONLY=true ;;
        *) echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

# 清理函数
cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止服务...${NC}"
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    done
    rm -f "${PID_FILE}" 2>/dev/null
    echo -e "${GREEN}所有服务已停止${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Spark 重启函数 — 通过 HTTP API 通知 Flask 后端重启 Spark
# 对应后端路由: POST /api/admin/spark/restart (admin.py)
restart_spark_service() {
    echo -e "${YELLOW}正在通过 HTTP API 重启 Spark 服务...${NC}"

    # 先检查 Flask 是否在运行
    local flask_port=5000
    local flask_ok
    flask_ok=$(curl -sf -o /dev/null -w "%{http_code}" "http://localhost:${flask_port}/" 2>/dev/null || echo "000")
    if [[ "${flask_ok}" == "000" ]]; then
        echo -e "  ${RED}Flask 后端未运行 (端口 ${flask_port})，无法重启 Spark${NC}"
        echo -e "  ${YELLOW}请先启动 Flask: ./start-dev.sh --skip-java --skip-frontend${NC}"
        return 1
    fi

    # 调用 localhost-only 免认证内部 API
    local response
    response=$(curl -sf -X POST "http://localhost:${flask_port}/api/admin/spark/restart-internal" \
        -H "Content-Type: application/json" \
        -d '{"confirm": true}' \
        --max-time 30 2>&1) || true

    if echo "${response}" | grep -q '"code": 200\|"code":200'; then
        echo -e "  ${GREEN}Spark 重启请求已被接受${NC}"
        echo -e "  ${CYAN}响应: ${response}${NC}"
    else
        echo -e "  ${YELLOW}Spark 重启响应: ${response:-无响应}${NC}"
        echo -e "  ${YELLOW}请确认 Flask 后端已启动且注册了 admin_bp 蓝图${NC}"
    fi
}

# 如果仅重启 Spark
if [[ "${RESTART_SPARK_ONLY}" == "true" ]]; then
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN} Spark 服务重启 (核心参数变更后使用)${NC}"
    echo -e "${CYAN}============================================${NC}"
    restart_spark_service
    echo -e "${GREEN}Spark 重启完成${NC}"
    exit 0
fi

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN} 微博情感分析系统 - 本地开发环境启动${NC}"
echo -e "${CYAN} 改进: 线程安全采集 / cascade分析 / Spark热重载${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# 清空旧 PID 文件
> "${PID_FILE}"

# ==================== 安装系统依赖 (可选) ====================
if [ "$INSTALL_DEPS" = true ]; then
    echo -e "${YELLOW}[0/6] 安装系统依赖 (sudo)...${NC}"
    sudo apt-get update -qq
    
    # Node.js (v20 LTS)
    if ! command -v node &>/dev/null; then
        echo -e "  安装 Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y -qq nodejs
    fi
    
    # Python 3 + pip
    if ! command -v python3 &>/dev/null; then
        echo -e "  安装 Python3..."
        sudo apt-get install -y -qq python3 python3-pip python3-venv
    fi
    
    # Java 11
    if ! command -v java &>/dev/null; then
        echo -e "  安装 Java 11..."
        sudo apt-get install -y -qq openjdk-11-jdk
    fi
    
    # Maven
    if ! command -v mvn &>/dev/null; then
        echo -e "  安装 Maven..."
        sudo apt-get install -y -qq maven
    fi
    
    # MySQL
    if ! command -v mysql &>/dev/null; then
        echo -e "  安装 MySQL..."
        sudo apt-get install -y -qq mysql-server
        sudo systemctl enable mysql
        sudo systemctl start mysql
    fi
    
    # Redis
    if ! command -v redis-cli &>/dev/null; then
        echo -e "  安装 Redis..."
        sudo apt-get install -y -qq redis-server
        sudo systemctl enable redis-server
        sudo systemctl start redis-server
    fi
    
    echo -e "${GREEN}  系统依赖安装完成${NC}"
    echo ""
fi

# ==================== 环境检查 ====================
echo -e "${YELLOW}[1/6] 检查环境依赖...${NC}"

# 适配 python/python3 命令
PYTHON_CMD="python3"
if ! command -v python3 &>/dev/null; then
    if command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "  ${RED}[FAIL] Python 未安装${NC}"
        exit 1
    fi
fi

# 适配 pip/pip3 命令
PIP_CMD="pip3"
if ! command -v pip3 &>/dev/null; then
    if command -v pip &>/dev/null; then
        PIP_CMD="pip"
    else
        echo -e "  ${RED}[FAIL] pip 未安装${NC}"
        exit 1
    fi
fi

command -v node &>/dev/null && echo -e "  ${GREEN}Node.js: $(node --version)${NC}" || { echo -e "  ${RED}[FAIL] Node.js 未安装${NC}"; exit 1; }
echo -e "  ${GREEN}Python:  $($PYTHON_CMD --version 2>&1)${NC}"

if ! $SKIP_JAVA; then
    command -v java &>/dev/null && echo -e "  ${GREEN}Java:    $(java -version 2>&1 | head -1)${NC}" || { echo -e "  ${YELLOW}[WARN] Java 未安装，跳过Java后端${NC}"; SKIP_JAVA=true; }
    command -v mvn &>/dev/null && echo -e "  ${GREEN}Maven:   $(mvn --version 2>&1 | head -1)${NC}" || { echo -e "  ${YELLOW}[WARN] Maven 未安装，跳过Java后端${NC}"; SKIP_JAVA=true; }
fi

# ==================== 检查数据库服务 ====================
echo ""
echo -e "${YELLOW}[2/6] 检查数据库服务...${NC}"

if nc -z localhost 3306 2>/dev/null; then
    echo -e "  ${GREEN}MySQL  :3306  [OK]${NC}"
else
    echo -e "  ${RED}MySQL  :3306  [FAIL] 请先启动MySQL: sudo systemctl start mysql${NC}"
    exit 1
fi

if nc -z localhost 6379 2>/dev/null; then
    echo -e "  ${GREEN}Redis  :6379  [OK]${NC}"
else
    echo -e "  ${YELLOW}Redis  :6379  [WARN] Redis未运行，部分缓存功能不可用${NC}"
fi

# ==================== 创建 .env ====================
echo ""
echo -e "${YELLOW}[3/6] 检查配置文件...${NC}"

ENV_FILE="$PROJECT_ROOT/backend-python/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "  创建 backend-python/.env ..."
    cat > "$ENV_FILE" << 'ENVEOF'
# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=weibo_sentiment_graduation
DB_USER=root
DB_PASSWORD=123456

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=123456

# Flask
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=true
SECRET_KEY=dev-secret-key-for-local-testing-only-2024
CORS_ORIGINS=http://localhost:3001,http://127.0.0.1:3001,http://localhost:5173

# Spark (local mode)
SPARK_MASTER_URL=local[*]

# Cascade sentiment analysis
CASCADE_THRESHOLD=0.7

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/app.log

# Model
CONFIDENCE_THRESHOLD=0.7
MODEL_USE_GPU=false
ENVEOF
    echo -e "  ${GREEN}.env 已创建${NC}"
else
    echo -e "  ${GREEN}.env 已存在${NC}"
fi

# 确保 logs 目录存在
mkdir -p "$PROJECT_ROOT/backend-python/logs"

# ==================== 安装依赖 ====================
echo ""
echo -e "${YELLOW}[4/6] 检查并安装依赖...${NC}"

# 前端依赖
if [ "$SKIP_FRONTEND" = false ]; then
    if [ ! -d "$PROJECT_ROOT/web-frontend/node_modules" ]; then
        echo -e "  安装前端依赖 (npm install)..."
        (cd "$PROJECT_ROOT/web-frontend" && npm install --quiet 2>&1) || true
        echo -e "  ${GREEN}前端依赖安装完成${NC}"
    else
        echo -e "  ${GREEN}前端依赖已存在${NC}"
    fi
fi

# Python 依赖
if [ "$SKIP_PYTHON" = false ]; then
    echo -e "  检查Python依赖..."
    $PIP_CMD install -q flask flask-cors python-dotenv pymysql redis DBUtils jieba numpy pandas requests pyspark 2>/dev/null || true
    echo -e "  ${GREEN}Python依赖已就绪${NC}"
fi

# Java 构建
if [ "$SKIP_JAVA" = false ]; then
    JAR_FILE="$PROJECT_ROOT/web-backend/target/web-backend-1.0-SNAPSHOT.jar"
    if [ "$BUILD_JAVA" = true ] || [ ! -f "$JAR_FILE" ]; then
        echo -e "  构建Java后端 (mvn package)..."
        (cd "$PROJECT_ROOT" && mvn -pl web-backend -am clean package -DskipTests -q 2>&1) || true
        if [ -f "$JAR_FILE" ]; then
            echo -e "  ${GREEN}Java后端构建成功${NC}"
        else
            echo -e "  ${RED}Java后端构建失败，跳过${NC}"
            SKIP_JAVA=true
        fi
    else
        echo -e "  ${GREEN}Java JAR已存在${NC}"
    fi
fi

# ==================== 启动服务 ====================
echo ""
echo -e "${YELLOW}[5/6] 启动服务...${NC}"

# 启动前端 (port 3001)
if [ "$SKIP_FRONTEND" = false ]; then
    echo -e "  ${CYAN}启动前端 (http://localhost:3001) ...${NC}"
    (cd "$PROJECT_ROOT/web-frontend" && npm run dev) &
    PIDS+=($!)
    echo "frontend=$!" >> "${PID_FILE}"
fi

# 启动 Python Flask (port 5000)
if [ "$SKIP_PYTHON" = false ]; then
    echo -e "  ${CYAN}启动Flask后端 (http://localhost:5000) ...${NC}"
    if [ "$CASCADE_MODE" = true ]; then
        echo -e "  ${GREEN}[CASCADE] 级联情感分析已启用 (threshold=0.7)${NC}"
        export SENTIMENT_MODE=cascade
    fi
    (cd "$PROJECT_ROOT/backend-python" && $PYTHON_CMD app.py) &
    PIDS+=($!)
    echo "flask=$!" >> "${PID_FILE}"
fi

# 启动 Java Spring Boot (port 8081)
if [ "$SKIP_JAVA" = false ]; then
    echo -e "  ${CYAN}启动Java后端 (http://localhost:8081) ...${NC}"
    java -jar "$PROJECT_ROOT/web-backend/target/web-backend-1.0-SNAPSHOT.jar" \
        --spring.profiles.active=dev \
        --DB_NAME=weibo_sentiment_graduation &
    PIDS+=($!)
    echo "java=$!" >> "${PID_FILE}"
fi

# ==================== 等待就绪 ====================
echo ""
echo -e "${YELLOW}[6/6] 等待服务就绪...${NC}"
sleep 10

check_service() {
    local name=$1 url=$2
    for i in $(seq 1 30); do
        code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
        if [ "$code" = "200" ]; then
            echo -e "  ${GREEN}$name [OK]${NC}"
            return 0
        fi
        sleep 2
    done
    echo -e "  ${RED}$name [TIMEOUT]${NC}"
    return 1
}

# TCP 端口检查 (用于 Java — 不依赖特定 HTTP 路径)
check_port() {
    local name=$1 port=$2
    for i in $(seq 1 30); do
        if (echo >/dev/tcp/localhost/"$port") 2>/dev/null; then
            echo -e "  ${GREEN}$name [OK] (port ${port})${NC}"
            return 0
        fi
        sleep 2
    done
    echo -e "  ${RED}$name [TIMEOUT] (port ${port})${NC}"
    return 1
}

[ "$SKIP_FRONTEND" = false ] && check_service "Frontend (Vue)" "http://localhost:3001/"
[ "$SKIP_PYTHON" = false ]   && check_service "Flask API"      "http://localhost:5000/"
[ "$SKIP_JAVA" = false ]     && check_port    "Java API"       8081

# ==================== 完成 ====================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN} 所有服务已启动！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "  前端界面:   http://localhost:3001"
echo -e "  Flask API:  http://localhost:5000"
echo -e "  Java  API:  http://localhost:8081/api"
echo -e "  Swagger UI: http://localhost:8081/api/swagger-ui.html"
echo ""
echo -e "  ${CYAN}改进功能:${NC}"
echo -e "    采集任务:  threading.Event 线程安全暂停/恢复/终止"
echo -e "    情感分析:  cascade 级联模式 (词典→BERT自动升级)"
echo -e "    预处理:    繁→简转换蓝色高亮 + 删除红色标注"
echo -e "    流水线:    终止按钮 + clearHistory 后端 DELETE"
echo -e "    热点分析:  四象限分类标签 (情感×热度)"
echo -e "    网络图:    节点颜色=情感 / 大小=转发量 / 富tooltip"
echo -e "    监控:      visibilitychange 自动停止标题闪烁"
echo -e "    Spark:     核心参数变更→提示重启 / 非核心→热加载"
echo ""
echo -e "  ${CYAN}管理命令:${NC}"
echo -e "    ./start-dev.sh --restart-spark   仅重启Spark服务"
echo -e "    ./start-dev.sh --cascade-mode    启用级联分析模式"
echo -e "    ./stop-dev.sh                    停止所有服务"
echo ""
echo -e "  PID 文件: ${PID_FILE}"
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo ""

# 等待子进程
wait
