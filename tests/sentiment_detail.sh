#!/bin/bash
# 查看情感分析API完整响应
echo "=== 正面文本 ==="
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"text":"这个产品太棒了非常满意质量很好"}' \
  http://localhost:5000/api/sentiment/analyze 2>/dev/null | python3 -m json.tool

echo ""
echo "=== 负面文本 ==="
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"text":"服务态度极差再也不来了太差了"}' \
  http://localhost:5000/api/sentiment/analyze 2>/dev/null | python3 -m json.tool

echo ""
echo "=== 中性文本 ==="
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"text":"今天天气多云转晴温度适宜"}' \
  http://localhost:5000/api/sentiment/analyze 2>/dev/null | python3 -m json.tool
