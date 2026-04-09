#!/bin/bash
# ====================================================================
# 微博情感分析系统 - 快速启动脚本 (Linux/macOS)
# ====================================================================

set -e

echo "========================================"
echo "  微博情感分析系统 - 快速启动"
echo "========================================"
echo

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 未安装"
    exit 1
fi

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "[WARNING] .env 文件不存在，正在从模板创建..."
    cp .env.example .env
    echo "[INFO] 请编辑 .env 文件配置数据库等信息"
    read -p "按回车继续..."
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "[INFO] 创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "[INFO] 安装Python依赖..."
pip install -r backend/requirements.txt -q

# 启动后端服务
echo
echo "[INFO] 启动Flask后端服务..."
echo "[INFO] 后端地址: http://localhost:5000"
echo
cd backend
python app.py
