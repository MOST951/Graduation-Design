#!/bin/bash
# ====================================================================
# 微博情感分析系统 — 手动构建 Docker 镜像
# ====================================================================
# 用法: 在项目根目录执行 bash deployment/scripts/build-images.sh
# ====================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

echo "=== 构建 Flask 后端镜像 ==="
docker build -t weibo-sentiment/flask-backend:latest -f deployment/docker/Dockerfile .

echo "=== 构建 Java 后端镜像 ==="
docker build -t weibo-sentiment/java-backend:latest -f deployment/docker/Dockerfile.web-backend .

echo "=== 构建前端镜像 ==="
docker build -t weibo-sentiment/frontend:latest -f deployment/docker/Dockerfile.frontend .

echo ""
echo "=== 构建完成 ==="
docker images | grep weibo-sentiment
