#!/bin/bash
# ====================================================================
# 微博情感分析系统 — Docker Compose 集群监控
# ====================================================================
# 用法: bash deployment/scripts/monitor-cluster.sh
# ====================================================================
set -uo pipefail

echo "=== 容器运行状态 ==="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' --filter 'name=weibo_sentiment'

echo ""
echo "=== 容器资源使用 ==="
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}' $(docker ps -q --filter 'name=weibo_sentiment') 2>/dev/null || echo "  无运行中的容器"

echo ""
echo "=== 容器健康状态 ==="
for c in $(docker ps --format '{{.Names}}' --filter 'name=weibo_sentiment'); do
    health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}N/A{{end}}' "$c" 2>/dev/null)
    printf "  %-40s %s\n" "$c" "$health"
done

echo ""
echo "=== 磁盘 / 内存 ==="
df -h / | tail -1 | awk '{printf "  磁盘: %s / %s (已用 %s)\n", $3, $2, $5}'
free -h | awk '/Mem:/{printf "  内存: %s / %s (可用 %s)\n", $3, $2, $7}'

echo ""
echo "=== Docker 磁盘占用 ==="
docker system df

echo ""
echo "=== 最近错误日志 (每容器最后 5 行) ==="
for c in weibo_sentiment_web weibo_sentiment_java weibo_sentiment_frontend; do
    echo "--- $c ---"
    docker logs --tail 5 "$c" 2>&1 | tail -5
done
