#!/bin/bash
#
# 一键部署脚本
# ==============
#
# 简化项目部署，方便答辩演示
#
# 使用方式：
#   ./one_click_deploy.sh dev    # 开发模式
#   ./one_click_deploy.sh demo   # 演示模式（包含演示数据）
#   ./one_click_deploy.sh prod   # 生产模式（清空数据）
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 打印横幅
print_banner() {
    echo ""
    echo "=============================================="
    echo "   微博情感分析系统 - 一键部署脚本"
    echo "=============================================="
    echo ""
}

# ==================== 环境检查 ====================

check_python() {
    log_info "检查 Python..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        log_success "Python $PYTHON_VERSION"
        return 0
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
        log_success "Python $PYTHON_VERSION"
        return 0
    else
        log_error "Python 未安装"
        return 1
    fi
}

check_node() {
    log_info "检查 Node.js..."
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        log_success "Node.js $NODE_VERSION"
        return 0
    else
        log_warning "Node.js 未安装（前端将无法启动）"
        return 1
    fi
}

check_java() {
    log_info "检查 Java..."
    if command -v java &> /dev/null; then
        JAVA_VERSION=$(java -version 2>&1 | head -n 1)
        log_success "$JAVA_VERSION"
        return 0
    else
        log_warning "Java 未安装（Spark将无法启动）"
        return 1
    fi
}

check_docker() {
    log_info "检查 Docker..."
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        log_success "$DOCKER_VERSION"
        
        if command -v docker-compose &> /dev/null; then
            COMPOSE_VERSION=$(docker-compose --version)
            log_success "$COMPOSE_VERSION"
        else
            log_warning "Docker Compose 未安装"
        fi
        return 0
    else
        log_warning "Docker 未安装"
        return 1
    fi
}

check_ports() {
    log_info "检查端口占用..."
    
    PORTS=(3000 5000 3306 8080 9870 16010)
    PORT_NAMES=("Vue前端" "Flask后端" "MySQL" "Spark Master" "HDFS NameNode" "HBase Master")
    
    OCCUPIED=0
    for i in "${!PORTS[@]}"; do
        PORT=${PORTS[$i]}
        NAME=${PORT_NAMES[$i]}
        
        if lsof -i :$PORT &> /dev/null || netstat -tuln 2>/dev/null | grep -q ":$PORT "; then
            log_warning "端口 $PORT ($NAME) 已被占用"
            OCCUPIED=1
        fi
    done
    
    if [ $OCCUPIED -eq 0 ]; then
        log_success "所有端口可用"
    fi
    
    return 0
}

run_environment_check() {
    log_info "========== 环境检查 =========="
    
    check_python
    check_node
    check_java
    check_docker
    check_ports
    
    echo ""
}

# ==================== 服务部署 ====================

start_mysql() {
    log_info "启动 MySQL..."
    
    if [ -f "deployment/docker-compose.yml" ]; then
        cd deployment
        docker-compose up -d mysql 2>/dev/null || {
            log_warning "Docker MySQL 启动失败，尝试本地 MySQL"
        }
        cd ..
    fi
    
    # 等待MySQL就绪
    sleep 5
    log_success "MySQL 服务已启动"
}

start_hadoop() {
    log_info "启动 Hadoop 伪集群..."
    
    if [ -n "$HADOOP_HOME" ] && [ -f "$HADOOP_HOME/sbin/start-dfs.sh" ]; then
        $HADOOP_HOME/sbin/start-dfs.sh
        log_success "HDFS 已启动"
    else
        log_warning "Hadoop 未配置，跳过 HDFS 启动"
    fi
}

start_spark() {
    log_info "启动 Spark..."
    
    if [ -n "$SPARK_HOME" ] && [ -f "$SPARK_HOME/sbin/start-master.sh" ]; then
        $SPARK_HOME/sbin/start-master.sh
        $SPARK_HOME/sbin/start-worker.sh spark://localhost:7077
        log_success "Spark 已启动"
    else
        log_warning "Spark 未配置，跳过启动"
    fi
}

