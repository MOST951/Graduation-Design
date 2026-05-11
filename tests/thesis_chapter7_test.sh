#!/bin/bash
# ============================================================
# 第七章 系统测试 — 论文数据采集脚本
# ============================================================
API="http://localhost:5000"
DB="docker exec weibo_sentiment_db mysql -u weibo_user -p123456 -N weibo_sentiment"

echo "============================================================"
echo " 第七章系统测试 数据采集"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"

# =============================================================
# 7.2.1 数据采集功能测试
# =============================================================
echo ""
echo "========================================"
echo " 7.2.1 数据采集功能测试"
echo "========================================"

# 清理旧测试数据的统计
echo "--- 当前数据库基线 ---"
base_weibo=$($DB -e "SELECT COUNT(*) FROM weibo_core_data" 2>/dev/null)
echo "  当前微博总数: $base_weibo"

# 启动采集任务: 关键词"人工智能"
echo ""
echo "--- 步骤1: 启动采集任务(关键词=人工智能) ---"
t_start=$(date +%s%3N)
collect_resp=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"keywords":["人工智能"],"pages":3,"crawl_hot":true,"auto_process":true}' \
  "$API/api/weibo/collect" 2>/dev/null)
task_id=$(echo "$collect_resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('task_id',''))" 2>/dev/null)
echo "  任务ID: $task_id"
echo "  创建响应: $(echo "$collect_resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message',''))" 2>/dev/null)"

# 等待完成并记录各阶段
echo ""
echo "--- 步骤2: 等待流水线完成(监控状态) ---"
prev_phase=""
phase_times=""
for i in $(seq 1 90); do
  sleep 2
  st=$(curl -s "$API/api/weibo/collect/status/$task_id" 2>/dev/null)
  status=$(echo "$st" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('status',''))" 2>/dev/null)
  phase=$(echo "$st" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('phase',''))" 2>/dev/null)
  progress=$(echo "$st" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('progress',0))" 2>/dev/null)
  
  if [ "$phase" != "$prev_phase" ]; then
    t_now=$(date +%s%3N)
    echo "  [$(date '+%H:%M:%S')] 阶段: $phase | 进度: $progress% | 状态: $status"
    phase_times="$phase_times|$phase:$t_now"
    prev_phase="$phase"
  fi
  
  if [ "$status" = "completed" ] || [ "$status" = "failed" ]; then
    t_end=$(date +%s%3N)
    total_ms=$((t_end - t_start))
    echo "  最终状态: $status"
    echo "  总耗时: ${total_ms}ms"
    break
  fi
done

# 步骤3: 验证数据
echo ""
echo "--- 步骤3: 数据验证 ---"
new_weibo=$($DB -e "SELECT COUNT(*) FROM weibo_core_data" 2>/dev/null)
added=$((new_weibo - base_weibo))
echo "  新增微博数: $added 条 (之前$base_weibo → 现在$new_weibo)"

