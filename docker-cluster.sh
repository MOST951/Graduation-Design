#!/usr/bin/env bash
# ====================================================================
# 微博舆情情感分析系统 — Docker 集群启停脚本 (Ubuntu 20.04 / 1Panel)
# ====================================================================
# 用法:
#   ./docker-cluster.sh              # 启动集群（首次部署 / 后续仅启动）
#   ./docker-cluster.sh stop         # 停止集群（保留数据）
#   ./docker-cluster.sh restart      # 重启集群
#   ./docker-cluster.sh status       # 查看状态
#   ./docker-cluster.sh logs         # 实时日志
#   ./docker-cluster.sh down         # 销毁容器（数据卷保留）
#   ./docker-cluster.sh health       # 健康自检
#
# 适配: Ubuntu 20.04 + Docker Compose v2 + 1Panel
# ====================================================================

set -uo pipefail

# ==================== 颜色与符号 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}✅ $*${NC}"; log "INFO" "$*"; }
warn()  { echo -e "${YELLOW}⚠️  $*${NC}"; log "WARN" "$*"; }
error() { echo -e "${RED}❌ $*${NC}"; log "ERROR" "$*"; }
step()  { echo -e "${CYAN}▶  $*${NC}"; log "STEP" "$*"; }

# ==================== 路径解析 ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="${SCRIPT_DIR}/deployment"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"
ENV_FILE="${DEPLOY_DIR}/.env.docker"
ENV_EXAMPLE="${DEPLOY_DIR}/.env.docker.example"
LOG_DIR="${SCRIPT_DIR}/logs"
LOG_FILE="${LOG_DIR}/cluster-$(date +%Y%m%d).log"

# Compose 参数 (启动时从 .env 动态构建, 见 init_compose_base)
PROFILES=""
COMPOSE_BASE=""

# 标记容器（判断是否首次部署）
SENTINEL_CONTAINER="weibo_sentiment_db"

# 最大重试次数
MAX_RETRY=3

# 需要检测的端口列表 (端口:服务名) — 包含大数据服务端口
REQUIRED_PORTS="5000:Flask 3306:MySQL 6379:Redis 3001:Frontend 8081:JavaBackend 8080:SparkUI 7077:SparkMaster 2181:ZooKeeper 9000:HDFS_NameNode 50070:HDFS_WebUI 50075:HDFS_DataNode 16000:HBase_Master 16010:HBase_WebUI 16020:HBase_RS 16030:HBase_RS_WebUI"

# ==================== 日志函数 ====================
log() {
    local level="$1"; shift
    mkdir -p "${LOG_DIR}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] $*" >> "${LOG_FILE}" 2>/dev/null || true
}

# ==================== 环境检查 ====================

# 检查 Docker 权限（Ubuntu 下非 root 用户需在 docker 组）
check_docker_permission() {
    if [[ $EUID -ne 0 ]]; then
        if ! groups | grep -qw docker; then
            error "当前用户不在 docker 组中，无法执行 Docker 命令"
            echo "  修复方法:"
            echo "    sudo usermod -aG docker \$USER"
            echo "    newgrp docker  # 或重新登录"
            exit 1
        fi
    fi
}

# 自动检测 docker compose 命令
detect_compose_cmd() {
    if docker compose version &>/dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        error "未找到 docker compose，请先安装 Docker Compose v2"
        echo "  Ubuntu 安装: sudo apt-get install docker-compose-plugin"
        echo "  1Panel 环境通常已自带，请检查 Docker 服务是否正常"
        exit 1
    fi
}

# 完整 Docker 环境检查
check_docker() {
    step "检查 Docker 环境..."

    if ! command -v docker &>/dev/null; then
        error "未检测到 Docker，请先安装"
        echo "  Ubuntu:  curl -fsSL https://get.docker.com | bash"
        echo "  1Panel:  在应用商店安装 Docker"
        exit 1
    fi

    if ! docker info &>/dev/null 2>&1; then
        error "Docker 守护进程未运行"
        echo "  启动: sudo systemctl start docker"
        echo "  开机自启: sudo systemctl enable docker"
        exit 1
    fi

    check_docker_permission
    detect_compose_cmd

    local docker_ver compose_ver
    docker_ver=$(docker --version 2>/dev/null | head -1)
    compose_ver=$(${COMPOSE_CMD} version 2>/dev/null | head -1)
    info "Docker 就绪: ${docker_ver}"
    info "Compose 就绪: ${compose_ver}"
}

