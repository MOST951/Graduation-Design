#!/usr/bin/env bash
# ====================================================================
# 微博情感分析系统 — 部署自检脚本
# ====================================================================
# 功能:
#   1. 检查 Docker / Compose 版本
#   2. 检查端口占用
#   3. 检查目录权限
#   4. 检查所有容器运行状态
#   5. 检查 MySQL / Redis 连通性
#   6. 检查 HDFS / HBase 状态
#   7. 自动测试前后端接口连通性
#   8. 输出综合诊断报告
#
# 用法: bash deployment/scripts/health-check.sh
# ====================================================================

set -uo pipefail

# ==================== 颜色 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}✅ PASS${NC}  $*"; }
fail() { echo -e "  ${RED}❌ FAIL${NC}  $*"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
warn() { echo -e "  ${YELLOW}⚠️  WARN${NC}  $*"; WARN_COUNT=$((WARN_COUNT + 1)); }
section() { echo -e "\n${CYAN}${BOLD}══ $* ══${NC}"; }

FAIL_COUNT=0
WARN_COUNT=0

# ==================== 路径 ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEPLOY_DIR="${PROJECT_ROOT}/deployment"
ENV_FILE="${DEPLOY_DIR}/.env.docker"

# 从 .env.docker 读取配置
get_env() {
    local key="$1" default="$2"
    grep -E "^${key}=" "${ENV_FILE}" 2>/dev/null | tail -1 | cut -d= -f2 | tr -d '[:space:]' || echo "${default}"
}

# ==================== 1. 基础环境检查 ====================
section "1. 基础环境检查"

# Docker
if command -v docker &>/dev/null; then
    docker_ver=$(docker --version 2>/dev/null)
    pass "Docker 已安装: ${docker_ver}"
else
    fail "Docker 未安装"
fi

# Docker 守护进程
if docker info &>/dev/null 2>&1; then
    pass "Docker 守护进程运行中"
else
    fail "Docker 守护进程未运行 → sudo systemctl start docker"
fi

# Docker Compose
if docker compose version &>/dev/null; then
    compose_ver=$(docker compose version 2>/dev/null)
    pass "Docker Compose v2: ${compose_ver}"
elif command -v docker-compose &>/dev/null; then
    compose_ver=$(docker-compose --version 2>/dev/null)
    warn "使用 Docker Compose v1: ${compose_ver} (建议升级到 v2)"
else
    fail "Docker Compose 未安装 → sudo apt-get install docker-compose-plugin"
fi

# Docker 用户组
if [[ $EUID -ne 0 ]]; then
    if groups | grep -qw docker; then
        pass "当前用户在 docker 组中"
    else
        fail "当前用户不在 docker 组 → sudo usermod -aG docker \$USER && newgrp docker"
    fi
else
    pass "以 root 用户运行"
fi

# ==================== 2. 配置文件检查 ====================
section "2. 配置文件检查"

if [[ -f "${DEPLOY_DIR}/docker-compose.yml" ]]; then
    pass "docker-compose.yml 存在"
    # 检查是否有 version 字段 (v1 遗留)
    if grep -q "^version:" "${DEPLOY_DIR}/docker-compose.yml"; then
        warn "docker-compose.yml 包含 'version' 字段 (v2 已不需要)"
    fi
else
    fail "docker-compose.yml 缺失"
fi

if [[ -f "${ENV_FILE}" ]]; then
    pass ".env.docker 存在"
    # 检查是否修改了默认密码
    if grep -q "YourStrongPassword123!" "${ENV_FILE}"; then
        warn "DB_PASSWORD 仍为默认值，建议修改！"
    fi
    if grep -q "your-secret-key" "${ENV_FILE}"; then
        warn "SECRET_KEY 仍为默认值，建议修改！"
    fi
else
    fail ".env.docker 不存在 → cp .env.docker.example .env.docker"
fi

if [[ -f "${DEPLOY_DIR}/sql/init.sql" ]]; then
    pass "init.sql 存在"
else
    fail "init.sql 缺失"
fi

# ==================== 3. 端口检查 ====================
section "3. 端口占用检查"

if [[ -f "${ENV_FILE}" ]]; then
    WEB_PORT=$(get_env "WEB_PORT" "5000")
    DB_PORT=$(get_env "DB_PORT" "3306")
    REDIS_PORT=$(get_env "REDIS_PORT" "6379")
    FRONTEND_PORT=$(get_env "FRONTEND_PORT" "3001")
    JAVA_PORT=$(get_env "JAVA_BACKEND_PORT" "8081")
    SPARK_UI_PORT=$(get_env "SPARK_WEBUI_PORT" "8080")
    SPARK_PORT=$(get_env "SPARK_MASTER_PORT" "7077")
else
    WEB_PORT=5000; DB_PORT=3306; REDIS_PORT=6379
    FRONTEND_PORT=3001; JAVA_PORT=8081; SPARK_UI_PORT=8080; SPARK_PORT=7077
fi

check_port() {
    local port=$1 name=$2
    if ss -tlnp 2>/dev/null | grep -q ":${port} "; then
        # 检查是否是自己的容器
        local owner
        owner=$(docker ps --format '{{.Names}}' --filter "publish=${port}" 2>/dev/null | head -1)
        if [[ -n "${owner}" && "${owner}" == weibo_sentiment_* ]]; then
            pass "端口 ${port} (${name}) — 本项目容器 ${owner}"
        else
            warn "端口 ${port} (${name}) 已被占用"
        fi
    else
        pass "端口 ${port} (${name}) 可用"
    fi
}

check_port "${WEB_PORT}" "Flask"
check_port "${DB_PORT}" "MySQL"
check_port "${REDIS_PORT}" "Redis"
check_port "${FRONTEND_PORT}" "Frontend"
check_port "${JAVA_PORT}" "JavaBackend"
check_port "${SPARK_UI_PORT}" "SparkUI"
check_port "${SPARK_PORT}" "SparkMaster"

# 大数据服务端口
ZK_PORT=$(get_env "ZK_PORT" "2181")
HDFS_NN_PORT=$(get_env "HDFS_NAMENODE_PORT" "9000")
HDFS_NN_HTTP=$(get_env "HDFS_NAMENODE_HTTP_PORT" "50070")
HDFS_DN_HTTP=$(get_env "HDFS_DATANODE_HTTP_PORT" "50075")
HBASE_MASTER_PORT=$(get_env "HBASE_MASTER_PORT" "16000")
HBASE_WEBUI_PORT=$(get_env "HBASE_MASTER_WEBUI_PORT" "16010")
HBASE_RS_PORT=$(get_env "HBASE_RS_PORT" "16020")

check_port "${ZK_PORT}" "ZooKeeper"
check_port "${HDFS_NN_PORT}" "HDFS_NameNode"
check_port "${HDFS_NN_HTTP}" "HDFS_WebUI"
check_port "${HDFS_DN_HTTP}" "HDFS_DataNode"
check_port "${HBASE_MASTER_PORT}" "HBase_Master"
check_port "${HBASE_WEBUI_PORT}" "HBase_WebUI"
check_port "${HBASE_RS_PORT}" "HBase_RegionServer"

# ==================== 4. 容器状态检查 ====================
section "4. 容器运行状态"

CONTAINERS=(
    "weibo_sentiment_db:MySQL"
    "weibo_sentiment_redis:Redis"
    "weibo_sentiment_web:Flask"
    "weibo_sentiment_frontend:Frontend"
    "weibo_sentiment_java:JavaBackend"
    "weibo_sentiment_spark_master:SparkMaster"
    "weibo_sentiment_spark_worker:SparkWorker"
    "weibo_sentiment_zookeeper:ZooKeeper"
    "weibo_sentiment_namenode:HDFS_NameNode"
    "weibo_sentiment_datanode:HDFS_DataNode"
    "weibo_sentiment_hbase_master:HBase_Master"
    "weibo_sentiment_hbase_rs:HBase_RegionServer"
)

for item in "${CONTAINERS[@]}"; do
    name="${item%%:*}"
    label="${item##*:}"
    status=$(docker inspect --format='{{.State.Status}}' "${name}" 2>/dev/null || echo "not_found")
    health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}N/A{{end}}' "${name}" 2>/dev/null || echo "N/A")

    if [[ "${status}" == "running" ]]; then
        if [[ "${health}" == "healthy" || "${health}" == "N/A" ]]; then
            pass "${label} (${name}): running [health=${health}]"
        else
            warn "${label} (${name}): running [health=${health}]"
        fi
    elif [[ "${status}" == "not_found" ]]; then
        warn "${label} (${name}): 容器不存在 (profile 未启用或未部署)"
    else
        fail "${label} (${name}): ${status}"
    fi
