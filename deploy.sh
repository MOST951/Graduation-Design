#!/usr/bin/env bash
# ====================================================================
# 微博舆情情感分析系统 — 一键部署脚本 (Ubuntu 24.04)
# ====================================================================
# 用法:
#   ./deploy.sh              # 一键部署 (首次自动构建镜像)
#   ./deploy.sh stop         # 停止所有服务 (数据保留)
#   ./deploy.sh start        # 启动已部署的服务
#   ./deploy.sh restart      # 重启所有服务
#   ./deploy.sh status       # 查看服务状态
#   ./deploy.sh logs         # 查看实时日志
#   ./deploy.sh down         # 销毁容器 (数据卷保留)
#   ./deploy.sh health       # 健康检查
#   ./deploy.sh clean        # 彻底清理 (容器+数据卷+镜像)
# ====================================================================

set -euo pipefail

# ==================== 颜色 ====================
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; }
step()  { echo -e "${CYAN}[▶]${NC} $*"; }

# ==================== 路径 ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="${SCRIPT_DIR}/deployment"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"
ENV_FILE="${DEPLOY_DIR}/.env.docker"
ENV_EXAMPLE="${DEPLOY_DIR}/.env.docker.example"

# ==================== 前置检查 ====================
preflight() {
    echo ""
    echo -e "${BOLD}=====================================================${NC}"
    echo -e "${BOLD}  微博舆情情感分析系统 — Docker 一键部署${NC}"
    echo -e "${BOLD}  适配: Ubuntu 24.04 / Docker Compose v2${NC}"
    echo -e "${BOLD}=====================================================${NC}"
    echo ""

    # Docker
    if ! command -v docker &>/dev/null; then
        error "Docker 未安装"
        echo "  安装命令: curl -fsSL https://get.docker.com | bash"
        echo "  然后:     sudo systemctl enable docker && sudo systemctl start docker"
        echo "  加组:     sudo usermod -aG docker \$USER && newgrp docker"
        exit 1
    fi

    if ! docker info &>/dev/null 2>&1; then
        error "Docker 守护进程未运行"
        echo "  启动: sudo systemctl start docker"
        exit 1
    fi

    # Docker Compose
    if docker compose version &>/dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        error "Docker Compose 未安装"
        echo "  安装: sudo apt-get install -y docker-compose-plugin"
        exit 1
    fi

    # 非 root 用户需在 docker 组
    if [[ $EUID -ne 0 ]] && ! groups | grep -qw docker; then
        error "当前用户不在 docker 组"
        echo "  修复: sudo usermod -aG docker \$USER && newgrp docker"
        exit 1
    fi

    info "Docker 就绪: $(docker --version | head -1)"
}

# ==================== 环境变量文件 ====================
ensure_env() {
    if [[ ! -f "${ENV_FILE}" ]]; then
        if [[ ! -f "${ENV_EXAMPLE}" ]]; then
            error "缺少模板 ${ENV_EXAMPLE}"
            exit 1
        fi
        step "从模板创建 .env.docker ..."
        cp "${ENV_EXAMPLE}" "${ENV_FILE}"

        # 自动生成随机密钥
        if command -v python3 &>/dev/null; then
            local sk jk
            sk=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "auto-$(date +%s)-key")
            jk=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "auto-$(date +%s)-jwt")
            sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${sk}|" "${ENV_FILE}"
            sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${jk}|" "${ENV_FILE}"
            info "已自动生成 SECRET_KEY / JWT_SECRET"
        fi
        info "已创建 ${ENV_FILE}"
        warn "默认密码为 123456，生产环境请务必修改！"
    else
        info ".env.docker 已存在"
    fi
}

# ==================== 修复 Windows 换行符 ====================
fix_line_endings() {
    if command -v dos2unix &>/dev/null; then
        find "${SCRIPT_DIR}" -maxdepth 1 -name "*.sh" -exec dos2unix -q {} \; 2>/dev/null
        find "${DEPLOY_DIR}" -name "*.sh" -exec dos2unix -q {} \; 2>/dev/null
        find "${DEPLOY_DIR}" -name "*.yml" -exec dos2unix -q {} \; 2>/dev/null
        find "${DEPLOY_DIR}" -name "*.conf" -exec dos2unix -q {} \; 2>/dev/null
        find "${DEPLOY_DIR}" -name "*.xml" -exec dos2unix -q {} \; 2>/dev/null
        find "${DEPLOY_DIR}" -name ".env*" -exec dos2unix -q {} \; 2>/dev/null
    else
        # 无 dos2unix 时用 sed 替代
        find "${SCRIPT_DIR}" -maxdepth 1 -name "*.sh" -exec sed -i 's/\r$//' {} \; 2>/dev/null
        find "${DEPLOY_DIR}" \( -name "*.sh" -o -name "*.yml" -o -name "*.conf" -o -name "*.xml" -o -name ".env*" \) \
            -exec sed -i 's/\r$//' {} \; 2>/dev/null
    fi
}

