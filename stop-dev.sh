#!/bin/bash
# ====================================================================
# 微博情感分析系统 - Ubuntu 本地开发停止脚本
# ====================================================================
# 使用方法: chmod +x stop-dev.sh && ./stop-dev.sh
# 功能:
#   1. 读取 .dev-pids 文件中记录的 PID 并终止
#   2. 兜底: 按端口清理残留进程
#   3. 释放端口 3001 / 5000 / 8081
# ====================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="${PROJECT_ROOT}/.dev-pids"

echo ""
echo "======================================================"
echo "  微博情感分析系统 - 停止本地开发服务"
echo "======================================================"
echo ""

# ==================== 阶段1: 通过PID文件停止 ====================
if [ -f "${PID_FILE}" ]; then
    echo -e "${YELLOW}[1/3] 读取 PID 文件停止进程...${NC}"
    while IFS='=' read -r svc_name svc_pid; do
        if [ -n "${svc_pid}" ] && kill -0 "${svc_pid}" 2>/dev/null; then
            echo -e "  停止 ${svc_name} (PID: ${svc_pid})..."
            kill "${svc_pid}" 2>/dev/null || true
            # 等待最多5秒优雅退出
            for i in $(seq 1 10); do
                if ! kill -0 "${svc_pid}" 2>/dev/null; then
                    break
                fi
                sleep 0.5
            done
            # 如果仍在运行，强制终止
            if kill -0 "${svc_pid}" 2>/dev/null; then
                kill -9 "${svc_pid}" 2>/dev/null || true
            fi
            echo -e "  ${GREEN}[OK] ${svc_name} 已停止${NC}"
        else
            echo -e "  ${YELLOW}[SKIP] ${svc_name} (PID: ${svc_pid}) 已不存在${NC}"
        fi
    done < "${PID_FILE}"
    rm -f "${PID_FILE}"
    echo ""
else
    echo -e "${YELLOW}[1/3] 未找到 PID 文件，跳过...${NC}"
    echo ""
fi

# ==================== 阶段2: 按端口清理残留进程 ====================
echo -e "${YELLOW}[2/3] 检查端口残留进程...${NC}"

kill_port() {
    local port=$1
    local name=$2
    local pids
    pids=$(lsof -ti ":${port}" 2>/dev/null || ss -tlnp 2>/dev/null | grep ":${port} " | grep -oP 'pid=\K[0-9]+' || true)
    if [ -n "${pids}" ]; then
        echo -e "  释放端口 ${port} (${name})..."
        for pid in ${pids}; do
            kill "${pid}" 2>/dev/null || true
        done
        sleep 1
        for pid in ${pids}; do
            if kill -0 "${pid}" 2>/dev/null; then
                kill -9 "${pid}" 2>/dev/null || true
            fi
        done
        echo -e "  ${GREEN}[OK] 端口 ${port} 已释放${NC}"
    else
        echo -e "  ${GREEN}[OK] 端口 ${port} (${name}) 无残留${NC}"
    fi
}

kill_port 3001 "Frontend"
kill_port 5000 "Flask"
kill_port 8081 "Java"
echo ""

# ==================== 阶段3: 确认所有服务已停止 ====================
echo -e "${YELLOW}[3/3] 最终确认...${NC}"

all_clear=true
for port in 3001 5000 8081; do
    if ss -tlnp 2>/dev/null | grep -q ":${port} "; then
        echo -e "  ${RED}[WARN] 端口 ${port} 仍被占用${NC}"
        all_clear=false
    fi
done

if [ "${all_clear}" = true ]; then
    echo -e "  ${GREEN}所有端口已释放${NC}"
fi

echo ""
echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}  所有开发服务已停止${NC}"
echo -e "${GREEN}======================================================${NC}"
echo ""
echo -e "  端口 3001 / 5000 / 8081 已释放"
echo -e "  重新启动: ./start-dev.sh"
echo -e "  仅重启Spark: ./start-dev.sh --restart-spark"
echo ""