done

# ==================== 5. 数据库连通性 ====================
section "5. MySQL 连通性"

DB_ROOT_PW=$(get_env "DB_ROOT_PASSWORD" "root")
DB_NAME=$(get_env "DB_NAME" "weibo_sentiment")

if docker exec weibo_sentiment_db mysqladmin ping -h localhost -u root -p"${DB_ROOT_PW}" &>/dev/null 2>&1; then
    pass "MySQL ping 成功"

    # 检查数据库是否存在
    db_exists=$(docker exec weibo_sentiment_db mysql -u root -p"${DB_ROOT_PW}" -e "SHOW DATABASES LIKE '${DB_NAME}';" 2>/dev/null | grep -c "${DB_NAME}" || echo "0")
    if [[ "${db_exists}" -gt 0 ]]; then
        pass "数据库 '${DB_NAME}' 存在"

        # 检查核心表
        table_count=$(docker exec weibo_sentiment_db mysql -u root -p"${DB_ROOT_PW}" -D "${DB_NAME}" -e "SHOW TABLES;" 2>/dev/null | wc -l || echo "0")
        table_count=$((table_count - 1))  # 减去 header 行
        if [[ ${table_count} -gt 0 ]]; then
            pass "数据库包含 ${table_count} 张表"
        else
            warn "数据库为空（0 张表），init.sql 可能未执行"
        fi
    else
        fail "数据库 '${DB_NAME}' 不存在"
    fi