# ==================== 构建 Compose 命令 ====================
build_compose_cmd() {
    # 从 .env.docker 读取启用的 profiles
    local profiles_str
    profiles_str=$(grep -E "^ENABLED_PROFILES=" "${ENV_FILE}" 2>/dev/null | tail -1 | cut -d= -f2 | tr -d '[:space:]')
    profiles_str="${profiles_str:-with-frontend,with-java-backend,with-spark,with-bigdata}"

    COMPOSE_PROFILES=""
    IFS=',' read -ra _profiles <<< "${profiles_str}"
    for p in "${_profiles[@]}"; do
        COMPOSE_PROFILES+=" --profile ${p}"
    done

    COMPOSE_FULL="${COMPOSE_CMD} -f ${COMPOSE_FILE} --env-file ${ENV_FILE}${COMPOSE_PROFILES}"
    info "Profiles: ${profiles_str}"
}

# ==================== 获取本机 IP ====================
get_ip() {
    hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost"
}

# ==================== 等待核心服务就绪 ====================
wait_ready() {
    step "等待核心服务就绪 (最多 120s) ..."
    local waited=0

    # 等待 MySQL
    while [[ ${waited} -lt 90 ]]; do
        if docker exec weibo_sentiment_db mysqladmin ping -h localhost \
            -u root -p"$(grep '^DB_ROOT_PASSWORD=' "${ENV_FILE}" | cut -d= -f2)" &>/dev/null 2>&1; then
            info "MySQL 就绪"
            break
        fi
        echo -ne "  等待 MySQL ... [${waited}s]\r"
        sleep 3
        waited=$((waited + 3))
    done

    # 等待 Flask
    local flask_waited=0
    while [[ ${flask_waited} -lt 60 ]]; do
        if curl -sf http://127.0.0.1:5000/ &>/dev/null; then
            info "Flask API 就绪"
            break
        fi
        sleep 3
        flask_waited=$((flask_waited + 3))
    done
    echo ""
}

