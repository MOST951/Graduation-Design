#!/bin/bash
# ====================================================================
# HDFS NameNode 启动入口脚本
# - 首次启动: 自动格式化 HDFS + 创建项目目录
# - 后续启动: 跳过格式化, 保留数据
# ====================================================================
set -e

FORMATTED_FLAG="/hadoop/dfs/name/.formatted"

echo "[NameNode] 检查 HDFS 格式化状态..."

# 首次启动: 格式化 NameNode
if [ ! -f "${FORMATTED_FLAG}" ]; then
    echo "[NameNode] 首次启动, 正在格式化 HDFS..."
    hdfs namenode -format -force -nonInteractive
    touch "${FORMATTED_FLAG}"
    echo "[NameNode] HDFS 格式化完成"
else
    echo "[NameNode] HDFS 已格式化, 跳过"
fi

# 启动 NameNode (后台)
echo "[NameNode] 启动 NameNode 进程..."
hdfs namenode &
NAMENODE_PID=$!

# 等待 NameNode 就绪
echo "[NameNode] 等待 NameNode 就绪..."
for i in $(seq 1 60); do
    if hdfs dfs -ls / >/dev/null 2>&1; then
        echo "[NameNode] NameNode 就绪 (${i}s)"
        break
    fi
    sleep 2
done

# 创建项目目录 (幂等操作)
echo "[NameNode] 初始化 HDFS 项目目录..."
hdfs dfs -mkdir -p /weibo/raw
hdfs dfs -mkdir -p /weibo/output
hdfs dfs -mkdir -p /weibo/checkpoint
hdfs dfs -chmod -R 777 /weibo
echo "[NameNode] HDFS 目录初始化完成:"
hdfs dfs -ls -R /weibo 2>/dev/null || true

# 前台保持运行
echo "[NameNode] NameNode 运行中 (PID: ${NAMENODE_PID})"
wait ${NAMENODE_PID}