else
    fail "MySQL 连接失败"
fi

# ==================== 6. Redis 连通性 ====================
section "6. Redis 连通性"

if docker exec weibo_sentiment_redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
    pass "Redis PING → PONG"
else
    fail "Redis 连接失败"
fi

# ==================== 6.5 HDFS 状态检查 ====================
section "6.5 HDFS 状态"

NN_CONTAINER="weibo_sentiment_namenode"
nn_running=$(docker inspect --format='{{.State.Status}}' "${NN_CONTAINER}" 2>/dev/null || echo "not_found")
if [[ "${nn_running}" == "running" ]]; then
    # 安全模式
    safemode=$(docker exec "${NN_CONTAINER}" hdfs dfsadmin -safemode get 2>/dev/null || echo "unknown")
    if echo "${safemode}" | grep -q "OFF"; then
        pass "NameNode 安全模式: OFF"
    else
        warn "NameNode 安全模式: ${safemode}"
    fi
    # HDFS 目录
    if docker exec "${NN_CONTAINER}" hdfs dfs -test -d /weibo/raw 2>/dev/null; then
        pass "HDFS 目录 /weibo/raw 存在"
    else
        fail "HDFS 目录 /weibo/raw 不存在"
    fi
    if docker exec "${NN_CONTAINER}" hdfs dfs -test -d /weibo/output 2>/dev/null; then
        pass "HDFS 目录 /weibo/output 存在"
    else
        fail "HDFS 目录 /weibo/output 不存在"
    fi
    # HDFS 容量
    hdfs_report=$(docker exec "${NN_CONTAINER}" hdfs dfsadmin -report 2>/dev/null | head -5)
    if [[ -n "${hdfs_report}" ]]; then
        echo -e "\n  HDFS 报告:"
        echo "${hdfs_report}" | sed 's/^/    /'
    fi
else
    warn "HDFS NameNode 未运行 (with-bigdata profile 未启用?)"
fi

# ==================== 6.6 HBase 状态检查 ====================
section "6.6 HBase 状态"

