#!/bin/bash
# ====================================================================
# HBase Master 启动入口脚本
# - 启动 HBase Master
# - 首次自动创建 weibo_sentiment 表
# ====================================================================
set -e

INIT_FLAG="/hbase/tmp/.tables_created"

echo "[HBase] 启动 HBase Master..."
/hbase/bin/hbase master start &
HBASE_PID=$!

# 等待 HBase Master 就绪
echo "[HBase] 等待 HBase Master 就绪..."
for i in $(seq 1 90); do
    if echo "status" | /hbase/bin/hbase shell 2>/dev/null | grep -q "active"; then
        echo "[HBase] Master 就绪 (${i}s)"
        break
    fi
    if [ $i -eq 90 ]; then
        echo "[HBase] 警告: 等待超时, 继续尝试建表..."
    fi
    sleep 2
done

# 首次创建表 (幂等)
if [ ! -f "${INIT_FLAG}" ]; then
    echo "[HBase] 首次启动, 创建 weibo_sentiment 表..."
    sleep 10  # 额外等待 RegionServer 注册

    /hbase/bin/hbase shell <<'EOF'
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
EOF

    if [ $? -eq 0 ]; then
        touch "${INIT_FLAG}"
        echo "[HBase] 表创建完成"
    else
        echo "[HBase] 警告: 表创建可能失败, 后续可手动重试"
    fi
else
    echo "[HBase] 表已存在, 跳过创建"
fi

# 前台保持运行
echo "[HBase] HBase Master 运行中 (PID: ${HBASE_PID})"
wait ${HBASE_PID}
