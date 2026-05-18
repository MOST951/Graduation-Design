#!/bin/bash
API="http://localhost:5000"
JAVA="http://localhost:8081"

echo "============================================================"
echo " 补充测试：并发/边界/容错"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"

# ============================================================
# 1. 边界条件测试
# ============================================================
echo ""
echo "========================================"
echo " 1. 数据边界值测试"
echo "========================================"

echo "--- 1.1 空文本情感分析 ---"
r=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"text":""}' "$API/api/sentiment/analyze" 2>/dev/null)
code=$(echo "$r" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code','?'))" 2>/dev/null)
echo "  空文本 => code=$code (预期: 400或有默认处理)"

echo "--- 1.2 纯表情文本 ---"
r=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"text":"[微笑][微笑][鲜花]"}' "$API/api/sentiment/analyze" 2>/dev/null)
score=$(echo "$r" | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(d.get('score','?'))" 2>/dev/null)
echo "  纯表情 => score=$score (预期: 正常返回)"

echo "--- 1.3 超长文本(2000字) ---"
long_text=$(python3 -c "print('测试文本' * 500)")
r=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d "{\"text\":\"$long_text\"}" "$API/api/sentiment/analyze" 2>/dev/null)
code=$(echo "$r" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code','?'))" 2>/dev/null)
echo "  超长文本(2000字) => code=$code (预期: 200截断处理或正常)"

echo "--- 1.4 特殊字符文本 ---"
r=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"text":"<script>alert(1)</script> & \u0000 \" 测试"}' "$API/api/sentiment/analyze" 2>/dev/null)
code=$(echo "$r" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code','?'))" 2>/dev/null)
echo "  特殊字符/XSS => code=$code (预期: 安全处理)"

echo "--- 1.5 空关键词采集(已修复) ---"
r=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"keywords":[],"crawl_hot":false}' "$API/api/weibo/collect" 2>/dev/null)
code=$(echo "$r" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code','?'))" 2>/dev/null)
echo "  空关键词 => code=$code (预期: 400)"

echo "--- 1.6 非数组关键词 ---"
r=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"keywords":"string_not_array"}' "$API/api/weibo/collect" 2>/dev/null)
code=$(echo "$r" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code','?'))" 2>/dev/null)
echo "  非数组关键词 => code=$code (预期: 400)"

echo "--- 1.7 极端情感得分文本 ---"
r1=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"text":"太棒了太棒了太棒了好好好好好好好好好好"}' "$API/api/sentiment/analyze" 2>/dev/null)
s1=$(echo "$r1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('score','?'))" 2>/dev/null)
r2=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"text":"太差了太差了太差了差差差差差差差差差差"}' "$API/api/sentiment/analyze" 2>/dev/null)
s2=$(echo "$r2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('score','?'))" 2>/dev/null)
echo "  极端正面 => score=$s1 (预期: 接近1.0)"
echo "  极端负面 => score=$s2 (预期: 接近-1.0)"

# ============================================================
# 2. 并发场景测试
# ============================================================
echo ""
echo "========================================"
echo " 2. 并发场景测试"
echo "========================================"

echo "--- 2.1 并发情感分析(5个同时) ---"
t_start=$(date +%s%3N)
for i in $(seq 1 5); do
  curl -s -X POST -H 'Content-Type: application/json' \
    -d "{\"text\":\"并发测试文本第${i}条\"}" \
    "$API/api/sentiment/analyze" > /tmp/conc_$i.json 2>/dev/null &
done
wait
t_end=$(date +%s%3N)
all_ok=true
for i in $(seq 1 5); do
  c=$(python3 -c "import json; print(json.load(open('/tmp/conc_$i.json')).get('code','?'))" 2>/dev/null)
  if [ "$c" != "200" ]; then all_ok=false; fi
done
echo "  5路并发情感分析 => 全部200: $all_ok, 总耗时: $((t_end - t_start))ms"

echo "--- 2.2 并发API访问(10个Dashboard) ---"
t_start=$(date +%s%3N)
for i in $(seq 1 10); do
  curl -s -o /dev/null -w '' "$API/api/dashboard/overview" 2>/dev/null &
done
wait
t_end=$(date +%s%3N)
echo "  10路并发Dashboard => 总耗时: $((t_end - t_start))ms"

echo "--- 2.3 快速连续请求(20个) ---"
ok=0; fail=0
for i in $(seq 1 20); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$API/api/dashboard/overview" 2>/dev/null)
  if [ "$code" = "200" ]; then ((ok++)); else ((fail++)); fi
done
echo "  20次快速请求 => 成功: $ok, 失败: $fail"

# ============================================================
# 3. 容错能力测试
# ============================================================
echo ""
echo "========================================"
echo " 3. 容错能力测试"
echo "========================================"

echo "--- 3.1 Flask重启恢复 ---"
docker restart weibo_web > /dev/null 2>&1
sleep 8
r=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$API/api/v2/health" 2>/dev/null)
echo "  Flask重启后API响应 => $r (预期: 200)"

echo "--- 3.2 无效API路径 ---"
r=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$API/api/nonexistent/endpoint" 2>/dev/null)
echo "  无效路径 => $r (预期: 404)"

echo "--- 3.3 无效JSON请求体 ---"
r=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d 'invalid json{{{' "$API/api/sentiment/analyze" 2>/dev/null)
code=$(echo "$r" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code','?'))" 2>/dev/null)
echo "  无效JSON => code=$code (预期: 400或500, 不崩溃)"

echo "--- 3.4 缺少必填字段 ---"
r=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d '{}' "$API/api/sentiment/analyze" 2>/dev/null)
code=$(echo "$r" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code','?'))" 2>/dev/null)
echo "  缺少text字段 => code=$code (预期: 400)"

echo "--- 3.5 服务健康状态汇总 ---"
for c in weibo_web weibo_db weibo_frontend weibo_namenode weibo_spark_master; do
  s=$(docker inspect --format='{{.State.Status}}' $c 2>/dev/null)
  h=$(docker inspect --format='{{.State.Health.Status}}' $c 2>/dev/null || echo "N/A")
  echo "  $c => status=$s health=$h"
done

echo ""
echo "============================================================"
echo " 补充测试完成"
echo "============================================================"
