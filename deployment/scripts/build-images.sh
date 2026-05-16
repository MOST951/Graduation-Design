#!/bin/bash
# ====================================================================
# 微博情感分析系统 — 手动构建 Docker 镜像
# ====================================================================
# 用法: bash deployment/scripts/build-images.sh [web|java-backend|frontend|all]
# 说明: 镜像 tag 与 docker-compose.yml 中 build 自动生成的名称一致
# ====================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${DEPLOY_DIR}/.env.docker"

TARGET="${1:-all}"

build_service() {
    local svc="$1"
    echo "=== 构建 ${svc} 镜像 ==="
    cd "${DEPLOY_DIR}"
    if [[ -f "${ENV_FILE}" ]]; then
        docker compose --env-file "${ENV_FILE}" build "${svc}"
    else
        docker compose build "${svc}"
    fi
}

case "${TARGET}" in
    web)          build_service web ;;
    java|java-backend) build_service java-backend ;;
    frontend)     build_service frontend ;;
    all)
        build_service web
        build_service java-backend
        build_service frontend
        ;;
    *)
        echo "用法: $0 [web|java-backend|frontend|all]" >&2
        exit 1
        ;;
esac

echo ""
echo "=== 构建完成 ==="
docker images | grep deployment
