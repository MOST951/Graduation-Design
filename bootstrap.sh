#!/usr/bin/env bash
# ====================================================================
# 微博舆情情感分析系统 — Ubuntu 首次环境引导脚本
# ====================================================================
# 用途: 从一台全新的 Ubuntu 主机, 一键完成:
#   1. 安装基础工具 (git/curl/dos2unix/python3)
#   2. 安装 Docker + Compose v2
#   3. 拉取本项目源码
#   4. 从 HuggingFace 下载已微调模型 (~410 MB)
#   5. 修复换行符 + 赋予脚本执行权限
#   6. 调用 docker-cluster.sh 开始部署
#
# 用法:
#   # 方式 1: 直接从 GitHub 运行 (推荐, 什么都不用下载)
#   curl -fsSL https://raw.githubusercontent.com/MOST951/Graduation-Design/master/bootstrap.sh | bash
#
#   # 方式 2: 先克隆再运行
#   git clone https://github.com/MOST951/Graduation-Design.git
#   cd Graduation-Design && ./bootstrap.sh
#
#   # 方式 3: 只做环境准备, 不自动部署
#   ./bootstrap.sh --no-deploy
#
# 适配: Ubuntu 20.04 / 22.04 / 24.04
# ====================================================================

set -euo pipefail

# ==================== 颜色 ====================
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; }
step()  { echo -e "${CYAN}[▶]${NC} $*"; }

# ==================== 配置 ====================
REPO_URL="https://github.com/MOST951/Graduation-Design.git"
REPO_DIR_NAME="weibo-analysis"
HF_MODEL_ID="senlou/weibo-sentiment-chinese-bert"
HF_MIRROR="${HF_ENDPOINT:-}"  # 用户可通过环境变量 HF_ENDPOINT 自定义镜像

# 参数解析
AUTO_DEPLOY=true
for arg in "$@"; do
    case "$arg" in
        --no-deploy)     AUTO_DEPLOY=false ;;
        --help|-h)
            grep -E '^# (用途|用法|方式|适配)' "$0" | sed 's/^# //'
            exit 0
            ;;
    esac
done

banner() {
    echo ""
    echo -e "${BOLD}============================================================${NC}"
    echo -e "${BOLD}  微博舆情情感分析系统 — Ubuntu 一键环境引导${NC}"
    echo -e "${BOLD}  GitHub:      ${REPO_URL}${NC}"
    echo -e "${BOLD}  HF Model:    https://huggingface.co/${HF_MODEL_ID}${NC}"
    echo -e "${BOLD}============================================================${NC}"
    echo ""
}

# ==================== 前置检查 ====================

check_os() {
    step "检查操作系统 ..."
    if [[ ! -f /etc/os-release ]]; then
        error "无法识别操作系统, 此脚本仅支持 Ubuntu/Debian"
        exit 1
    fi
    . /etc/os-release
    if [[ "${ID}" != "ubuntu" && "${ID_LIKE:-}" != *"debian"* && "${ID}" != "debian" ]]; then
        warn "当前系统: ${PRETTY_NAME:-unknown}, 此脚本为 Ubuntu/Debian 设计, 可能不兼容"
        read -r -p "继续吗? (y/N) " ans
        [[ "${ans}" != "y" && "${ans}" != "Y" ]] && exit 1
    fi
    info "OS: ${PRETTY_NAME:-${ID} ${VERSION_ID:-}}"
}

check_sudo() {
    if [[ $EUID -eq 0 ]]; then
        SUDO=""
        info "当前以 root 运行"
    elif sudo -n true 2>/dev/null; then
        SUDO="sudo"
        info "sudo 可用 (免密)"
    elif command -v sudo &>/dev/null; then
        SUDO="sudo"
        warn "sudo 会要求输入密码"
    else
        error "需要 root 权限或 sudo 命令, 但都不可用"
        exit 1
    fi
}

# ==================== 步骤实现 ====================

