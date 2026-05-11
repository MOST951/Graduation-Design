#!/bin/bash
DB="docker exec weibo_sentiment_db mysql -u weibo_user -p123456 weibo_sentiment"

echo "=== 1. 查找孤儿情感记录 ==="
$DB -N -e "
SELECT s.id, s.weibo_id
FROM sentiment_analysis_results s
LEFT JOIN weibo_core_data w ON s.weibo_id = w.weibo_id
WHERE w.weibo_id IS NULL
" 2>/dev/null

echo "=== 孤儿数量 ==="
$DB -N -e "
SELECT COUNT(*)
FROM sentiment_analysis_results s
LEFT JOIN weibo_core_data w ON s.weibo_id = w.weibo_id
WHERE w.weibo_id IS NULL
" 2>/dev/null

echo "=== 2. 查找孤儿排序记录 ==="
$DB -N -e "
SELECT COUNT(*)
FROM tri_dimension_ranking r
LEFT JOIN weibo_core_data w ON r.weibo_id = w.weibo_id
WHERE w.weibo_id IS NULL
" 2>/dev/null

echo "=== 3. 各表数据量 ==="
$DB -N -e "SELECT 'weibo_core_data', COUNT(*) FROM weibo_core_data
UNION ALL SELECT 'sentiment_analysis_results', COUNT(*) FROM sentiment_analysis_results
UNION ALL SELECT 'tri_dimension_ranking', COUNT(*) FROM tri_dimension_ranking
UNION ALL SELECT 'crawl_batch_log', COUNT(*) FROM crawl_batch_log" 2>/dev/null

echo "=== 4. 清理孤儿记录 ==="
echo "--- 删除孤儿排序记录 ---"
$DB -e "
DELETE r FROM tri_dimension_ranking r
LEFT JOIN weibo_core_data w ON r.weibo_id = w.weibo_id
WHERE w.weibo_id IS NULL
" 2>/dev/null
echo "affected: $?"

echo "--- 删除孤儿情感记录 ---"
$DB -e "
DELETE s FROM sentiment_analysis_results s
LEFT JOIN weibo_core_data w ON s.weibo_id = w.weibo_id
WHERE w.weibo_id IS NULL
" 2>/dev/null
echo "affected: $?"

echo "=== 5. 清理后数据量 ==="
$DB -N -e "SELECT 'weibo_core_data', COUNT(*) FROM weibo_core_data
UNION ALL SELECT 'sentiment_analysis_results', COUNT(*) FROM sentiment_analysis_results
UNION ALL SELECT 'tri_dimension_ranking', COUNT(*) FROM tri_dimension_ranking" 2>/dev/null
