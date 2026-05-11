#!/bin/bash
API="http://localhost:5000"

echo "=== 情感分析准确率测试 ==="

# 测试样本: text|expected_label
SAMPLES=(
  "这个产品太棒了，质量非常好，用着很满意！|positive"
  "今天心情特别好，一切都很顺利！|positive"
  "这家店的服务真的很不错推荐给大家|positive"
  "非常感谢你的帮助让我解决了问题|positive"
  "终于拿到了心仪的offer太开心了|positive"
  "这次旅行体验很好风景也很美|positive"
  "今天收到了朋友送的礼物超级惊喜|positive"
  "服务态度极差再也不来了|negative"
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
  "呵呵说得好听做得难看|negative"
)

dict_correct=0
hybrid_correct=0
total=0

for item in "${SAMPLES[@]}"; do
  text="${item%%|*}"
  expected="${item#*|}"
  
  resp=$(curl -s -X POST -H 'Content-Type: application/json' \
    -d "{\"text\":\"$text\"}" \
    "$API/api/sentiment/analyze" 2>/dev/null)
  
  h_score=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(d.get('score', d.get('hybrid_score', d.get('sentiment_score',0))))" 2>/dev/null || echo "0")
  d_score=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(d.get('dict_score',0))" 2>/dev/null || echo "0")
  method=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(d.get('method', d.get('analysis_method','')))" 2>/dev/null || echo "?")
  
  # 混合标签
  h_label=$(python3 -c "s=float('$h_score'); print('positive' if s>0.2 else ('negative' if s<-0.2 else 'neutral'))" 2>/dev/null)
  # 词典标签
  d_label=$(python3 -c "s=float('${d_score}'); print('positive' if s>0.2 else ('negative' if s<-0.2 else 'neutral'))" 2>/dev/null)
  
  ((total++))
  h_ok="x"; d_ok="x"
  if [ "$h_label" = "$expected" ]; then ((hybrid_correct++)); h_ok="v"; fi
  if [ "$d_label" = "$expected" ]; then ((dict_correct++)); d_ok="v"; fi
  
  printf "  [%s] %-8s h=%-8s(%-8s %s) d=%-8s(%-8s %s) m=%-6s \"%s\"\n" \
    "$expected" "" "$h_score" "$h_label" "$h_ok" "$d_score" "$d_label" "$d_ok" "$method" "${text:0:25}"
done

echo ""
echo "  总样本: $total"
echo "  词典模式: $dict_correct/$total = $(python3 -c "print(f'{$dict_correct/$total*100:.1f}')")%"
echo "  混合模式: $hybrid_correct/$total = $(python3 -c "print(f'{$hybrid_correct/$total*100:.1f}')")%"

# 按类别统计
echo ""
echo "=== 按类别准确率 ==="
# 正面
pos_total=7; pos_h=0; pos_d=0
neg_total=7; neg_h=0; neg_d=0
neu_total=6; neu_h=0; neu_d=0
# Re-count from results above would be complex, so let me just show totals
echo "(详细per-class统计见上方每行结果)"