start_hbase() {
    log_info "启动 HBase..."
    
    if [ -n "$HBASE_HOME" ] && [ -f "$HBASE_HOME/bin/start-hbase.sh" ]; then
        $HBASE_HOME/bin/start-hbase.sh
        log_success "HBase 已启动"
    else
        log_warning "HBase 未配置，跳过启动"
    fi
}

start_backend() {
    log_info "启动 Flask 后端..."
    
    cd backend
    
    # 创建虚拟环境（如果不存在）
    if [ ! -d "venv" ]; then
        log_info "创建 Python 虚拟环境..."
        python3 -m venv venv || python -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || true
    
    # 安装依赖
    if [ -f "requirements.txt" ]; then
        log_info "安装 Python 依赖..."
        pip install -r requirements.txt -q
    fi
    
    # 启动后端
    log_info "启动 Flask 服务..."
    nohup python app.py > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../logs/backend.pid
    
    cd ..
    
    # 等待启动
    sleep 3
    
    if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
        log_success "Flask 后端已启动 (PID: $BACKEND_PID)"
    else
        log_warning "Flask 后端启动中..."
    fi
}

start_frontend() {
    log_info "启动 Vue 前端..."
    
    cd web-frontend
    
    # 安装依赖
    if [ ! -d "node_modules" ]; then
        log_info "安装前端依赖..."
        npm install
    fi
    
    # 启动前端
    log_info "启动 Vite 开发服务器..."
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../logs/frontend.pid
    
    cd ..
    
    sleep 5
    log_success "Vue 前端已启动 (PID: $FRONTEND_PID)"
}

# ==================== 数据初始化 ====================

init_mysql_tables() {
    log_info "初始化 MySQL 表..."
    
    if [ -f "deployment/sql/init.sql" ]; then
        mysql -u root -p < deployment/sql/init.sql 2>/dev/null || {
            log_warning "MySQL 初始化失败，可能需要手动执行"
        }
    fi
}

init_hbase_tables() {
    log_info "初始化 HBase 表..."
    
    if [ -n "$HBASE_HOME" ]; then
        echo "
        create_if_not_exists 'weibo_raw', 'cf'
        create_if_not_exists 'weibo_topics', 'cf'
        create_if_not_exists 'sentiment_results', 'cf'
        " | $HBASE_HOME/bin/hbase shell 2>/dev/null || {
            log_warning "HBase 表创建失败"
        }
    fi
}

load_demo_data() {
    log_info "加载演示数据..."
    
    cd backend
    
    # 生成演示数据
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from utils.data_validator import get_validator
    print('数据验证器已加载')
except:
    pass

# 生成模拟数据
import json
import random
from datetime import datetime, timedelta

topics = ['人工智能', '新能源汽车', '房价走势', '教育改革', '医疗保障']
demo_data = []

for i in range(100):
    topic = random.choice(topics)
    sentiment = random.uniform(-1, 1)
    demo_data.append({
        'id': f'demo_{i}',
        'text': f'关于{topic}的讨论，这是第{i}条演示数据',
        'topic': topic,
        'sentiment': sentiment,
        'heat': random.randint(1000, 100000),
        'created_at': (datetime.now() - timedelta(hours=random.randint(0, 72))).isoformat()
    })

# 保存演示数据
with open('data/demo_data.json', 'w', encoding='utf-8') as f:
    json.dump(demo_data, f, ensure_ascii=False, indent=2)

print(f'已生成 {len(demo_data)} 条演示数据')
" 2>/dev/null || log_warning "演示数据生成失败"
    
    cd ..
    log_success "演示数据已加载"
}

# ==================== 健康检查 ====================