# 检查端口占用
check_ports() {
    step "检查端口占用..."
    local has_conflict=false

    # 从 .env.docker 读取实际端口
    local web_port frontend_port java_port db_port redis_port spark_ui_port spark_port
    web_port=$(get_env_val "WEB_PORT" "5000")
    frontend_port=$(get_env_val "FRONTEND_PORT" "3001")
    java_port=$(get_env_val "JAVA_BACKEND_PORT" "8081")
    db_port=$(get_env_val "DB_PORT" "3306")
    redis_port=$(get_env_val "REDIS_PORT" "6379")
    spark_ui_port=$(get_env_val "SPARK_WEBUI_PORT" "8080")
    spark_port=$(get_env_val "SPARK_MASTER_PORT" "7077")

    # 大数据服务端口
    local zk_port hdfs_nn_port hdfs_nn_http hdfs_dn_http hbase_master hbase_webui hbase_rs hbase_rs_webui
    zk_port=$(get_env_val "ZK_PORT" "2181")
    hdfs_nn_port=$(get_env_val "HDFS_NAMENODE_PORT" "9000")
    hdfs_nn_http=$(get_env_val "HDFS_NAMENODE_HTTP_PORT" "50070")
    hdfs_dn_http=$(get_env_val "HDFS_DATANODE_HTTP_PORT" "50075")
    hbase_master=$(get_env_val "HBASE_MASTER_PORT" "16000")
    hbase_webui=$(get_env_val "HBASE_MASTER_WEBUI_PORT" "16010")
    hbase_rs=$(get_env_val "HBASE_RS_PORT" "16020")
    hbase_rs_webui=$(get_env_val "HBASE_RS_WEBUI_PORT" "16030")

    local port_list="${web_port}:Flask ${db_port}:MySQL ${redis_port}:Redis ${frontend_port}:Frontend ${java_port}:JavaBackend ${spark_ui_port}:SparkUI ${spark_port}:SparkMaster ${zk_port}:ZooKeeper ${hdfs_nn_port}:HDFS_NameNode ${hdfs_nn_http}:HDFS_WebUI ${hdfs_dn_http}:HDFS_DataNode ${hbase_master}:HBase_Master ${hbase_webui}:HBase_WebUI ${hbase_rs}:HBase_RS ${hbase_rs_webui}:HBase_RS_WebUI"

    for item in ${port_list}; do
        local port="${item%%:*}"
        local name="${item##*:}"
        if ss -tlnp 2>/dev/null | grep -qE ":${port}\b" || \
           netstat -tlnp 2>/dev/null | grep -qE ":${port}\b"; then
            # 检查是否是我们自己的容器占用
            local container_using
            container_using=$(docker ps --format '{{.Names}}' --filter "publish=${port}" 2>/dev/null | head -1)
            if [[ -n "${container_using}" && "${container_using}" == weibo_sentiment_* ]]; then
                continue  # 是自己的容器，跳过
            fi
            warn "端口 ${port} (${name}) 已被占用！"
            echo "    查看占用: ss -tlnp | grep :${port}"
            echo "    可在 .env.docker 中修改 ${name} 端口"
            has_conflict=true
        fi
    done

    if [[ "${has_conflict}" == "true" ]]; then
        warn "发现端口冲突，请修改 ${ENV_FILE} 中的端口配置后重试"
        echo ""
        read -r -p "是否仍然继续? (y/N) " confirm
        if [[ "${confirm}" != "y" && "${confirm}" != "Y" ]]; then
            exit 1
        fi
    else
        info "所有端口可用"
    fi
}

# 检查目录权限
check_directory_permissions() {
    step "检查目录权限..."

    local dirs=("${LOG_DIR}" "${DEPLOY_DIR}")
    for dir in "${dirs[@]}"; do
        if [[ ! -d "${dir}" ]]; then
            mkdir -p "${dir}" 2>/dev/null || {
                warn "无法创建目录 ${dir}，尝试 sudo..."
                sudo mkdir -p "${dir}" && sudo chmod 755 "${dir}"
            }
        fi
        if [[ ! -w "${dir}" ]]; then
            warn "目录 ${dir} 无写入权限，尝试修复..."
            sudo chmod 755 "${dir}" 2>/dev/null || true
        fi
    done
    info "目录权限检查完成"
}

# ==================== 环境配置文件 ====================

check_env_file() {
    if [[ ! -f "${ENV_FILE}" ]]; then
        if [[ ! -f "${ENV_EXAMPLE}" ]]; then
            error "未找到 ${ENV_EXAMPLE}，无法生成环境配置"
            exit 1
        fi
        warn ".env.docker 不存在，正在从模板复制..."
        cp "${ENV_EXAMPLE}" "${ENV_FILE}"
        # 自动生成强随机密钥
        if command -v python3 &>/dev/null; then
            local secret_key jwt_secret
            secret_key=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "change-me-$(date +%s)")
            jwt_secret=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "jwt-change-me-$(date +%s)")
            sed -i "s|SECRET_KEY=.*|SECRET_KEY=${secret_key}|" "${ENV_FILE}"
            sed -i "s|JWT_SECRET=.*|JWT_SECRET=${jwt_secret}|" "${ENV_FILE}"
            info "已自动生成 SECRET_KEY 和 JWT_SECRET"
        fi
        info "已创建 ${ENV_FILE}"
        warn "⚡ 请务必修改 DB_PASSWORD 和 DB_ROOT_PASSWORD！"
        echo ""
    fi
}

