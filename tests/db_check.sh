#!/bin/bash
DB_CMD="docker exec weibo_sentiment_db mysql -u weibo_user -p123456 -N weibo_sentiment"

echo "=== 微博总数 ==="
$DB_CMD -e "SELECT COUNT(*) FROM weibo_core_data" 2>/dev/null

echo "=== 重复数 ==="
$DB_CMD -e "SELECT COUNT(*) - COUNT(DISTINCT weibo_id) FROM weibo_core_data" 2>/dev/null

echo "=== 字段空值检查 ==="
$DB_CMD -e "SELECT SUM(CASE WHEN weibo_id IS NULL THEN 1 ELSE 0 END) as null_id, SUM(CASE WHEN content IS NULL OR content='' THEN 1 ELSE 0 END) as null_content, SUM(CASE WHEN created_at IS NULL THEN 1 ELSE 0 END) as null_time, SUM(CASE WHEN reposts_count IS NULL THEN 1 ELSE 0 END) as null_reposts FROM weibo_core_data" 2>/dev/null

echo "=== 情感分布 ==="
$DB_CMD -e "SELECT sentiment_class, COUNT(*) as cnt FROM sentiment_analysis_results GROUP BY sentiment_class ORDER BY cnt DESC" 2>/dev/null

echo "=== 情感结果总数 ==="
$DB_CMD -e "SELECT COUNT(*) FROM sentiment_analysis_results" 2>/dev/null

echo "=== 排序总数 ==="
$DB_CMD -e "SELECT COUNT(*) FROM tri_dimension_ranking" 2>/dev/null

echo "=== 批次 ==="
$DB_CMD -e "SELECT batch_id, status, total_weibos, start_time, end_time FROM crawl_batch_log ORDER BY created_at DESC" 2>/dev/null

echo "=== 排序TOP5 ==="
$DB_CMD -e "SELECT ranking_position, ROUND(composite_score,4), ROUND(sentiment_score,4), ROUND(popularity_score,4), ROUND(time_decay,4) FROM tri_dimension_ranking ORDER BY ranking_position LIMIT 5" 2>/dev/null

echo "=== 展示API响应 ==="
for ep in "dashboard/sentiment-distribution" "dashboard/trend" "dashboard/overview" "dashboard/hot-topics" "topics/wordcloud" "pipeline/ranking?limit=20"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://localhost:5000/api/$ep" 2>/dev/null)
  echo "  /api/$ep => $code"
done
