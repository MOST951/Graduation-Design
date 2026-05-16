#!/bin/bash
# ====================================================================
# 微博情感分析系统 — MySQL 数据备份脚本
# ====================================================================
# 用法: bash deployment/scripts/backup-data.sh
# 说明: 通过 Docker exec 进入 MySQL 容器执行 mysqldump, 无需宿主机安装 MySQL 客户端
# ====================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${DEPLOY_DIR}/.env.docker"

# 从 .env.docker 读取配置
get_env() {
    local key="$1" default="$2"
    grep -E "^${key}=" "${ENV_FILE}" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '[:space:]' || echo "${default}"
}

if [[ ! -f "${ENV_FILE}" ]]; then
    echo "错误: ${ENV_FILE} 不存在, 请先创建" >&2
    exit 1
fi

DB_CONTAINER="weibo_sentiment_db"
DB_ROOT_PW=$(get_env "DB_ROOT_PASSWORD" "")
DB_NAME=$(get_env "DB_NAME" "weibo_sentiment")
BACKUP_DIR="${DEPLOY_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup-${DB_NAME}-${TIMESTAMP}.sql.gz"

if [[ -z "${DB_ROOT_PW}" ]]; then
    echo "错误: DB_ROOT_PASSWORD 未配置" >&2
    exit 1
fi

mkdir -p "${BACKUP_DIR}"

echo "[备份] 开始备份数据库 ${DB_NAME} ..."
docker exec "${DB_CONTAINER}" mysqldump \
    -u root -p"${DB_ROOT_PW}" \
    --single-transaction --quick --lock-tables=false \
    "${DB_NAME}" 2>/dev/null | gzip > "${BACKUP_FILE}"

if [[ -s "${BACKUP_FILE}" ]]; then
    SIZE=$(du -h "${BACKUP_FILE}" | awk '{print $1}')
    echo "[备份] 完成: ${BACKUP_FILE} (${SIZE})"

    # 清理 7 天前的备份
    find "${BACKUP_DIR}" -name "backup-${DB_NAME}-*.sql.gz" -mtime +7 -delete 2>/dev/null
    REMAINING=$(ls -1 "${BACKUP_DIR}"/backup-${DB_NAME}-*.sql.gz 2>/dev/null | wc -l)
    echo "[备份] 保留最近 ${REMAINING} 个备份文件"
else
    echo "[备份] 失败: 输出文件为空" >&2
    rm -f "${BACKUP_FILE}"
    exit 1
fi
