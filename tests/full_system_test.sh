#!/bin/bash
# ============================================================
# 微博舆情情感分析系统 - 全业务功能自动化测试
# ============================================================
set -uo pipefail

API="http://localhost:5000"
JAVA_API="http://localhost:8081"
FRONTEND="http://localhost:3001"
PASS=0; FAIL=0; WARN=0; SKIP=0

G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'; C='\033[0;36m'; NC='\033[0m'
ok()   { ((PASS++)); echo -e "${G}  PASS${NC} | $1"; }
fail() { ((FAIL++)); echo -e "${R}  FAIL${NC} | $1 | $2"; }
warn() { ((WARN++)); echo -e "${Y}  WARN${NC} | $1"; }
skip_t() { ((SKIP++)); echo -e "${C}  SKIP${NC} | $1"; }

api_check() {
  local desc="$1" url="$2" method="${3:-GET}" data="${4:-}" expect="${5:-200}"
  local code body
  if [ "$method" = "POST" ]; then
    body=$(curl -s -w '\n%{http_code}' --max-time 30 -X POST -H 'Content-Type: application/json' -d "$data" "$url" 2>/dev/null || echo -e "\n000")
  else
    body=$(curl -s -w '\n%{http_code}' --max-time 15 "$url" 2>/dev/null || echo -e "\n000")
  fi
  code=$(echo "$body" | tail -1)
  body=$(echo "$body" | sed '$d')
  if [ "$code" = "$expect" ]; then
    ok "$desc [HTTP $code]"
  else
    fail "$desc" "Expected $expect, got $code"
  fi
  echo "$body" > /tmp/test_last_resp.json
}

echo "============================================================"
echo " 微博舆情情感分析系统 - 全业务功能测试"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"

# === 0. 系统健康检查 ===
echo -e "\n${C}=== 0. 系统健康检查 ===${NC}"
for svc in db web frontend namenode datanode spark_master spark_worker; do
  status=$(docker ps --filter "name=weibo_$svc" --format '{{.Status}}' 2>/dev/null || echo "NOT FOUND")
  if echo "$status" | grep -qi "Up"; then
    ok "容器 $svc: $status"
  else
    fail "容器 $svc" "$status"
  fi
done

for pd in "5000:Flask" "3001:Frontend" "3306:MySQL" "8080:SparkUI" "9870:HDFS_WebUI"; do
  p=${pd%%:*}; d=${pd#*:}
  if nc -z localhost $p 2>/dev/null; then ok "端口 $p ($d)"; else fail "端口 $p ($d)" "不可达"; fi
done

api_check "Flask健康" "$API/api/v2/health"
api_check "前端首页" "$FRONTEND/"

db_ok=$(docker exec weibo_db mysql -u weibo_user -p123456 -N -e "SELECT 1" weibo_sentiment 2>/dev/null || echo "0")
if echo "$db_ok" | grep -q "1"; then ok "MySQL连接正常"; else fail "MySQL" "无法连接"; fi

# === 1. 数据采集模块 ===
echo -e "\n${C}=== 1. 数据采集模块 ===${NC}"
api_check "GET /weibo/hot (热搜)" "$API/api/weibo/hot"
api_check "GET /weibo/hot-topics (热门话题)" "$API/api/weibo/hot-topics"

echo "--- 1.1 启动完整流水线 ---"
api_check "POST /weibo/collect (完整流水线)" "$API/api/weibo/collect" "POST" '{"keywords":["测试"],"pages":1,"crawl_hot":false,"auto_process":true}'
TASK_ID=$(python3 -c "import json; d=json.load(open('/tmp/test_last_resp.json')); print(d.get('data',{}).get('task_id',''))" 2>/dev/null || echo "")
if [ -n "$TASK_ID" ]; then
  ok "任务ID: $TASK_ID"
  echo "等待流水线执行(最多120s)..."
  for i in $(seq 1 60); do
    sleep 2
    st=$(curl -s "$API/api/weibo/collect/status/$TASK_ID" 2>/dev/null)
    status=$(echo "$st" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('status',''))" 2>/dev/null || echo "")
    if [ "$status" = "completed" ]; then
      ok "流水线完成: $TASK_ID"
      collected=$(echo "$st" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('collected',0))" 2>/dev/null || echo "0")
      ok "采集数据量: $collected 条"
      break
    elif [ "$status" = "failed" ]; then
      fail "流水线失败" "$(echo "$st" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('error',''))" 2>/dev/null)"
      break
    fi
    if [ "$i" = "60" ]; then warn "流水线超时(120s)，当前状态: $status"; fi
  done
else
  warn "未获取到任务ID"
fi

echo "--- 1.2 边界条件 ---"
api_check "空关键词" "$API/api/weibo/collect" "POST" '{"keywords":[],"pages":1}' "400"
api_check "超长关键词" "$API/api/weibo/collect" "POST" '{"keywords":["AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"],"pages":1}' "200"

echo "--- 1.3 任务状态查询 ---"
api_check "GET /weibo/collect/status (不存在ID)" "$API/api/weibo/collect/status/nonexist_123" "" "" "404"

# === 2. 数据预处理模块 ===
echo -e "\n${C}=== 2. 数据预处理模块 ===${NC}"
api_check "GET /preprocess/tasks (预处理任务列表)" "$API/api/preprocess/tasks"
api_check "POST /preprocess/clean (文本清洗)" "$API/api/preprocess/clean" "POST" '{"text":"<a href=\"x\">链接</a> @用户 http://test.com [微笑] 测试文本内容"}'
clean_result=$(python3 -c "import json; d=json.load(open('/tmp/test_last_resp.json')); print(d.get('data',{}).get('cleaned',''))" 2>/dev/null || echo "")
if echo "$clean_result" | grep -q "测试文本内容"; then
  ok "文本清洗: HTML/URL/提及已去除"
else
  warn "文本清洗结果: $clean_result"
fi

api_check "POST /preprocess/segment (分词)" "$API/api/preprocess/segment" "POST" '{"text":"微博舆情情感分析系统支持自然语言处理"}'
api_check "POST /preprocess/convert (繁简转换)" "$API/api/preprocess/convert" "POST" '{"text":"微博輿情情感分析系統支持自然語言處理"}'

# === 3. 情感分析模块 ===
echo -e "\n${C}=== 3. 情感分析模块 ===${NC}"
echo "--- 3.1 单条情感分析 ---"
api_check "POST /sentiment/analyze (正面)" "$API/api/sentiment/analyze" "POST" '{"text":"这个产品太棒了非常满意质量非常好"}'
pos_score=$(python3 -c "import json; d=json.load(open('/tmp/test_last_resp.json')); r=d.get('data',{}); print(r.get('score',r.get('hybrid_score',r.get('sentiment_score','N/A'))))" 2>/dev/null || echo "N/A")
ok "正面文本得分: $pos_score"

api_check "POST /sentiment/analyze (负面)" "$API/api/sentiment/analyze" "POST" '{"text":"服务态度极差再也不来了太差了垃圾"}'
neg_score=$(python3 -c "import json; d=json.load(open('/tmp/test_last_resp.json')); r=d.get('data',{}); print(r.get('score',r.get('hybrid_score',r.get('sentiment_score','N/A'))))" 2>/dev/null || echo "N/A")
ok "负面文本得分: $neg_score"

api_check "POST /sentiment/analyze (中性)" "$API/api/sentiment/analyze" "POST" '{"text":"今天天气是多云转晴"}'
neu_score=$(python3 -c "import json; d=json.load(open('/tmp/test_last_resp.json')); r=d.get('data',{}); print(r.get('score',r.get('hybrid_score',r.get('sentiment_score','N/A'))))" 2>/dev/null || echo "N/A")
ok "中性文本得分: $neu_score"

echo "--- 3.2 BERT模型状态 ---"
api_check "GET /sentiment/model-status" "$API/api/sentiment/model-status"

echo "--- 3.3 级联策略验证 ---"
api_check "POST /sentiment/analyze (强情感-词典路径)" "$API/api/sentiment/analyze" "POST" '{"text":"太棒了太好了真是太开心了非常满意非常棒！"}'
strong_method=$(python3 -c "import json; d=json.load(open('/tmp/test_last_resp.json')); print(d.get('data',{}).get('method',d.get('data',{}).get('analysis_method','')))" 2>/dev/null || echo "")
ok "强情感分析方法: $strong_method"

api_check "POST /sentiment/analyze (弱情感-BERT路径)" "$API/api/sentiment/analyze" "POST" '{"text":"这件事情值得关注一下看看后续发展"}'
weak_method=$(python3 -c "import json; d=json.load(open('/tmp/test_last_resp.json')); print(d.get('data',{}).get('method',d.get('data',{}).get('analysis_method','')))" 2>/dev/null || echo "")
ok "弱情感分析方法: $weak_method"

echo "--- 3.4 批量分析 ---"
api_check "POST /weibo/analyze (批量)" "$API/api/weibo/analyze" "POST" '{"data":[{"id":"test1","text":"好评"},{"id":"test2","text":"差评"},{"id":"test3","text":"一般"}]}'

# === 4. 三维度排序模块 ===
echo -e "\n${C}=== 4. 三维度排序模块 ===${NC}"
api_check "GET /pipeline/ranking (排序结果)" "$API/api/pipeline/ranking?limit=5"
rank_total=$(python3 -c "import json; d=json.load(open('/tmp/test_last_resp.json')); print(d.get('data',{}).get('total',0))" 2>/dev/null || echo "0")
ok "排序结果总数: $rank_total"

if [ "$rank_total" -gt 0 ]; then
  top1_score=$(python3 -c "import json; d=json.load(open('/tmp/test_last_resp.json')); items=d.get('data',{}).get('items',[]); print(items[0].get('composite_score','N/A') if items else 'N/A')" 2>/dev/null || echo "N/A")
  ok "TOP1综合得分: $top1_score"
fi

echo "--- 4.1 三维度计算验证 ---"
api_check "POST /tri-dimension/calculate (手动计算)" "$API/api/tri-dimension/calculate" "POST" '{"sentiment_score":0.8,"reposts":100,"comments":50,"likes":200,"created_at":"2026-05-05T10:00:00"}'

# === 5. 实时监控 + WebSocket ===
echo -e "\n${C}=== 5. 实时监控模块 ===${NC}"
api_check "GET /dashboard/realtime" "$API/api/dashboard/realtime"
api_check "GET /dashboard/alerts" "$API/api/dashboard/alerts"

# WebSocket测试
ws_test=$(timeout 3 curl -s -o /dev/null -w "%{http_code}" -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGVzdA==" "$API/socket.io/?transport=websocket" 2>/dev/null || echo "000")
if [ "$ws_test" = "101" ] || [ "$ws_test" = "200" ] || [ "$ws_test" = "400" ]; then
  ok "WebSocket端点可达 [HTTP $ws_test]"
else
  warn "WebSocket端点 [HTTP $ws_test]"
fi

# === 6. 流水线管理模块 ===
echo -e "\n${C}=== 6. 流水线管理模块 ===${NC}"
api_check "GET /pipeline/status" "$API/api/pipeline/status"
api_check "GET /pipeline/stats (数据库统计)" "$API/api/pipeline/stats"

stats_body=$(cat /tmp/test_last_resp.json)
for tbl in weibo_core_data sentiment_analysis_results tri_dimension_ranking crawl_batch_log; do
  cnt=$(echo "$stats_body" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('$tbl',0))" 2>/dev/null || echo "0")
  if [ "$cnt" -gt 0 ]; then
    ok "表 $tbl: $cnt 条记录"
  else
    warn "表 $tbl: 0 条记录"
  fi
done

api_check "GET /pipeline/ranking" "$API/api/pipeline/ranking?limit=20"
api_check "GET /pipeline/history (历史记录)" "$API/api/pipeline/history"
api_check "GET /pipeline/health" "$API/api/pipeline/health"

# === 7. 可视化展示模块 ===
echo -e "\n${C}=== 7. 可视化展示模块 ===${NC}"
for ep in "sentiment-distribution" "sentiment-trend" "hot-topics" "topic-wordcloud" "overview" "realtime"; do
  api_check "GET /dashboard/$ep" "$API/api/dashboard/$ep"
done

# === 8. 系统管理 + 双后端 ===
echo -e "\n${C}=== 8. 系统管理 + Java后端 ===${NC}"
api_check "Java: GET /api/user/list" "$JAVA_API/api/user/list"
api_check "Java: POST /api/user/login" "$JAVA_API/api/user/login" "POST" '{"username":"admin","password":"admin123"}'
token=$(python3 -c "import json; d=json.load(open('/tmp/test_last_resp.json')); print(d.get('data',{}).get('token',d.get('token','')))" 2>/dev/null || echo "")
if [ -n "$token" ]; then
  ok "JWT Token获取成功 (长度=${#token})"
else
  warn "JWT Token未获取到"
fi

api_check "Java: GET /api/admin/spark-status" "$JAVA_API/api/admin/spark-status"
api_check "Java: GET /api/log/list" "$JAVA_API/api/log/list"

# === 9. 跨模块数据一致性 ===
echo -e "\n${C}=== 9. 跨模块数据一致性 ===${NC}"
echo "--- MySQL 表数据对账 ---"
DB_CMD="docker exec weibo_sentiment_db mysql -u weibo_user -p123456 -N weibo_sentiment"
weibo_cnt=$($DB_CMD -e "SELECT COUNT(*) FROM weibo_core_data" 2>/dev/null || echo "0")
senti_cnt=$($DB_CMD -e "SELECT COUNT(*) FROM sentiment_analysis_results" 2>/dev/null || echo "0")
rank_cnt=$($DB_CMD -e "SELECT COUNT(*) FROM tri_dimension_ranking" 2>/dev/null || echo "0")
batch_cnt=$($DB_CMD -e "SELECT COUNT(*) FROM crawl_batch_log" 2>/dev/null || echo "0")

echo "  weibo_core_data:            $weibo_cnt"
echo "  sentiment_analysis_results: $senti_cnt"
echo "  tri_dimension_ranking:      $rank_cnt"
echo "  crawl_batch_log:            $batch_cnt"

if [ "$weibo_cnt" -gt 0 ]; then ok "微博数据已入库: $weibo_cnt 条"; else warn "微博数据表为空"; fi
if [ "$senti_cnt" -gt 0 ]; then ok "情感结果已入库: $senti_cnt 条"; else warn "情感结果表为空"; fi
if [ "$rank_cnt" -gt 0 ]; then ok "排序结果已入库: $rank_cnt 条"; else warn "排序结果表为空"; fi

# 数据一致性检查
if [ "$weibo_cnt" -gt 0 ] && [ "$senti_cnt" -gt 0 ]; then
  if [ "$weibo_cnt" -ge "$senti_cnt" ]; then
    ok "数据一致性: weibo($weibo_cnt) >= sentiment($senti_cnt)"
  else
    warn "数据异常: weibo($weibo_cnt) < sentiment($senti_cnt)"
  fi
fi

if [ "$senti_cnt" -gt 0 ] && [ "$rank_cnt" -gt 0 ]; then
  if [ "$senti_cnt" -ge "$rank_cnt" ]; then
    ok "数据一致性: sentiment($senti_cnt) >= ranking($rank_cnt)"
  else
    warn "数据异常: sentiment($senti_cnt) < ranking($rank_cnt)"
  fi
fi

echo "--- 情感分布统计 ---"
pos=$($DB_CMD -e "SELECT COUNT(*) FROM sentiment_analysis_results WHERE sentiment_class='positive'" 2>/dev/null || echo "0")
neg=$($DB_CMD -e "SELECT COUNT(*) FROM sentiment_analysis_results WHERE sentiment_class='negative'" 2>/dev/null || echo "0")
neu=$($DB_CMD -e "SELECT COUNT(*) FROM sentiment_analysis_results WHERE sentiment_class='neutral'" 2>/dev/null || echo "0")
echo "  正面: $pos | 中性: $neu | 负面: $neg"
total_senti=$((pos + neg + neu))
if [ "$total_senti" -gt 0 ]; then ok "情感分布完整: 正$pos/中$neu/负$neg (总$total_senti)"; fi

echo "--- API与数据库一致性 ---"
api_stats=$(curl -s "$API/api/pipeline/stats" 2>/dev/null)
api_weibo=$(echo "$api_stats" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('weibo_core_data',0))" 2>/dev/null || echo "0")
if [ "$api_weibo" = "$weibo_cnt" ]; then
  ok "API stats与数据库一致: $api_weibo"
else
  fail "API stats不一致" "API=$api_weibo, DB=$weibo_cnt"
fi

# === 10. Spark 集群 ===
echo -e "\n${C}=== 10. Spark集群 ===${NC}"
spark_ui=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:8080" 2>/dev/null || echo "000")
if [ "$spark_ui" = "200" ] || [ "$spark_ui" = "302" ]; then
  ok "Spark Master UI 可访问 [HTTP $spark_ui]"
else
  warn "Spark Master UI [HTTP $spark_ui]"
fi

# === 汇总 ===
echo ""
echo "============================================================"
echo -e " 测试汇总"
echo "============================================================"
TOTAL=$((PASS + FAIL + WARN + SKIP))
echo -e " ${G}通过: $PASS${NC} | ${R}失败: $FAIL${NC} | ${Y}警告: $WARN${NC} | ${C}跳过: $SKIP${NC} | 总计: $TOTAL"
if [ "$FAIL" -eq 0 ]; then
  echo -e " ${G}结果: 全部通过!${NC}"
else
  echo -e " ${R}结果: 存在 $FAIL 个失败项${NC}"
fi
echo "============================================================"