# 字段完整性
echo ""
echo "--- 步骤4: 字段完整性检查 ---"
null_check=$($DB -e "
SELECT 
  SUM(CASE WHEN weibo_id IS NULL THEN 1 ELSE 0 END) as null_id,
  SUM(CASE WHEN content IS NULL OR content='' THEN 1 ELSE 0 END) as null_content,
  SUM(CASE WHEN created_at IS NULL THEN 1 ELSE 0 END) as null_time,
  SUM(CASE WHEN reposts_count IS NULL THEN 1 ELSE 0 END) as null_reposts,
  SUM(CASE WHEN comments_count IS NULL THEN 1 ELSE 0 END) as null_comments,
  SUM(CASE WHEN attitudes_count IS NULL THEN 1 ELSE 0 END) as null_likes
FROM weibo_core_data
" 2>/dev/null)
echo "  空值检查 (id/content/time/reposts/comments/likes): $null_check"

# 去重检查
echo ""
echo "--- 步骤5: 去重检查 ---"
dup_count=$($DB -e "SELECT COUNT(*) - COUNT(DISTINCT weibo_id) as dups FROM weibo_core_data" 2>/dev/null)
echo "  重复微博数: $dup_count"

# =============================================================
# 7.2.2 情感分析功能测试
# =============================================================
echo ""
echo "========================================"
echo " 7.2.2 情感分析功能测试"
echo "========================================"

# 构造测试样本(正面/负面/中性各代表文本)
echo "--- 词典模式 vs 混合模式对比 ---"

test_texts=(
  "这个产品太棒了，质量非常好，用着很满意！|positive"
  "今天心情特别好，一切都很顺利！|positive"
  "这家店的服务真的很不错推荐给大家|positive"
  "非常感谢你的帮助让我解决了问题|positive"
  "这次旅行体验很好风景也很美|positive"
  "终于拿到了心仪的offer太开心了|positive"
  "服务态度极差，再也不来了|negative"
  "这个质量太差了完全是浪费钱|negative"
  "等了两个小时还没上菜差评|negative"
  "物流太慢了而且包装破损严重|negative"
  "售后态度恶劣问题一直没解决|negative"
  "这个电影太难看了浪费时间|negative"
  "今天天气多云转晴|neutral"
  "明天会议在下午三点开始|neutral"
  "这款手机采用了最新处理器|neutral"
  "官方发布了新版本更新公告|neutral"
  "目前该项目正在推进中|neutral"
  "该报告已提交给相关部门|neutral"
  "太讽刺了号称最好的服务就这水平|negative"
  "呵呵说得好听做得难看|negative"
)

dict_correct=0
hybrid_correct=0
dict_total=0
hybrid_total=0

for item in "${test_texts[@]}"; do
  text="${item%%|*}"
  expected="${item#*|}"
  
  # 混合模式(默认)
  resp=$(curl -s -X POST -H 'Content-Type: application/json' \
    -d "{\"text\":\"$text\"}" \
    "$API/api/sentiment/analyze" 2>/dev/null)
  
  h_score=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(d.get('score', d.get('hybrid_score', d.get('sentiment_score',0))))" 2>/dev/null)
  h_method=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(d.get('method', d.get('analysis_method','')))" 2>/dev/null)
  d_score=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(d.get('dict_score',0))" 2>/dev/null)
  b_score=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(d.get('bert_score', d.get('bert_positive_prob','N/A')))" 2>/dev/null)
  
  # 判断分类
  if python3 -c "s=float('$h_score'); exit(0 if s>0.2 else 1)" 2>/dev/null; then
    h_label="positive"
  elif python3 -c "s=float('$h_score'); exit(0 if s<-0.2 else 1)" 2>/dev/null; then
    h_label="negative"
  else
    h_label="neutral"
  fi
  
  if python3 -c "s=float('${d_score:-0}'); exit(0 if s>0.2 else 1)" 2>/dev/null; then
    d_label="positive"
  elif python3 -c "s=float('${d_score:-0}'); exit(0 if s<-0.2 else 1)" 2>/dev/null; then
    d_label="negative"
  else
    d_label="neutral"
  fi
  
  ((dict_total++))
  ((hybrid_total++))
  if [ "$d_label" = "$expected" ]; then ((dict_correct++)); fi
  if [ "$h_label" = "$expected" ]; then ((hybrid_correct++)); fi
  
  echo "  [$expected] hybrid=$h_score($h_label) dict=$d_score($d_label) method=$h_method | \"${text:0:20}...\""
done

dict_acc=$(python3 -c "print(f'{$dict_correct/$dict_total*100:.1f}')" 2>/dev/null)
hybrid_acc=$(python3 -c "print(f'{$hybrid_correct/$hybrid_total*100:.1f}')" 2>/dev/null)
echo ""
echo "  词典模式准确率:  $dict_correct/$dict_total = ${dict_acc}%"
echo "  混合模式准确率:  $hybrid_correct/$hybrid_total = ${hybrid_acc}%"

# 数据库中的情感分布
echo ""
echo "--- 数据库情感分布 ---"
$DB -e "SELECT sentiment_class, COUNT(*) as cnt, 
  ROUND(COUNT(*)*100.0/(SELECT COUNT(*) FROM sentiment_analysis_results),1) as pct
  FROM sentiment_analysis_results GROUP BY sentiment_class ORDER BY cnt DESC" 2>/dev/null

# =============================================================
# 7.2.3 数据展示功能测试
# =============================================================
echo ""
echo "========================================"
echo " 7.2.3 数据展示功能测试"
echo "========================================"

declare -A dashboard_eps
dashboard_eps=(
  ["情感分布图"]="$API/api/dashboard/sentiment-distribution"
  ["情感趋势图"]="$API/api/dashboard/trend"
  ["热点话题词云"]="$API/api/topics/wordcloud"
  ["总览仪表盘"]="$API/api/dashboard/overview"
  ["实时监控"]="$API/api/dashboard/realtime"
  ["预警数据"]="$API/api/dashboard/alerts"
  ["话题列表"]="$API/api/topics/list"
  ["话题排名"]="$API/api/topics/ranked"
  ["传播网络"]="$API/api/propagation/network"
  ["影响力排名"]="$API/api/propagation/influence-ranking"
  ["三维度排序"]="$API/api/pipeline/ranking?limit=20"
)

for name in "${!dashboard_eps[@]}"; do
  url="${dashboard_eps[$name]}"
  t1=$(date +%s%3N)
  code=$(curl -s -o /tmp/dash_resp.json -w '%{http_code}' --max-time 10 "$url" 2>/dev/null)
  t2=$(date +%s%3N)
  ms=$((t2 - t1))
  data_count=$(python3 -c "
import json
d=json.load(open('/tmp/dash_resp.json'))
data=d.get('data',{})
if isinstance(data, list): print(len(data))
elif isinstance(data, dict):
  for k in ['items','data','list','records','distribution','trend','nodes']:
    if k in data: 
      print(len(data[k]) if isinstance(data[k],list) else 1)
      break
  else: print(len(data))
else: print(0)
" 2>/dev/null || echo "?")
  echo "  $name | HTTP $code | ${ms}ms | 数据量: $data_count"
done

# =============================================================
# 7.3.1 数据处理效率测试
# =============================================================
echo ""
echo "========================================"
echo " 7.3.1 数据处理效率测试"
echo "========================================"

# 使用已有流水线日志提取各阶段耗时
echo "--- 从最近流水线日志提取各阶段耗时 ---"
docker logs weibo_sentiment_web --since 30m 2>&1 | grep -E "\[collect_" | grep -E "阶段[1-5]|完成|采集完成" | tail -20

echo ""
echo "--- 计算各阶段耗时 ---"
# 提取最近一次完整流水线的时间戳
latest_task=$(docker logs weibo_sentiment_web --since 30m 2>&1 | grep "阶段1: 开始数据采集" | tail -1 | grep -oP "collect_\d+")
if [ -n "$latest_task" ]; then
  echo "  分析任务: $latest_task"
  
  stage1_start=$(docker logs weibo_sentiment_web --since 30m 2>&1 | grep "$latest_task.*阶段1" | head -1 | grep -oP "\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}")
  stage2_start=$(docker logs weibo_sentiment_web --since 30m 2>&1 | grep "$latest_task.*阶段2" | head -1 | grep -oP "\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}")
  stage3_start=$(docker logs weibo_sentiment_web --since 30m 2>&1 | grep "$latest_task.*阶段3" | head -1 | grep -oP "\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}")
  stage4_start=$(docker logs weibo_sentiment_web --since 30m 2>&1 | grep "$latest_task.*阶段4" | head -1 | grep -oP "\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}")
  stage5_start=$(docker logs weibo_sentiment_web --since 30m 2>&1 | grep "$latest_task.*阶段5" | head -1 | grep -oP "\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}")
  done_time=$(docker logs weibo_sentiment_web --since 30m 2>&1 | grep "$latest_task.*处理完成" | tail -1 | grep -oP "\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}")
  
  echo "  阶段1(采集)开始: $stage1_start"
  echo "  阶段2(清洗)开始: $stage2_start"
  echo "  阶段3(分析)开始: $stage3_start"
  echo "  阶段4(排序)开始: $stage4_start"
  echo "  阶段5(入库)开始: $stage5_start"
  echo "  全部完成:         $done_time"
  
  # 计算秒数差
  python3 << 'PYEOF'
from datetime import datetime
import sys

def parse_ts(s):
    if not s: return None
    return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S,%f")

stages = {
    "stage1": """STAGE1""",
    "stage2": """STAGE2""",
    "stage3": """STAGE3""",
    "stage4": """STAGE4""",
    "stage5": """STAGE5""",
    "done":   """DONE"""
}
PYEOF
  
  # 用简单方法计算
  python3 -c "
from datetime import datetime
def p(s):
    if not s: return None
    return datetime.strptime(s.strip(), '%Y-%m-%d %H:%M:%S,%f')
s1=p('$stage1_start'); s2=p('$stage2_start'); s3=p('$stage3_start')
s4=p('$stage4_start'); s5=p('$stage5_start'); done=p('$done_time')
if s1 and s2: print(f'  数据采集耗时: {(s2-s1).total_seconds():.1f}s')
if s2 and s3: print(f'  数据清洗耗时: {(s3-s2).total_seconds():.1f}s')
if s3 and s4: print(f'  情感分析耗时: {(s4-s3).total_seconds():.1f}s')
if s4 and s5: print(f'  三维度排序耗时: {(s5-s4).total_seconds():.1f}s')
if s5 and done: print(f'  结果入库耗时: {(done-s5).total_seconds():.1f}s')
if s1 and done: print(f'  总耗时: {(done-s1).total_seconds():.1f}s')
" 2>/dev/null
fi

# 单条情感分析性能测试
echo ""
echo "--- 单条情感分析响应时间 ---"
for i in 1 2 3 4 5; do
  t1=$(date +%s%3N)
  curl -s -X POST -H 'Content-Type: application/json' \
    -d '{"text":"这是一条用于性能测试的微博文本内容，测试系统响应速度"}' \
    "$API/api/sentiment/analyze" > /dev/null 2>&1
  t2=$(date +%s%3N)
  echo "  第${i}次: $((t2-t1))ms"
done

# =============================================================
# 7.3.2 系统稳定性测试
# =============================================================
echo ""
echo "========================================"
echo " 7.3.2 系统稳定性测试"
echo "========================================"

echo "--- 容器运行时间 ---"
docker ps --filter "name=weibo_sentiment" --format "  {{.Names}}: {{.Status}}" 2>/dev/null

echo ""
echo "--- 内存使用 ---"
docker stats --no-stream --format "  {{.Name}}: {{.MemUsage}} ({{.MemPerc}})" $(docker ps --filter "name=weibo_sentiment" -q) 2>/dev/null

echo ""
echo "--- 数据库统计 ---"
echo "  总查询数:"
$DB -e "SHOW GLOBAL STATUS LIKE 'Questions'" 2>/dev/null
echo "  活跃连接:"
$DB -e "SHOW GLOBAL STATUS LIKE 'Threads_connected'" 2>/dev/null
echo "  慢查询:"
$DB -e "SHOW GLOBAL STATUS LIKE 'Slow_queries'" 2>/dev/null

echo ""
echo "--- 批次成功率 ---"
total_batches=$($DB -e "SELECT COUNT(*) FROM crawl_batch_log" 2>/dev/null)
success_batches=$($DB -e "SELECT COUNT(*) FROM crawl_batch_log WHERE status='completed'" 2>/dev/null)
echo "  总批次: $total_batches, 成功: $success_batches"
if [ "$total_batches" -gt 0 ]; then
  rate=$(python3 -c "print(f'{$success_batches/$total_batches*100:.1f}')" 2>/dev/null)
  echo "  成功率: ${rate}%"
fi

echo ""
echo "--- Flask 错误日志统计 ---"
err_count=$(docker logs weibo_sentiment_web --since 3h 2>&1 | grep -c "ERROR" || echo "0")
warn_count=$(docker logs weibo_sentiment_web --since 3h 2>&1 | grep -c "WARNING" || echo "0")
echo "  最近3小时: ERROR=$err_count, WARNING=$warn_count"

echo ""
echo "========================================"
echo " 测试完成 $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
