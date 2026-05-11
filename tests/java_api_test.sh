#!/bin/bash
echo "=== Java 后端 API 端点扫描 ==="
for ep in \
  api/auth/login \
  api/auth/register \
  api/auth/info \
  api/auth/send-code \
  api/monitor/ws \
  api/ws \
  api/user/list \
  api/user/login \
  api/admin/users \
  api/admin/spark-status \
  api/log/list \
  api/system/info \
  actuator/health \
  api/pipeline/create \
  api/pipeline/status; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "http://localhost:8081/$ep" 2>/dev/null)
  echo "  $ep => HTTP $code"
done

echo ""
echo "=== Flask 缺失端点补测 ==="
for ep in \
  "api/weibo/hot" \
  "api/weibo/hotsearch" \
  "api/weibo/hot-topics" \
  "api/weibo/topic" \
  "api/preprocess/clean" \
  "api/preprocess/preview" \
  "api/preprocess/health" \
  "api/preprocess/start" \
  "api/sentiment/analyze" \
  "api/sentiment/bert/info" \
  "api/sentiment/health" \
  "api/sentiment/distribution" \
  "api/sentiment/statistics" \
  "api/sentiment/methods" \
  "api/tri-dimension/analyze" \
  "api/tri-dimension/config" \
  "api/tri-dimension/ranking-from-db" \
  "api/dashboard/overview" \
  "api/dashboard/sentiment-distribution" \
  "api/dashboard/trend" \
  "api/dashboard/realtime" \
  "api/dashboard/hot-topics" \
  "api/dashboard/alerts" \
  "api/dashboard/health" \
  "api/dashboard/spark/status" \
  "api/topics/list" \
  "api/topics/wordcloud" \
  "api/topics/ranked" \
  "api/propagation/network" \
  "api/propagation/influence-ranking" \
  "api/pipeline/status" \
  "api/pipeline/stats" \
  "api/pipeline/ranking" \
  "api/pipeline/history" \
  "api/pipeline/health" \
  "api/auth/health" \
  "api/v2/health" \
  "api/v2/status"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://localhost:5000/$ep" 2>/dev/null)
  echo "  $ep => HTTP $code"
done

echo ""
echo "=== 数据库详细对账 ==="
DB="docker exec weibo_sentiment_db mysql -u weibo_user -p123456 -N weibo_sentiment"
echo "  weibo_core_data:            $($DB -e 'SELECT COUNT(*) FROM weibo_core_data' 2>/dev/null)"
echo "  sentiment_analysis_results: $($DB -e 'SELECT COUNT(*) FROM sentiment_analysis_results' 2>/dev/null)"
echo "  tri_dimension_ranking:      $($DB -e 'SELECT COUNT(*) FROM tri_dimension_ranking' 2>/dev/null)"
echo "  crawl_batch_log:            $($DB -e 'SELECT COUNT(*) FROM crawl_batch_log' 2>/dev/null)"

echo ""
echo "--- 情感分布 ---"
$DB -e "SELECT sentiment_class, COUNT(*) as cnt FROM sentiment_analysis_results GROUP BY sentiment_class" 2>/dev/null

echo ""
echo "--- 排序TOP5 ---"
$DB -e "SELECT weibo_id, composite_score, sentiment_score, popularity_score, ranking_position FROM tri_dimension_ranking ORDER BY ranking_position LIMIT 5" 2>/dev/null

echo ""
echo "--- 批次日志 ---"
$DB -e "SELECT batch_id, status, total_weibos, start_time, end_time FROM crawl_batch_log ORDER BY created_at DESC LIMIT 5" 2>/dev/null

echo ""
echo "=== 前端页面可访问性 ==="
for path in "/" "/collection" "/preprocess" "/sentiment" "/tri-dimension" "/realtime" "/pipeline" "/visualization" "/admin"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "http://localhost:3001$path" 2>/dev/null)
  echo "  $path => HTTP $code"
done
