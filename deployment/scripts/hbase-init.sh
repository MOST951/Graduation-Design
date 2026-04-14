#!/bin/bash
# ====================================================================
# HBase Master 启动入口脚本
# - 启动 HBase Master (前台保持存活)
# - 建表逻辑在后台运行, 等 RegionServer 注册后自动创建
# ====================================================================

INIT_FLAG="/hbase/tmp/.tables_created"

# ---------- 后台建表函数 ----------
create_tables_bg() {
    local init_flag="$1"

    if [ -f "${init_flag}" ]; then
        echo "[HBase-init] 表已存在, 跳过创建"
        return 0
    fi

    # 1) 等 Master 自身就绪
    echo "[HBase-init] 等待 HBase Master 就绪..."
    for i in $(seq 1 120); do
        if curl -sf http://localhost:16010/master-status >/dev/null 2>&1 || wget -q -O /dev/null http://localhost:16010/master-status 2>/dev/null; then
            echo "[HBase-init] Master Web UI 就绪 (${i}s)"
            break
        fi
        [ "$i" -eq 120 ] && echo "[HBase-init] 警告: Master 等待超时" && return 1
        sleep 2
    done

    # 2) 等至少 1 个 RegionServer 注册
    echo "[HBase-init] 等待 RegionServer 注册 (最多 180s)..."
    for i in $(seq 1 90); do
        if echo "status 'simple'" | /hbase/bin/hbase shell 2>/dev/null | grep -qi "regionserver"; then
            echo "[HBase-init] RegionServer 已注册 (${i}×2s)"
            break
        fi
        [ "$i" -eq 90 ] && echo "[HBase-init] 警告: RegionServer 等待超时, 仍尝试建表..."
        sleep 2
    done

    # 3) 建表 (带超时)
    echo "[HBase-init] 创建 weibo_sentiment 表..."
    timeout 120 /hbase/bin/hbase shell <<'HBASE_SCRIPT'
create_if_not_exists = lambda do |table_name, *args|
  if !admin.tableExists?(table_name)
    create table_name, *args
    puts "Created table: #{table_name}"
  else
    puts "Table already exists: #{table_name}"
  end
end

# 舆情分析结果表
# cf_info: 基础信息 (微博ID, 内容, 用户, 时间)
# cf_sentiment: 情感分析 (得分, 标签, 置信度, 方法)
# cf_metrics: 热度指标 (转发, 评论, 点赞, 热度分, 排序分)
create_if_not_exists.call 'weibo_sentiment', \
  {NAME => 'cf_info', VERSIONS => 1, TTL => 'FOREVER', COMPRESSION => 'SNAPPY'}, \
  {NAME => 'cf_sentiment', VERSIONS => 3, TTL => 'FOREVER', COMPRESSION => 'SNAPPY'}, \
  {NAME => 'cf_metrics', VERSIONS => 5, TTL => 'FOREVER', COMPRESSION => 'SNAPPY'}

# 原始数据索引表 (按时间分区, 加速范围查询)
create_if_not_exists.call 'weibo_raw_index', \
  {NAME => 'cf_idx', VERSIONS => 1, COMPRESSION => 'SNAPPY'}

puts "All tables ready."
list
exit
HBASE_SCRIPT

    if [ $? -eq 0 ]; then
        mkdir -p "$(dirname "${init_flag}")"
        touch "${init_flag}"
        echo "[HBase-init] 表创建完成"
    else
        echo "[HBase-init] 警告: 表创建失败, 后续可手动执行:  docker exec -it weibo_sentiment_hbase_master /hbase/bin/hbase shell"
    fi
}

# ---------- 主流程 ----------
echo "[HBase] 启动 HBase Master..."

# 启动建表子进程 (后台, 不影响主进程存活)
create_tables_bg "${INIT_FLAG}" &

# 前台启动 Master —— 容器随此进程存活
exec /hbase/bin/hbase master start