install_basic_tools() {
    step "[1/6] 安装基础工具 (git curl wget dos2unix python3 python3-pip) ..."
    ${SUDO} apt-get update -qq
    ${SUDO} DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        git curl wget dos2unix python3 python3-pip ca-certificates 2>&1 | \
        grep -Ev "^(Selecting|Preparing|Unpacking|Setting up|Processing)" || true
    info "基础工具就绪"
}

install_docker() {
    step "[2/6] 安装 Docker + Compose v2 ..."
    if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
        info "Docker 已安装: $(docker --version | head -1)"
    else
        info "下载 Docker 官方安装脚本 ..."
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
        ${SUDO} bash /tmp/get-docker.sh
        rm -f /tmp/get-docker.sh
        ${SUDO} systemctl enable --now docker
    fi

    # 确认 compose v2 可用
    if ! docker compose version &>/dev/null 2>&1; then
        warn "Docker Compose v2 插件未找到, 尝试安装 ..."
        ${SUDO} apt-get install -y -qq docker-compose-plugin 2>/dev/null || true
    fi

    # 当前用户加入 docker 组
    if [[ -n "${SUDO}" ]] && ! groups | grep -qw docker; then
        ${SUDO} usermod -aG docker "$USER"
        warn "已将 ${USER} 加入 docker 组, 本次会话需要 newgrp docker 或重新登录生效"
        NEED_NEWGRP=true
    fi

    info "Docker: $(docker --version 2>/dev/null | head -1)"
    info "Compose: $(docker compose version 2>/dev/null | head -1 || echo 'v1 (docker-compose)')"
}

clone_repo() {
    step "[3/6] 拉取项目源码 ..."

    # 如果当前目录已经是项目根目录 (有 deploy.sh), 直接复用
    if [[ -f "./docker-cluster.sh" && -f "./deployment/docker-compose.yml" ]]; then
        PROJECT_DIR="$(pwd)"
        info "检测到当前目录已是项目根目录: ${PROJECT_DIR}"
        return 0
    fi

    # 否则克隆到 ~/weibo-analysis
    PROJECT_DIR="${HOME}/${REPO_DIR_NAME}"
    if [[ -d "${PROJECT_DIR}/.git" ]]; then
        info "项目目录已存在, 执行 git pull ..."
        (cd "${PROJECT_DIR}" && git pull --ff-only 2>&1 | tail -3) || warn "git pull 失败, 使用现有代码"
    else
        info "克隆到 ${PROJECT_DIR} ..."
        git clone --depth=1 "${REPO_URL}" "${PROJECT_DIR}"
    fi
    info "项目目录: ${PROJECT_DIR}"
}

download_model() {
    step "[4/6] 下载已微调 ChineseBERT 模型 (~410 MB) ..."

    local model_dir="${PROJECT_DIR}/backend-python/models/chinese-bert-wwm-ext"

    # 已存在且完整则跳过
    if [[ -f "${model_dir}/model.safetensors" && -f "${model_dir}/config.json" ]]; then
        local size
        size=$(stat -c%s "${model_dir}/model.safetensors" 2>/dev/null || echo 0)
        if [[ ${size} -gt 400000000 ]]; then
            info "模型已存在且完整 ($(numfmt --to=iec ${size})), 跳过下载"
            return 0
        fi
    fi

    # 安装 huggingface_hub
    if ! command -v huggingface-cli &>/dev/null; then
        info "安装 huggingface_hub ..."
        pip3 install --break-system-packages --quiet huggingface_hub 2>/dev/null || \
        pip3 install --user --quiet huggingface_hub
    fi

    # 国内加速 (用户可通过 HF_ENDPOINT 环境变量自定义)
    if [[ -z "${HF_MIRROR}" ]]; then
        info "使用 HuggingFace 官方源 (如需国内镜像, 设置 HF_ENDPOINT=https://hf-mirror.com)"
    else
        export HF_ENDPOINT="${HF_MIRROR}"
        info "使用镜像: ${HF_MIRROR}"
    fi

    mkdir -p "${model_dir}"

    # 重试下载 (网络不稳定场景)
    local attempt=0
    while [[ ${attempt} -lt 3 ]]; do
        attempt=$((attempt + 1))
        info "下载尝试 ${attempt}/3 ..."
        if huggingface-cli download "${HF_MODEL_ID}" \
             --local-dir "${model_dir}" \
             --local-dir-use-symlinks False 2>&1 | tail -5; then
            info "模型下载完成"
            return 0
        fi
        warn "下载失败, 10 秒后重试 ..."
        sleep 10
    done

    error "模型下载失败 3 次, 请手动执行:"
    echo "  huggingface-cli download ${HF_MODEL_ID} \\"
    echo "      --local-dir ${model_dir}"
    echo "  或使用国内镜像: export HF_ENDPOINT=https://hf-mirror.com"
    exit 1
}