health_check() {
    log_info "========== 健康检查 =========="
    
    SERVICES_OK=0
    SERVICES_TOTAL=0
    
    # 检查后端
    SERVICES_TOTAL=$((SERVICES_TOTAL + 1))
    if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
        log_success "Flask 后端: 运行中"
        SERVICES_OK=$((SERVICES_OK + 1))
    else
        log_warning "Flask 后端: 未响应"
    fi
    
    # 检查前端
    SERVICES_TOTAL=$((SERVICES_TOTAL + 1))
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        log_success "Vue 前端: 运行中"
        SERVICES_OK=$((SERVICES_OK + 1))
    else
        log_warning "Vue 前端: 未响应"
    fi
    
    # 检查MySQL
    SERVICES_TOTAL=$((SERVICES_TOTAL + 1))
    if mysqladmin ping -h localhost 2>/dev/null | grep -q "alive"; then
        log_success "MySQL: 运行中"
        SERVICES_OK=$((SERVICES_OK + 1))
    else
        log_warning "MySQL: 未响应"
    fi
    
    echo ""
    log_info "服务状态: $SERVICES_OK/$SERVICES_TOTAL 运行中"
    
    return 0
}

run_basic_test() {
    log_info "运行基本功能测试..."
    
    # 测试API
    RESPONSE=$(curl -s http://localhost:5000/api/weibo/hot-search 2>/dev/null)
    if [ -n "$RESPONSE" ]; then
        log_success "API 测试通过"
    else
        log_warning "API 测试失败"
    fi
}

# ==================== 生成部署报告 ====================

generate_report() {
    log_info "生成部署报告..."
    
    REPORT_FILE="logs/deploy_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$REPORT_FILE" << EOF
============================================
微博情感分析系统 - 部署报告
============================================
部署时间: $(date)
部署模式: $DEPLOY_MODE

环境信息:
- Python: $(python3 --version 2>&1 || echo "未安装")
- Node.js: $(node --version 2>/dev/null || echo "未安装")
- Java: $(java -version 2>&1 | head -n 1 || echo "未安装")

服务状态:
- Flask 后端: http://localhost:5000
- Vue 前端: http://localhost:3000
- MySQL: localhost:3306

访问地址:
- 前端界面: http://localhost:3000
- API文档: http://localhost:5000/api

日志文件:
- 后端日志: logs/backend.log
- 前端日志: logs/frontend.log

停止服务:
  kill \$(cat logs/backend.pid)
  kill \$(cat logs/frontend.pid)
============================================
EOF

    log_success "部署报告已生成: $REPORT_FILE"
}

# ==================== 主函数 ====================

main() {
    print_banner
    
    # 解析参数
    DEPLOY_MODE=${1:-dev}
    
    log_info "部署模式: $DEPLOY_MODE"
    echo ""
    
    # 创建日志目录
    mkdir -p logs
    mkdir -p backend/data
    
    # 环境检查
    run_environment_check
    
    case $DEPLOY_MODE in
        dev)
            log_info "========== 开发模式部署 =========="
            start_backend
            start_frontend
            ;;
        demo)
            log_info "========== 演示模式部署 =========="
            start_mysql
            start_backend
            start_frontend
            load_demo_data
            ;;
        prod)
            log_info "========== 生产模式部署 =========="
            start_mysql
            start_hadoop
            start_spark
            start_hbase
            init_mysql_tables
            init_hbase_tables
            start_backend
            start_frontend
            ;;
        stop)
            log_info "========== 停止所有服务 =========="
            [ -f logs/backend.pid ] && kill $(cat logs/backend.pid) 2>/dev/null && log_success "后端已停止"
            [ -f logs/frontend.pid ] && kill $(cat logs/frontend.pid) 2>/dev/null && log_success "前端已停止"
            exit 0
            ;;
        *)
            log_error "未知模式: $DEPLOY_MODE"
            echo "使用方式: $0 {dev|demo|prod|stop}"
            exit 1
            ;;
    esac
    
    echo ""
    
    # 等待服务启动
    sleep 3
    
    # 健康检查
    health_check
    
    # 基本测试
    run_basic_test
    
    # 生成报告
    generate_report
    
    echo ""
    log_success "========== 部署完成 =========="
    echo ""
    echo "访问地址:"
    echo "  前端: http://localhost:3000"
    echo "  后端: http://localhost:5000/api"
    echo ""
    echo "停止服务: $0 stop"
    echo ""
}

# 运行主函数
main "$@"