check_compose_file() {
    if [[ ! -f "${COMPOSE_FILE}" ]]; then
        error "未找到 ${COMPOSE_FILE}"
        error "请确认脚本位于项目根目录"
        exit 1
    fi
}

# ==================== 工具函数 ====================

# 从 .env.docker 读取配置值
get_env_val() {
    local key="$1" default="$2"
    local val
    val=$(grep -E "^${key}=" "${ENV_FILE}" 2>/dev/null | tail -1 | cut -d= -f2 | tr -d '[:space:]')
    echo "${val:-${default}}"
}

# 判断集群是否已部署
cluster_exists() {
    docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${SENTINEL_CONTAINER}$"
}

# 执行 compose 命令
run_compose() {
    # shellcheck disable=SC2086
    ${COMPOSE_CMD} ${COMPOSE_BASE} "$@"
}

# 获取本机 IP (用于显示访问地址)
get_host_ip() {
    local ip
    ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [[ -z "${ip}" ]]; then
        ip=$(ip -4 addr show scope global 2>/dev/null | grep inet | head -1 | awk '{print $2}' | cut -d/ -f1)
    fi
    echo "${ip:-localhost}"
}

# 初始化 Compose 参数 (从 .env 动态读取启用的 profiles)
init_compose_base() {
    local enabled_profiles
    enabled_profiles=$(grep -E "^ENABLED_PROFILES=" "${ENV_FILE}" 2>/dev/null | tail -1 | cut -d= -f2 | tr -d '[:space:]')
    if [[ -z "${enabled_profiles}" ]]; then
        enabled_profiles="with-frontend,with-java-backend,with-spark,with-bigdata"
    fi
    PROFILES=""
    local profile_list
    IFS=',' read -ra profile_list <<< "${enabled_profiles}"
    for p in "${profile_list[@]}"; do
        PROFILES+=" --profile ${p}"
    done
    COMPOSE_BASE="-f ${COMPOSE_FILE} --env-file ${ENV_FILE}${PROFILES}"
    info "启用 Profiles:${PROFILES}"
}

# ==================== 镜像拉取 (国内网络增强) ====================

# 代理源候选 (根据响应速度动态排序)
MIRROR_CANDIDATES=(
    "docker.1panel.live"
    "hub.rat.dev"
    "docker.anyhub.us.kg"
    "dockerpull.org"
)

# 所需镜像列表 (Compose & Dockerfile 基础镜像)
REQUIRED_IMAGES=(
    "bitnami/spark:3.5"
    "harisekhon/hbase:2.4"
    "apache/hadoop:3.3.6"
    "zookeeper:3.8"
    "mysql:8.0"
    "redis:7-alpine"
    "maven:3.8-openjdk-11-slim"
    "eclipse-temurin:11-jre-jammy"
    "python:3.9-slim"
    "node:16-alpine"
    "nginx:alpine"
)

# 镜像拉取超时时间 (秒)
IMAGE_PULL_TIMEOUT=120

# 镜像源测速结果
declare -a MIRROR_PRIORITY=()

# 特殊镜像备用方案 (space 分隔的候选列表)
# 注意: Fallback 镜像必须与原镜像功能完全一致 (如: JDK 不可降级为 JRE)
declare -A IMAGE_FALLBACKS=(
    ["bitnami/spark:3.5"]="apache/spark:3.5 bitnamilegacy/spark:3.5"
)

# 测试镜像源可用性并记录耗时 (秒)
test_mirror() {
    local mirror="$1"
    local proto
    for proto in https http; do
        local url="${proto}://${mirror}/v2/"
        local result
        result=$(curl -s -o /dev/null -w "%{http_code} %{time_total}" --connect-timeout 2 --max-time 4 "${url}" 2>/dev/null) || continue
        local code="${result%% *}"
        local timing="${result##* }"
        if [[ "${code}" =~ ^(200|301|302|401)$ ]]; then
            printf '%s' "${timing}"
            return 0
        fi
    done
    return 1
}

