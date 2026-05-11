#!/bin/bash
API="http://localhost:5000"
echo "=== 情感分析三模式准确率对比 ==="

SAMPLES=(
  "这个产品太棒了质量非常好用着很满意|positive"
  "今天心情特别好一切都很顺利|positive"
  "这家店的服务真的很不错推荐给大家|positive"
  "非常感谢你的帮助让我解决了问题|positive"
  "终于拿到了心仪的offer太开心了|positive"
  "这次旅行体验很好风景也很美|positive"
  "今天收到了朋友送的礼物超级惊喜|positive"
  "公司年终奖发了很多真是太好了|positive"
  "新买的电脑速度飞快运行流畅|positive"
  "考试成绩出来了全部优秀太棒了|positive"
  "服务态度极差再也不来了|negative"
  "这个质量太差了完全是浪费钱|negative"
  "等了两个小时还没上菜差评|negative"
  "物流太慢了而且包装破损严重|negative"
  "售后态度恶劣问题一直没解决|negative"
  "这个电影太难看了浪费时间|negative"
  "价格虚高性价比极低不值得购买|negative"
  "投诉了好几次都没有回复太失望了|negative"
  "呵呵说得好听做得难看|negative"
  "食物不新鲜吃完就拉肚子了|negative"
  "今天天气多云转晴|neutral"
  "明天会议在下午三点开始|neutral"
  "这款手机搭载了骁龙处理器|neutral"
  "官方发布了新版本更新公告|neutral"
  "该项目目前正在推进过程中|neutral"
  "报告已提交给相关部门审核|neutral"
  "北京今天最高气温28度|neutral"
  "新闻发布会定于周五举行|neutral"
  "本次航班预计延误30分钟|neutral"
  "系统将于今晚进行维护升级|neutral"
)

dict_ok=0; bert_ok=0; hybrid_ok=0; total=0
pos_d=0; pos_b=0; pos_h=0; pos_t=0
neg_d=0; neg_b=0; neg_h=0; neg_t=0
neu_d=0; neu_b=0; neu_h=0; neu_t=0

for item in "${SAMPLES[@]}"; do
  text="${item%%|*}"
  expected="${item#*|}"
  
  resp=$(curl -s -X POST -H 'Content-Type: application/json' \
    -d "{\"text\":\"$text\"}" "$API/api/sentiment/analyze" 2>/dev/null)
  
  # Extract scores
  h_score=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['score'])" 2>/dev/null || echo "0")
  d_score=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['details']['lexicon']['score'])" 2>/dev/null || echo "0")
  b_score=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['details']['bert']['score'])" 2>/dev/null || echo "0")
  
  classify() { python3 -c "s=float('$1'); print('positive' if s>0.2 else ('negative' if s<-0.2 else 'neutral'))" 2>/dev/null; }
  
  d_label=$(classify "$d_score")
  b_label=$(classify "$b_score")
  h_label=$(classify "$h_score")
  
  ((total++))
  dv="x"; bv="x"; hv="x"
  if [ "$d_label" = "$expected" ]; then ((dict_ok++)); dv="v"; fi
  if [ "$b_label" = "$expected" ]; then ((bert_ok++)); bv="v"; fi
  if [ "$h_label" = "$expected" ]; then ((hybrid_ok++)); hv="v"; fi
  
  # Per-class
  case "$expected" in
    positive) ((pos_t++)); [ "$dv" = "v" ] && ((pos_d++)); [ "$bv" = "v" ] && ((pos_b++)); [ "$hv" = "v" ] && ((pos_h++));;
    negative) ((neg_t++)); [ "$dv" = "v" ] && ((neg_d++)); [ "$bv" = "v" ] && ((neg_b++)); [ "$hv" = "v" ] && ((neg_h++));;
    neutral)  ((neu_t++)); [ "$dv" = "v" ] && ((neu_d++)); [ "$bv" = "v" ] && ((neu_b++)); [ "$hv" = "v" ] && ((neu_h++));;
  esac
  
  printf "  %-9s d=%-7s(%s) b=%-7s(%s) h=%-7s(%s) \"%s\"\n" \
    "[$expected]" "$d_score" "$dv" "$b_score" "$bv" "$h_score" "$hv" "${text:0:22}"
done

echo ""
echo "=========================================="
echo " 总体准确率 (30样本)"
echo "=========================================="
echo "  词典模式:     $dict_ok/$total = $(python3 -c "print(f'{$dict_ok/$total*100:.1f}')")%"
echo "  BERT模式:     $bert_ok/$total = $(python3 -c "print(f'{$bert_ok/$total*100:.1f}')")%"
echo "  混合模式:     $hybrid_ok/$total = $(python3 -c "print(f'{$hybrid_ok/$total*100:.1f}')")%"

echo ""
echo "=========================================="
echo " 分类别准确率"
echo "=========================================="
echo "         正面(${pos_t}条)  负面(${neg_t}条)  中性(${neu_t}条)"
echo "  词典:  $pos_d/${pos_t}        $neg_d/${neg_t}        $neu_d/${neu_t}"
echo "  BERT:  $pos_b/${pos_t}        $neg_b/${neg_t}        $neu_b/${neu_t}"
echo "  混合:  $pos_h/${pos_t}        $neg_h/${neg_t}        $neu_h/${neu_t}"

# 计算P/R/F1
echo ""
echo "=========================================="
echo " 混合模式详细指标 (按类别)"
echo "=========================================="
python3 << PYEOF
pos_h=$pos_h; pos_t=$pos_t
neg_h=$neg_h; neg_t=$neg_t
neu_h=$neu_h; neu_t=$neu_t
total=$total; hybrid_ok=$hybrid_ok

# Precision = TP / (TP + FP), Recall = TP / (TP + FN)
# For simplicity, Recall = correct/total_of_that_class
print(f"  正面 - 召回率: {pos_h}/{pos_t} = {pos_h/pos_t*100:.1f}%")
print(f"  负面 - 召回率: {neg_h}/{neg_t} = {neg_h/neg_t*100:.1f}%")
print(f"  中性 - 召回率: {neu_h}/{neu_t} = {neu_h/neu_t*100:.1f}%")
acc = hybrid_ok/total
print(f"  总体准确率: {acc*100:.1f}%")
PYEOF