fix_permissions() {
    step "[5/6] 修复换行符与脚本权限 ..."
    cd "${PROJECT_DIR}"

    # 修复所有 shell 脚本的 Windows 换行符
    find . -name "*.sh" -not -path "./node_modules/*" -not -path "./*/node_modules/*" \
        -exec dos2unix -q {} \; 2>/dev/null || true

    # 确保关键脚本可执行
    chmod +x docker-cluster.sh bootstrap.sh 2>/dev/null || true
    find deployment/scripts -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true

    info "脚本权限就绪"
}

run_deploy() {
    step "[6/6] 调用 docker-cluster.sh 开始部署 ..."
    cd "${PROJECT_DIR}"

    if [[ -n "${NEED_NEWGRP:-}" ]]; then
        warn "本次会话 docker 组权限未生效, 使用 sudo 运行 deploy"
        ${SUDO} bash ./docker-cluster.sh
    else
        ./docker-cluster.sh
    fi
}

show_summary() {
    local ip
    ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    ip="${ip:-localhost}"

    echo ""
    echo -e "${BOLD}============================================================${NC}"
    echo -e "${GREEN}${BOLD}  ✅ 环境准备完成!${NC}"
    echo -e "${BOLD}============================================================${NC}"
    echo ""
    echo "  项目目录: ${PROJECT_DIR}"
    echo ""
    echo "  常用命令:"
    echo "    cd ${PROJECT_DIR}"
    echo "    ./docker-cluster.sh              # 启动集群 (首次自动构建镜像)"
    echo "    ./docker-cluster.sh stop         # 停止所有服务"
    echo "    ./docker-cluster.sh start        # 启动已部署的服务"
    echo "    ./docker-cluster.sh restart      # 重启"
    echo "    ./docker-cluster.sh status       # 查看状态"
    echo "    ./docker-cluster.sh logs         # 实时日志"
    echo "    ./docker-cluster.sh health       # 健康检查"
    echo ""

    if [[ "${AUTO_DEPLOY}" == "false" ]]; then
        echo -e "${YELLOW}  当前已跳过自动部署 (--no-deploy), 请手动运行:${NC}"
        echo "    cd ${PROJECT_DIR} && ./docker-cluster.sh"
    else
        echo "  部署完成后访问:"
        echo "    前端:    http://${ip}:3001"
        echo "    Flask:   http://${ip}:5000/api/v2/health"
        echo "    Java:    http://${ip}:8081/actuator/health"
        echo "    Spark:   http://${ip}:8080"
    fi

    if [[ -n "${NEED_NEWGRP:-}" ]]; then
        echo ""
        warn "⚠️  当前用户刚加入 docker 组, 为避免后续使用 sudo, 请执行:"
        echo "    newgrp docker     # 或重新登录"
    fi
    echo ""
}

# ==================== 主流程 ====================
main() {
    banner
    check_os
    check_sudo

    install_basic_tools
    install_docker
    clone_repo
    download_model
    fix_permissions

    if [[ "${AUTO_DEPLOY}" == "true" ]]; then
        run_deploy
    fi

    show_summary
}

main "$@"