# 根据测速结果生成镜像源优先级
prepare_mirror_priority() {
    MIRROR_PRIORITY=()
    local scored=()
    for mirror in "${MIRROR_CANDIDATES[@]}"; do
        local latency
        latency=$(test_mirror "${mirror}" 2>/dev/null) || continue
        scored+=("${latency}:${mirror}")
    done

    if [[ ${#scored[@]} -gt 0 ]]; then
        IFS=$'\n' scored=($(printf '%s\n' "${scored[@]}" | sort -n))
        unset IFS
        for entry in "${scored[@]}"; do
            MIRROR_PRIORITY+=("${entry#*:}")
        done
        info "镜像源测速成功: $(printf '%s ' "${MIRROR_PRIORITY[@]}")"
    else
        warn "镜像源测速全部失败，将直接尝试 Docker Hub"
    fi
}

# 根据镜像名称生成代理路径
get_proxy_path() {
    local image="$1"
    if [[ "${image}" != */* ]]; then
        echo "library/${image}"
    else
        echo "${image}"
    fi
}

# 尝试使用指定来源拉取镜像
try_pull_with_source() {
    local source="$1"      # DIRECT 或镜像域名
    local src_image="$2"   # 镜像真实名称 (可能是备用)
    local target_image="$3" # 目标标签

    local remote_image label status
    if [[ "${source}" == "DIRECT" ]]; then
        remote_image="${src_image}"
        label="直连 Docker Hub"
    else
        remote_image="${source}/$(get_proxy_path "${src_image}")"
        label="代理 ${source}"
    fi

    echo -ne "    ⤷ ${target_image} ... ${label} ... "
    if timeout "${IMAGE_PULL_TIMEOUT}" docker pull "${remote_image}" >/dev/null 2>&1; then
        if [[ "${remote_image}" != "${target_image}" ]]; then
            docker tag "${remote_image}" "${target_image}" >/dev/null 2>&1 || true
            docker rmi "${remote_image}" >/dev/null 2>&1 || true
        fi
        echo -e "${GREEN}OK${NC}"
        return 0
    fi

    status=$?
    if [[ ${status} -eq 124 ]]; then
        echo -e "${RED}超时${NC}"
        return 124
    fi
    echo -e "${YELLOW}失败${NC}"
    return 1
}

# 从当前可用来源列表尝试拉取镜像
pull_from_sources() {
    local source_image="$1"
    local target_image="${2:-$1}"
    local note="${3:-}"

    [[ -n "${note}" ]] && echo -e "    ↺ ${note}"

    local sources=("DIRECT")
    if [[ ${#MIRROR_PRIORITY[@]} -gt 0 ]]; then
        sources+=("${MIRROR_PRIORITY[@]}")
    fi

    local src rc
    for src in "${sources[@]}"; do
        try_pull_with_source "${src}" "${source_image}" "${target_image}"
        rc=$?
        if [[ ${rc} -eq 0 ]]; then
            return 0
        elif [[ ${rc} -eq 124 ]]; then
            # 超时说明网络不通, 不再尝试后续代理源
            return 1
        fi
    done
    return 1
}

# 拉取单个镜像（含备用方案）
pull_image() {
    local image="$1"

    if docker image inspect "${image}" >/dev/null 2>&1; then
        echo -e "    ${GREEN}✔${NC} ${image} (本地已存在)"
        return 0
    fi

    if pull_from_sources "${image}" "${image}"; then
        return 0
    fi

    local fallback_images=""
    if [[ -v IMAGE_FALLBACKS["${image}"] ]]; then
        fallback_images="${IMAGE_FALLBACKS["${image}"]}"
    fi
    if [[ -n "${fallback_images}" ]]; then
        local alt
        for alt in ${fallback_images}; do
            if pull_from_sources "${alt}" "${image}" "尝试备用镜像 ${alt}"; then
                echo -e "    ${GREEN}✔${NC} ${image} 已通过备用镜像 ${alt} 获取"
                return 0
            fi
        done
    fi

    echo -e "    ${RED}✘${NC} ${image} 所有来源均失败"
    echo "      建议:"
    echo "        - 配置 /etc/docker/daemon.json 添加国内加速器, 例如:"
    echo "          {\"registry-mirrors\": [\"https://docker.m.daocloud.io\", \"https://mirror.ccs.tencentyun.com\"]}"
    echo "        - 或手动执行: docker pull ${image}"
    if [[ -n "${fallback_images}" ]]; then
        echo "        - 备用手动命令:"
        local alt
        for alt in ${fallback_images}; do
            echo "            docker pull ${alt} && docker tag ${alt} ${image}"
        done
    fi
    return 1
}

# 批量预拉取所有所需镜像 (并行拉取 + 失败重试)
ensure_images() {
    step "检查并拉取所需 Docker 镜像..."
    prepare_mirror_priority
    echo ""

    local total=${#REQUIRED_IMAGES[@]}
    local -a images_to_pull=()

    # 阶段 1: 检查本地已存在的镜像
    for image in "${REQUIRED_IMAGES[@]}"; do
        if docker image inspect "${image}" >/dev/null 2>&1; then
            echo -e "    ${GREEN}✔${NC} ${image} (本地已存在)"
        else
            images_to_pull+=("${image}")
        fi
    done

    if [[ ${#images_to_pull[@]} -eq 0 ]]; then
        echo ""
        info "所有 ${total} 个镜像就绪"
        return 0
    fi

    # 阶段 2: 并行拉取缺失镜像
    local pull_tmp
    pull_tmp=$(mktemp -d /tmp/docker-pull-XXXXXX)
    local -a pids=()
    local idx=0

    step "并行拉取 ${#images_to_pull[@]} 个缺失镜像..."
    for image in "${images_to_pull[@]}"; do
        idx=$((idx + 1))
        (
            if pull_image "${image}" > "${pull_tmp}/${idx}.log" 2>&1; then
                echo "0" > "${pull_tmp}/${idx}.rc"
            else
                echo "1" > "${pull_tmp}/${idx}.rc"
                echo "${image}" > "${pull_tmp}/${idx}.failed"
            fi
        ) &
        pids+=($!)
        echo "  ⤴ [${idx}/${#images_to_pull[@]}] 已提交: ${image}"
    done

    # 等待所有后台任务完成
    step "等待所有镜像拉取完成..."
    for pid in "${pids[@]}"; do
        wait "${pid}" 2>/dev/null || true
    done

    # 阶段 3: 汇总结果
    local -a failed_images=()
    idx=0
    for image in "${images_to_pull[@]}"; do
        idx=$((idx + 1))
        local rc_file="${pull_tmp}/${idx}.rc"
        local log_file="${pull_tmp}/${idx}.log"
        if [[ -f "${rc_file}" ]] && [[ "$(cat "${rc_file}")" == "0" ]]; then
            echo -e "  ${GREEN}✅${NC} ${image} 拉取完成"
        else
            echo -e "  ${RED}✘${NC} ${image} 拉取失败"
            [[ -f "${log_file}" ]] && sed 's/^/    /' "${log_file}"
            failed_images+=("${image}")
        fi
    done

    # 阶段 4: 对失败镜像进行串行重试
    if [[ ${#failed_images[@]} -gt 0 ]]; then
        echo ""
        warn "以下 ${#failed_images[@]} 个镜像拉取失败，尝试串行重试..."
        local -a still_failed=()
        for image in "${failed_images[@]}"; do
            echo -e "📦 重试拉取: ${image}"
            if pull_image "${image}"; then
                echo -e "  ${GREEN}✅${NC} ${image} 重试成功"
            else
                still_failed+=("${image}")
            fi
        done

        if [[ ${#still_failed[@]} -gt 0 ]]; then
            rm -rf "${pull_tmp}"
            echo ""
            error "以下镜像拉取失败: ${still_failed[*]}"
            echo "  请配置国内镜像加速器或手动拉取后重试:"
            echo "    ./docker-cluster.sh"
            exit 1
        fi
    fi

    rm -rf "${pull_tmp}"
    echo ""
    info "所有 ${total} 个镜像就绪"
}

# ==================== 核心操作 ====================

# 首次部署 (带重试)
do_first_deploy() {
    echo ""
    info "检测到首次运行，正在部署完整集群 (Spark + HDFS + HBase + 前后端)，这可能需要几分钟..."
    echo ""

    # 预拉取所有镜像 (自动国内代理回退)
    ensure_images

    local attempt=0
    while [[ ${attempt} -lt ${MAX_RETRY} ]]; do
        attempt=$((attempt + 1))
        step "[${attempt}/${MAX_RETRY}] 构建并启动服务..."

        if run_compose up -d 2>&1 | tee -a "${LOG_FILE}"; then
            echo ""
            info "首次部署完成！"
            wait_for_healthy
            show_access_info
            return 0
        else
            warn "部署尝试 ${attempt}/${MAX_RETRY} 失败"
            if [[ ${attempt} -lt ${MAX_RETRY} ]]; then
                step "等待 10 秒后重试..."
                sleep 10
            fi
        fi
    done

    error "部署在 ${MAX_RETRY} 次尝试后仍然失败，请检查日志:"
    echo "  日志文件: ${LOG_FILE}"
    echo "  容器日志: ${COMPOSE_CMD} ${COMPOSE_BASE} logs"
    echo "  手动拉镜像: docker pull docker.1panel.live/<镜像名>"
    exit 1
}

# 启动已有容器 (带重试)
do_start_existing() {
    echo ""
    info "检测到已有集群服务，正在启动已有容器，所有历史数据将完整保留..."
    echo ""

    local attempt=0
    while [[ ${attempt} -lt ${MAX_RETRY} ]]; do
        attempt=$((attempt + 1))
        if run_compose start 2>&1 | tee -a "${LOG_FILE}"; then
            echo ""
            info "集群已启动！所有数据（MySQL / Redis）完整保留。"
            wait_for_healthy
            show_access_info
            return 0
        else
            warn "启动尝试 ${attempt}/${MAX_RETRY} 失败"
            if [[ ${attempt} -lt ${MAX_RETRY} ]]; then
                sleep 5
            fi
        fi
    done

    error "启动在 ${MAX_RETRY} 次尝试后失败"
    exit 1
}

# 等待核心服务就绪 (应用层检测)
wait_for_healthy() {
    step "等待核心服务就绪 (最多 180 秒)..."
    local max_wait=180
    local waited=0

    # 阶段 1: 等待 MySQL (应用层: mysqladmin ping + SELECT 1)
    while [[ ${waited} -lt 60 ]]; do
        if docker exec "${SENTINEL_CONTAINER}" mysqladmin ping -h localhost \
            -u root -p"$(get_env_val DB_ROOT_PASSWORD 'root')" &>/dev/null && \
           docker exec "${SENTINEL_CONTAINER}" mysql -u root \
            -p"$(get_env_val DB_ROOT_PASSWORD 'root')" -e "SELECT 1" &>/dev/null; then
            info "MySQL 服务就绪 (应用层验证通过)"
            break
        fi
        local db_status
        db_status=$(docker inspect --format='{{.State.Health.Status}}' "${SENTINEL_CONTAINER}" 2>/dev/null || echo "unknown")
        echo -ne "  [${waited}s] 等待 MySQL... (${db_status})\r"
        sleep 5
        waited=$((waited + 5))
    done

    # 阶段 2: 等待 HDFS NameNode (应用层: 安全模式检测)
    local nn_container="weibo_sentiment_namenode"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "${nn_container}"; then
        step "等待 HDFS NameNode 就绪..."
        while [[ ${waited} -lt ${max_wait} ]]; do
            if timeout 10 docker exec "${nn_container}" hdfs dfsadmin -safemode get 2>/dev/null | grep -q "OFF"; then
                info "HDFS NameNode 就绪 (安全模式已关闭)"
                break
            fi
            local nn_status
            nn_status=$(docker inspect --format='{{.State.Health.Status}}' "${nn_container}" 2>/dev/null || echo "unknown")
            echo -ne "  [${waited}s] 等待 HDFS NameNode... (${nn_status})\r"
            sleep 5
            waited=$((waited + 5))
        done
    fi

    # 阶段 3: 等待 HBase Master (应用层: ZooKeeper 连通 + hbase status)
    local hb_container="weibo_sentiment_hbase_master"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "${hb_container}"; then
        step "等待 HBase Master 就绪..."
        while [[ ${waited} -lt ${max_wait} ]]; do
            if timeout 15 docker exec "${hb_container}" /opt/hbase/bin/hbase shell <<< "status" 2>/dev/null | grep -q "servers"; then
                info "HBase Master 就绪 (应用层验证通过)"
                break
            fi
            local hb_status
            hb_status=$(docker inspect --format='{{.State.Health.Status}}' "${hb_container}" 2>/dev/null || echo "unknown")
            echo -ne "  [${waited}s] 等待 HBase Master... (${hb_status})\r"
            sleep 5
            waited=$((waited + 5))
        done
    fi

    echo ""
    if [[ ${waited} -ge ${max_wait} ]]; then
        warn "部分服务可能还未完全就绪，请用 './docker-cluster.sh status' 查看"
    fi
}

# 停止
do_stop() {
    echo ""
    info "正在停止所有集群服务，数据已持久化保存，下次启动可直接恢复..."
    echo ""
    run_compose stop 2>&1 | tee -a "${LOG_FILE}"
    echo ""
    info "所有服务已停止。"
    echo "  数据卷已保留:"
    echo "    - weibo_sentiment_mysql_data    (MySQL 数据)"
    echo "    - weibo_sentiment_redis_data    (Redis 数据)"
    echo "    - weibo_sentiment_hdfs_namenode (HDFS NameNode 元数据)"
    echo "    - weibo_sentiment_hdfs_datanode (HDFS DataNode 数据块)"
    echo "    - weibo_sentiment_hbase_data    (HBase 数据)"
    echo "    - weibo_sentiment_zk_data       (ZooKeeper 数据)"
    echo "    - weibo_sentiment_app_logs      (应用日志)"
    echo "    - weibo_sentiment_model_cache   (模型缓存)"
    echo ""
    echo "  再次运行 ./docker-cluster.sh 即可恢复全部服务和数据。"
}

# 状态
do_status() {
    echo ""
    step "集群容器状态:"
    echo ""
    run_compose ps
    echo ""
    step "数据卷:"
    docker volume ls --filter name=weibo_sentiment 2>/dev/null || true
    echo ""
}

# 日志
do_logs() {
    run_compose logs --tail=100 -f
}

# 销毁容器
do_down() {
    echo ""
    warn "即将销毁所有容器（数据卷将保留）..."
    echo ""
    run_compose down 2>&1 | tee -a "${LOG_FILE}"
    echo ""
    info "容器已销毁。命名数据卷已保留，如需彻底清理:"
    echo "    docker volume rm weibo_sentiment_mysql_data weibo_sentiment_redis_data \\"
    echo "      weibo_sentiment_hdfs_namenode weibo_sentiment_hdfs_datanode \\"
    echo "      weibo_sentiment_hbase_data weibo_sentiment_zk_data weibo_sentiment_zk_datalog \\"
    echo "      weibo_sentiment_app_logs weibo_sentiment_model_cache"
}

# 健康检查
do_health() {
    echo ""
    step "执行服务健康检查..."
    echo ""

    local host_ip
    host_ip=$(get_host_ip)
    local web_port frontend_port java_port spark_port
    web_port=$(get_env_val "WEB_PORT" "5000")
    frontend_port=$(get_env_val "FRONTEND_PORT" "3001")
    java_port=$(get_env_val "JAVA_BACKEND_PORT" "8081")
    spark_port=$(get_env_val "SPARK_WEBUI_PORT" "8080")
    local hdfs_http_port hbase_webui_port
    hdfs_http_port=$(get_env_val "HDFS_NAMENODE_HTTP_PORT" "50070")
    hbase_webui_port=$(get_env_val "HBASE_MASTER_WEBUI_PORT" "16010")
    local all_ok=true

    # 检查容器运行状态
    step "容器运行状态:"
    local -a containers=(
        weibo_sentiment_web weibo_sentiment_db weibo_sentiment_redis
        weibo_sentiment_frontend weibo_sentiment_java
        weibo_sentiment_spark_master weibo_sentiment_spark_worker
        weibo_sentiment_zookeeper weibo_sentiment_namenode weibo_sentiment_datanode
        weibo_sentiment_hbase_master weibo_sentiment_hbase_rs
    )
    for c in "${containers[@]}"; do
        local status
        status=$(docker inspect --format='{{.State.Status}}' "${c}" 2>/dev/null || echo "missing")
        if [[ "${status}" == "running" ]]; then
            echo -e "    ${GREEN}●${NC} ${c}: running"
        elif [[ "${status}" == "missing" ]]; then
            echo -e "    ${YELLOW}○${NC} ${c}: not deployed"
        else
            echo -e "    ${RED}●${NC} ${c}: ${status}"
            all_ok=false
        fi
    done
    echo ""

    # 检查 HTTP 接口
    step "接口连通性:"
    local endpoints=(
        "http://${host_ip}:${web_port}/api/v2/health:Flask_API"
        "http://${host_ip}:${frontend_port}/:Frontend"
        "http://${host_ip}:${java_port}/api/actuator/health:Java_API"
        "http://${host_ip}:${spark_port}/:Spark_WebUI"
        "http://${host_ip}:${hdfs_http_port}/dfshealth.html:HDFS_WebUI"
        "http://${host_ip}:${hbase_webui_port}/master-status:HBase_WebUI"
    )
    for ep in "${endpoints[@]}"; do
        local url="${ep%%:*}:${ep#*:}"
        url="${url%:*}"
        local name="${ep##*:}"
        local http_code
        http_code=$(curl -sf -o /dev/null -w "%{http_code}" --connect-timeout 5 "${url}" 2>/dev/null || echo "000")
        if [[ "${http_code}" =~ ^(200|301|302)$ ]]; then
            echo -e "    ${GREEN}●${NC} ${name}: HTTP ${http_code}"
        else
            echo -e "    ${RED}●${NC} ${name}: HTTP ${http_code} (${url})"
            all_ok=false
        fi
    done
    echo ""

    # 检查 MySQL 连通性
    step "MySQL 连通性:"
    if docker exec "${SENTINEL_CONTAINER}" mysqladmin ping -h localhost -u root -p"$(get_env_val DB_ROOT_PASSWORD 'root')" &>/dev/null; then
        echo -e "    ${GREEN}●${NC} MySQL: 连接正常"
    else
        echo -e "    ${RED}●${NC} MySQL: 连接失败"
        all_ok=false
    fi
    echo ""

    # 检查 HDFS 状态
    local nn_container="weibo_sentiment_namenode"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "${nn_container}"; then
        step "HDFS 状态:"
        # 检查 NameNode 安全模式 (超时保护)
        local safemode
        safemode=$(timeout 10 docker exec "${nn_container}" hdfs dfsadmin -safemode get 2>/dev/null || echo "unknown")
        if echo "${safemode}" | grep -q "OFF"; then
            echo -e "    ${GREEN}●${NC} NameNode: 安全模式已关闭"
        else
            echo -e "    ${YELLOW}●${NC} NameNode: ${safemode}"
        fi
        # 检查 HDFS 项目目录 (超时标记为 UNKNOWN 而非 FAIL)
        local hdfs_raw_rc=0
        timeout 10 docker exec "${nn_container}" hdfs dfs -test -d /weibo/raw 2>/dev/null || hdfs_raw_rc=$?
        if [[ ${hdfs_raw_rc} -eq 0 ]]; then
            echo -e "    ${GREEN}●${NC} HDFS 目录 /weibo/raw: 存在"
        elif [[ ${hdfs_raw_rc} -eq 124 ]]; then
            echo -e "    ${YELLOW}●${NC} HDFS 目录 /weibo/raw: 检测超时 (UNKNOWN)"
        else
            echo -e "    ${RED}●${NC} HDFS 目录 /weibo/raw: 不存在"
            all_ok=false
        fi
        local hdfs_output_rc=0
        timeout 10 docker exec "${nn_container}" hdfs dfs -test -d /weibo/output 2>/dev/null || hdfs_output_rc=$?
        if [[ ${hdfs_output_rc} -eq 0 ]]; then
            echo -e "    ${GREEN}●${NC} HDFS 目录 /weibo/output: 存在"
        elif [[ ${hdfs_output_rc} -eq 124 ]]; then
            echo -e "    ${YELLOW}●${NC} HDFS 目录 /weibo/output: 检测超时 (UNKNOWN)"
        else
            echo -e "    ${RED}●${NC} HDFS 目录 /weibo/output: 不存在"
            all_ok=false
        fi
        echo ""
    fi

    # 检查 HBase 状态 (通过 Web UI，避免 hbase shell JVM 启动慢)
    local hb_container="weibo_sentiment_hbase_master"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "${hb_container}"; then
        step "HBase 状态:"
        local hb_page
        hb_page=$(timeout 10 docker exec "${hb_container}" wget -q -O - http://localhost:16010/tablesDetailed.jsp 2>/dev/null || echo "")
        if echo "${hb_page}" | grep -q "weibo_sentiment"; then
            echo -e "    ${GREEN}●${NC} HBase 表 weibo_sentiment: 存在"
        else
            echo -e "    ${RED}●${NC} HBase 表 weibo_sentiment: 未找到"
            all_ok=false
        fi
        # RegionServer 数量 (从 master-status 页面检测)
        local rs_page
        rs_page=$(timeout 10 docker exec "${hb_container}" wget -q -O - http://localhost:16010/master-status 2>/dev/null || echo "")
        local rs_count
        rs_count=$(echo "${rs_page}" | grep -c "regionserver" || echo "0")
        if [[ ${rs_count} -gt 0 ]]; then
            echo -e "    ${GREEN}●${NC} RegionServer: 已注册"
        else
            echo -e "    ${YELLOW}●${NC} RegionServer: 未检测到"
        fi
        echo ""
    fi

    if [[ "${all_ok}" == "true" ]]; then
        info "所有服务运行正常！"
    else
        warn "部分服务异常，请检查日志: ./docker-cluster.sh logs"
    fi
}

# 显示访问地址
show_access_info() {
    local host_ip
    host_ip=$(get_host_ip)
    local web_port frontend_port java_port spark_ui_port
    web_port=$(get_env_val "WEB_PORT" "5000")
    frontend_port=$(get_env_val "FRONTEND_PORT" "3001")
    java_port=$(get_env_val "JAVA_BACKEND_PORT" "8081")
    spark_ui_port=$(get_env_val "SPARK_WEBUI_PORT" "8080")
    local hdfs_http_port hbase_webui_port
    hdfs_http_port=$(get_env_val "HDFS_NAMENODE_HTTP_PORT" "50070")
    hbase_webui_port=$(get_env_val "HBASE_MASTER_WEBUI_PORT" "16010")

    echo ""
    echo "=========================================="
    echo "  服务访问地址 (本机 IP: ${host_ip})"
    echo "=========================================="
    echo "  前端页面          http://${host_ip}:${frontend_port}"
    echo "  Flask API        http://${host_ip}:${web_port}"
    echo "  Java  API        http://${host_ip}:${java_port}"
    echo "  Spark Web UI     http://${host_ip}:${spark_ui_port}"
    echo "  HDFS  Web UI     http://${host_ip}:${hdfs_http_port}"
    echo "  HBase Web UI     http://${host_ip}:${hbase_webui_port}"
    echo "=========================================="
    echo "  管理命令:"
    echo "    ./docker-cluster.sh status   查看状态"
    echo "    ./docker-cluster.sh logs     查看日志"
    echo "    ./docker-cluster.sh health   健康检查"
    echo "    ./docker-cluster.sh stop     停止集群"
    echo "=========================================="
    echo ""
}

# ==================== 主入口 ====================

main() {
    local action="${1:-start}"

    # 确保 UTF-8 编码
    export LANG=C.UTF-8
    export LC_ALL=C.UTF-8

    echo ""
    echo "======================================================"
    echo "   微博舆情情感分析系统 — Docker 集群管理"
    echo "   适配: Ubuntu 20.04 / Docker Compose v2 / 1Panel"
    echo "======================================================"
    echo ""

    # 前置检查
    check_docker
    check_compose_file
    check_directory_permissions
    check_env_file
    init_compose_base

    # 清理 7 天前的旧日志
    find "${LOG_DIR}" -name "*.log" -mtime +7 -delete 2>/dev/null || true

    case "${action}" in
        start|up|"")
            check_ports
            if cluster_exists; then
                do_start_existing
            else
                do_first_deploy
            fi
            ;;
        stop)
            do_stop
            ;;
        status|ps)
            do_status
            ;;
        logs)
            do_logs
            ;;
        down|destroy)
            do_down
            ;;
        restart)
            do_stop
            echo ""
            step "等待 5 秒后重新启动..."
            sleep 5
            if cluster_exists; then
                do_start_existing
            else
                do_first_deploy
            fi
            ;;
        health|check)
            do_health
            ;;
        *)
            echo "用法: $0 [start|stop|status|logs|down|restart|health]"
            echo ""
            echo "  start    启动集群（默认，首次自动部署，后续仅启动已有容器）"
            echo "  stop     停止集群（保留所有数据）"
            echo "  restart  重启集群"
            echo "  status   查看集群状态"
            echo "  logs     查看实时日志"
            echo "  down     销毁容器（数据卷保留）"
            echo "  health   服务健康检查"
            exit 1
            ;;
    esac
}

main "$@"