HB_CONTAINER="weibo_sentiment_hbase_master"
hb_running=$(docker inspect --format='{{.State.Status}}' "${HB_CONTAINER}" 2>/dev/null || echo "not_found")
if [[ "${hb_running}" == "running" ]]; then
    hb_tables=$(docker exec "${HB_CONTAINER}" /opt/hbase/bin/hbase shell <<< "list" 2>/dev/null || echo "error")
    if echo "${hb_tables}" | grep -q "weibo_sentiment"; then
        pass "HBase 表 weibo_sentiment 存在"
    else
        fail "HBase 表 weibo_sentiment 不存在"
    fi
    if echo "${hb_tables}" | grep -q "weibo_raw_index"; then
        pass "HBase 表 weibo_raw_index 存在"
    else
        warn "HBase 表 weibo_raw_index 不存在"
    fi
else
    warn "HBase Master 未运行 (with-bigdata profile 未启用?)"
fi

# ==================== 7. HTTP 接口测试 ====================
section "7. HTTP 接口连通性"

HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
HOST_IP="${HOST_IP:-localhost}"

test_endpoint() {
    local url="$1" name="$2"
    local code
    code=$(curl -sf -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "${url}" 2>/dev/null || echo "000")
    if [[ "${code}" =~ ^(200|301|302|304)$ ]]; then
        pass "${name}: HTTP ${code} (${url})"
    elif [[ "${code}" == "000" ]]; then
        fail "${name}: 连接超时/拒绝 (${url})"
    else
        warn "${name}: HTTP ${code} (${url})"
    fi
}

test_endpoint "http://${HOST_IP}:${WEB_PORT}/api/health" "Flask API"
test_endpoint "http://${HOST_IP}:${FRONTEND_PORT}/" "Frontend"
test_endpoint "http://${HOST_IP}:${JAVA_PORT}/api/actuator/health" "Java Backend"
test_endpoint "http://${HOST_IP}:${SPARK_UI_PORT}/" "Spark Web UI"
test_endpoint "http://${HOST_IP}:${HDFS_NN_HTTP}/dfshealth.html" "HDFS WebUI"
test_endpoint "http://${HOST_IP}:${HBASE_WEBUI_PORT}/master-status" "HBase WebUI"

# ==================== 8. 磁盘和内存 ====================
section "8. 系统资源"

# 磁盘
disk_usage=$(df -h / 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
if [[ -n "${disk_usage}" ]]; then
    if [[ ${disk_usage} -lt 80 ]]; then
        pass "磁盘使用率: ${disk_usage}%"
    elif [[ ${disk_usage} -lt 90 ]]; then
        warn "磁盘使用率: ${disk_usage}% (建议清理)"
    else
        fail "磁盘使用率: ${disk_usage}% (空间不足!)"
    fi
fi

# 内存
mem_total=$(free -m 2>/dev/null | awk '/Mem:/{print $2}')
mem_avail=$(free -m 2>/dev/null | awk '/Mem:/{print $7}')
if [[ -n "${mem_total}" ]]; then
    if [[ ${mem_avail} -gt 512 ]]; then
        pass "可用内存: ${mem_avail}MB / ${mem_total}MB"
    else
        warn "可用内存偏低: ${mem_avail}MB / ${mem_total}MB"
    fi
fi

# Docker 磁盘
docker_disk=$(docker system df 2>/dev/null | head -5)
if [[ -n "${docker_disk}" ]]; then
    echo -e "\n  Docker 磁盘使用:"
    echo "${docker_disk}" | sed 's/^/    /'
fi

# ==================== 汇总 ====================
section "诊断汇总"

echo ""
if [[ ${FAIL_COUNT} -eq 0 && ${WARN_COUNT} -eq 0 ]]; then
    echo -e "  ${GREEN}${BOLD}🎉 全部检查通过！系统运行正常。${NC}"
elif [[ ${FAIL_COUNT} -eq 0 ]]; then
    echo -e "  ${YELLOW}${BOLD}⚠️  ${WARN_COUNT} 个警告，0 个错误。系统基本正常。${NC}"
else
    echo -e "  ${RED}${BOLD}❌ ${FAIL_COUNT} 个错误，${WARN_COUNT} 个警告。请根据上方提示修复。${NC}"
fi
echo ""
echo "  日志文件: ${PROJECT_ROOT}/logs/cluster-*.log"
echo "  容器日志: docker compose logs --tail=50"
echo ""