# ==================== 显示访问地址 ====================
show_urls() {
    local ip
    ip=$(get_ip)
    local fp=$(grep '^FRONTEND_PORT=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2)
    local wp=$(grep '^WEB_PORT=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2)
    local jp=$(grep '^JAVA_BACKEND_PORT=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2)
    local sp=$(grep '^SPARK_WEBUI_PORT=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2)

    echo ""
    echo -e "${BOLD}===================== 访问地址 =====================${NC}"
    echo "  前端页面:      http://${ip}:${fp:-3001}"
    echo "  Flask API:     http://${ip}:${wp:-5000}/api/v2/health"
    echo "  Java API:      http://${ip}:${jp:-8081}/api/actuator/health"
    echo "  Spark WebUI:   http://${ip}:${sp:-8080}"
    echo -e "${BOLD}====================================================${NC}"
    echo ""
    echo "  管理命令:"
    echo "    ./deploy.sh status    查看状态"
    echo "    ./deploy.sh logs      实时日志"
    echo "    ./deploy.sh health    健康检查"
    echo "    ./deploy.sh stop      停止服务"
    echo "    ./deploy.sh restart   重启服务"
    echo ""
}

# ==================== 核心操作 ====================

do_deploy() {
    step "修复文件换行符 ..."
    fix_line_endings

    # 检查端口冲突
    step "检查端口占用 ..."
    local ports=(5000 3306 6379 3001 8081)
    local conflict=false
    for port in "${ports[@]}"; do
        local pid_on_port
        pid_on_port=$(ss -tlnp 2>/dev/null | grep ":${port} " | head -1 || true)
        if [[ -n "${pid_on_port}" ]]; then
            # 忽略自己的容器
            local own=$(docker ps --format '{{.Names}}' --filter "publish=${port}" 2>/dev/null | head -1)
            if [[ -z "${own}" || "${own}" != weibo_sentiment_* ]]; then
                warn "端口 ${port} 被占用: ${pid_on_port}"
                conflict=true
            fi
        fi
    done
    if [[ "${conflict}" == "true" ]]; then
        warn "发现端口冲突，可在 deployment/.env.docker 中修改端口"
        read -r -p "继续部署? (y/N) " ans
        [[ "${ans}" != "y" && "${ans}" != "Y" ]] && exit 1
    else
        info "所有基础端口可用"
    fi

    step "构建并启动所有服务 (首次构建需要 5-15 分钟) ..."
    echo ""
    # shellcheck disable=SC2086
    ${COMPOSE_FULL} up -d --build 2>&1

    echo ""
    wait_ready
    show_urls
    info "部署完成！"
}

do_start() {
    step "启动已有服务 ..."
    # shellcheck disable=SC2086
    ${COMPOSE_FULL} start 2>&1
    echo ""
    wait_ready
    show_urls
    info "服务已启动"
}

do_stop() {
    step "停止所有服务 (数据保留) ..."
    # shellcheck disable=SC2086
    ${COMPOSE_FULL} stop 2>&1
    echo ""
    info "服务已停止。数据卷已保留，运行 ./deploy.sh start 可恢复。"
}

do_restart() {
    do_stop
    echo ""
    step "等待 3 秒 ..."
    sleep 3
    do_start
}

do_status() {
    echo ""
    # shellcheck disable=SC2086
    ${COMPOSE_FULL} ps
    echo ""
    step "数据卷:"
    docker volume ls --filter name=weibo_sentiment 2>/dev/null
    echo ""
}

do_logs() {
    # shellcheck disable=SC2086
    ${COMPOSE_FULL} logs --tail=100 -f
}

do_down() {
    warn "即将销毁所有容器 (数据卷保留) ..."
    # shellcheck disable=SC2086
    ${COMPOSE_FULL} down 2>&1
    echo ""
    info "容器已销毁。数据卷保留。"
    echo "  彻底清理: ./deploy.sh clean"
}

do_health() {
    echo ""
    step "服务健康检查:"
    echo ""

    local ip=$(get_ip)

    # 容器状态
    local -a containers=(
        "weibo_sentiment_db:MySQL"
        "weibo_sentiment_redis:Redis"
        "weibo_sentiment_web:Flask"
        "weibo_sentiment_frontend:Frontend"
        "weibo_sentiment_java:Java"
    )
    for item in "${containers[@]}"; do
        local name="${item%%:*}" label="${item##*:}"
        local st=$(docker inspect --format='{{.State.Status}}' "${name}" 2>/dev/null || echo "missing")
        if [[ "${st}" == "running" ]]; then
            echo -e "  ${GREEN}●${NC} ${label}: running"
        elif [[ "${st}" == "missing" ]]; then
            echo -e "  ${YELLOW}○${NC} ${label}: 未部署"
        else
            echo -e "  ${RED}●${NC} ${label}: ${st}"
        fi
    done
    echo ""

    # HTTP 接口
    step "接口连通性:"
    local wp=$(grep '^WEB_PORT=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2)
    local fp=$(grep '^FRONTEND_PORT=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2)
    local jp=$(grep '^JAVA_BACKEND_PORT=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2)

    local -a endpoints=(
        "http://127.0.0.1:${wp:-5000}/api/v2/health:Flask_API"
        "http://127.0.0.1:${fp:-3001}/:Frontend"
        "http://127.0.0.1:${jp:-8081}/api/actuator/health:Java_API"
    )
    for ep in "${endpoints[@]}"; do
        local url="${ep%:*}" ename="${ep##*:}"
        local code=$(curl -sf -o /dev/null -w "%{http_code}" --connect-timeout 5 "${url}" 2>/dev/null || echo "000")
        if [[ "${code}" =~ ^(200|301|302)$ ]]; then
            echo -e "  ${GREEN}●${NC} ${ename}: HTTP ${code}"
        else
            echo -e "  ${RED}●${NC} ${ename}: HTTP ${code}"
        fi
    done
    echo ""

    # MySQL
    step "MySQL:"
    local db_pw=$(grep '^DB_ROOT_PASSWORD=' "${ENV_FILE}" | cut -d= -f2)
    if docker exec weibo_sentiment_db mysqladmin ping -h localhost -u root -p"${db_pw}" &>/dev/null 2>&1; then
        echo -e "  ${GREEN}●${NC} 连接正常"
    else
        echo -e "  ${RED}●${NC} 连接失败"
    fi
    echo ""
}

do_clean() {
    warn "即将彻底清理所有容器、数据卷和本项目镜像！"
    read -r -p "确定? 这将删除所有数据！(输入 YES 确认) " ans
    if [[ "${ans}" != "YES" ]]; then
        echo "取消。"
        exit 0
    fi
    # shellcheck disable=SC2086
    ${COMPOSE_FULL} down -v --rmi local 2>&1
    echo ""
    info "已彻底清理。"
}

# ==================== 主入口 ====================
main() {
    local action="${1:-deploy}"

    export LANG=C.UTF-8
    export LC_ALL=C.UTF-8

    preflight
    ensure_env
    build_compose_cmd

    case "${action}" in
        deploy|up|"")   do_deploy ;;
        start)          do_start ;;
        stop)           do_stop ;;
        restart)        do_restart ;;
        status|ps)      do_status ;;
        logs)           do_logs ;;
        down|destroy)   do_down ;;
        health|check)   do_health ;;
        clean|purge)    do_clean ;;
        *)
            echo "用法: $0 [deploy|start|stop|restart|status|logs|down|health|clean]"
            echo ""
            echo "  deploy     一键部署 (默认，首次自动构建镜像)"
            echo "  start      启动已部署的服务"
            echo "  stop       停止服务 (数据保留)"
            echo "  restart    重启服务"
            echo "  status     查看服务状态"
            echo "  logs       查看实时日志"
            echo "  down       销毁容器 (数据卷保留)"
            echo "  health     健康检查"
            echo "  clean      彻底清理 (容器+卷+镜像)"
            exit 1
            ;;
    esac
}

main "$@"
