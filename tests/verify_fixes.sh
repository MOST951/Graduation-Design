#!/bin/bash
echo "=== Waiting for Java backend ==="
for i in $(seq 1 12); do
  sleep 10
  h=$(docker inspect --format='{{.State.Health.Status}}' weibo_sentiment_java 2>/dev/null || echo 'starting')
  echo "  [$i] status=$h"
  if [ "$h" = "healthy" ]; then break; fi
done

echo ""
echo "=== P0: Java backend endpoint verification ==="
for ep in \
  "api/auth/health" \
  "api/auth/login" \
  "api/admin/users" \
  "api/admin/logs" \
  "api/admin/system-info" \
  "api/admin/spark-status" \
  "api/admin/clear-cache" \
  "api/actuator/health" \
  "api/actuator/info" \
  "api/actuator/metrics" \
  "api/dashboard/summary" \
  "api/dashboard/alerts" \
  "api/dashboard/metrics" \
  "api/analysis/results/1" \
  "api/collection/tasks"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://localhost:8081/$ep" 2>/dev/null)
  echo "  /$ep => $code"
done

echo ""
echo "=== P0: Java admin/users full response ==="
curl -s http://localhost:8081/api/admin/users 2>/dev/null | python3 -m json.tool 2>/dev/null | head -20

echo ""
echo "=== P0: Java admin/system-info response ==="
curl -s http://localhost:8081/api/admin/system-info 2>/dev/null | python3 -m json.tool 2>/dev/null | head -25

echo ""
echo "=== P0: Java actuator/health response ==="
curl -s http://localhost:8081/api/actuator/health 2>/dev/null | python3 -m json.tool 2>/dev/null | head -25

echo ""
echo "=== P1: Flask empty keyword validation ==="
resp=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"keywords":[],"crawl_hot":false}' \
  http://localhost:5000/api/weibo/collect 2>/dev/null)
echo "  Empty keywords+no hot: $resp"

resp2=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"keywords":["","  "],"crawl_hot":false}' \
  http://localhost:5000/api/weibo/collect 2>/dev/null)
echo "  Whitespace keywords: $resp2"

resp3=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"keywords":"not_array"}' \
  http://localhost:5000/api/weibo/collect 2>/dev/null)
echo "  Non-array keywords: $resp3"

echo ""
echo "=== P0: Flask JWT auth middleware ==="
resp4=$(curl -s http://localhost:5000/api/sentiment/analyze -X POST \
  -H 'Content-Type: application/json' \
  -d '{"text":"测试文本"}' 2>/dev/null)
echo "  No token (should still work with optional_token): $(echo $resp4 | python3 -c 'import sys,json; print(json.load(sys.stdin).get("code","?"))' 2>/dev/null)"

echo ""
echo "=== Container health ==="
for c in weibo_sentiment_java weibo_sentiment_web weibo_sentiment_frontend weibo_sentiment_db weibo_sentiment_redis; do
  h=$(docker inspect --format='{{.State.Health.Status}}' $c 2>/dev/null || echo "no-health")
  s=$(docker inspect --format='{{.State.Status}}' $c 2>/dev/null || echo "?")
  echo "  $c: status=$s health=$h"
done

echo ""
echo "=== WebSocket test ==="
timeout 3 curl -s -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  -H "Sec-WebSocket-Version: 13" \
  http://localhost:8081/api/ws/alerts 2>/dev/null | head -5
echo "(WebSocket upgrade response above)"

echo ""
echo "=== Java endpoint coverage summary ==="
total=0
ok=0
for ep in \
  "api/auth/health" "api/auth/login" "api/auth/register" "api/auth/info" \
  "api/admin/users" "api/admin/logs" "api/admin/system-info" "api/admin/spark-status" \
  "api/actuator/health" "api/actuator/info" "api/actuator/metrics" \
  "api/dashboard/summary" "api/dashboard/alerts" "api/dashboard/metrics" "api/dashboard/charts"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://localhost:8081/$ep" 2>/dev/null)
  ((total++))
  if [ "$code" != "000" ] && [ "$code" != "404" ]; then
    ((ok++))
  fi
done
echo "  Reachable: $ok/$total"
pct=$(python3 -c "print(f'{$ok/$total*100:.1f}')" 2>/dev/null)
echo "  Coverage: ${pct}%"
