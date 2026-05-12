"""
30 条人工标注情感测试 - 通过部署的 /api/sentiment/analyze 接口
正/负/中各 10 条, 分别用 lexicon / bert / cascade(θ=0.7) 三模式调用,
聚合准确率与各类召回率, 输出 markdown 表。

用法 (容器宿主机):
    python3 manual_30_test.py --url http://localhost:5000

结果同时保存 JSON 到 manual_30_test_results.json。
"""
import argparse
import json
import sys
import time
from collections import Counter
from typing import List, Dict

try:
    import requests
except ImportError:
    print("pip install requests first", file=sys.stderr)
    sys.exit(1)


# ======================== 30 条人工标注样本 ========================
SAMPLES: List[Dict] = [
    # ---------- 正面 10 ----------
    {"text": "这个产品太棒了,质量非常好,用着很满意", "label": "positive"},
    {"text": "客服小姐姐态度超级好,问题秒解决,五星好评", "label": "positive"},
    {"text": "演唱会现场氛围炸裂,期待已久终于圆梦了,泪目", "label": "positive"},
    {"text": "新出的相机拍人像太顶了,色彩通透,买它不亏", "label": "positive"},
    {"text": "国产新能源车真争气,续航和智能驾驶都越来越强", "label": "positive"},
    {"text": "今天面试通过啦,薪资比预期还高,开心到飞起", "label": "positive"},
    {"text": "这家小店的牛肉面太香了,汤底浓郁,以后常来", "label": "positive"},
    {"text": "团队加班三个月终于上线了,看着用户数据涨好有成就感", "label": "positive"},
    {"text": "孩子拿了钢琴比赛一等奖,练琴的辛苦都值了", "label": "positive"},
    {"text": "周末爬山看日出真是治愈,身心舒畅,推荐", "label": "positive"},
    # ---------- 负面 10 ----------
    {"text": "服务态度极差,再也不来了", "label": "negative"},
    {"text": "物流太慢了,而且包装破损严重,非常失望", "label": "negative"},
    {"text": "客服推诿扯皮,问题拖了一周还没解决,差评", "label": "negative"},
    {"text": "新买的手机用了三天就死机,这质量真烂", "label": "negative"},
    {"text": "演员演技尴尬剧情拖沓,简直是浪费时间", "label": "negative"},
    {"text": "高速堵了四个小时,服务区还又脏又乱,糟糕透顶", "label": "negative"},
    {"text": "这家餐厅菜里居然吃出虫子,卫生太差恶心想吐", "label": "negative"},
    {"text": "公司年终奖缩水一半,管理层还在画饼,心寒", "label": "negative"},
    {"text": "孩子在学校被霸凌老师不作为,真让人气愤", "label": "negative"},
    {"text": "暴雨导致小区停电停水两天,物业完全失联,太离谱", "label": "negative"},
    # ---------- 中性 10 ----------
    {"text": "今天天气多云转晴,气温18到26度", "label": "neutral"},
    {"text": "官方发布了新版本更新公告,涉及若干功能调整", "label": "neutral"},
    {"text": "国家统计局公布上月CPI同比上涨0.3%", "label": "neutral"},
    {"text": "据报道,该公司将在下周召开股东大会", "label": "neutral"},
    {"text": "教育部表示将进一步推进义务教育阶段课程改革", "label": "neutral"},
    {"text": "上海地铁11号线明日起延长运营时间至23点", "label": "neutral"},
    {"text": "今年高考报名人数较去年小幅增加", "label": "neutral"},
    {"text": "央行公开市场操作开展逆回购1000亿元", "label": "neutral"},
    {"text": "记者从相关部门获悉,该项目目前处于评审阶段", "label": "neutral"},
    {"text": "本周末多地有降雨,公众出行请关注天气预报", "label": "neutral"},
]


METHODS = [
    ("lexicon", "词典模式"),
    ("bert", "BERT模式"),
    ("cascade", "级联融合(θ=0.7)"),
]

LABEL_CN = {"positive": "正面", "negative": "负面", "neutral": "中性"}


def call_api(url: str, text: str, method: str, theta: float = 0.7) -> Dict:
    payload = {"text": text, "method": method}
    if method == "cascade":
        payload["theta"] = theta
    try:
        r = requests.post(f"{url}/api/sentiment/analyze",
                          json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def extract(resp: Dict) -> Dict:
    """规范化提取 sentiment / confidence / method_used / score。"""
    if not resp or "error" in resp:
        return {"sentiment": None, "confidence": None, "raw": resp}
    # 兼容两种返回结构: 顶层或 data 包裹
    body = resp.get("data", resp)
    sent = (body.get("sentiment") or body.get("label")
            or body.get("category") or body.get("predicted"))
    if isinstance(sent, str):
        sent_l = sent.lower()
        if sent_l in ("pos", "positive", "正面", "1"):
            sent_norm = "positive"
        elif sent_l in ("neg", "negative", "负面", "-1"):
            sent_norm = "negative"
        elif sent_l in ("neu", "neutral", "中性", "0"):
            sent_norm = "neutral"
        else:
            sent_norm = sent
    else:
        sent_norm = None
    return {
        "sentiment": sent_norm,
        "confidence": body.get("confidence"),
        "score": body.get("score") or body.get("polarity_score"),
        "method_used": body.get("method") or body.get("method_used"),
        "raw": body,
    }


def aggregate(results: List[Dict], method_key: str) -> Dict:
    total = len(results)
    correct = 0
    per_class_total = Counter()
    per_class_correct = Counter()
    for r in results:
        gold = r["label"]
        pred = r[method_key]["sentiment"]
        per_class_total[gold] += 1
        if pred == gold:
            correct += 1
            per_class_correct[gold] += 1
    recall = {c: (per_class_correct[c] / per_class_total[c] if per_class_total[c] else 0.0)
              for c in ("positive", "negative", "neutral")}
    return {
        "accuracy": correct / total,
        "correct": correct,
        "total": total,
        "recall": recall,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:5000")
    ap.add_argument("--out", default="manual_30_test_results.json")
    ap.add_argument("--theta", type=float, default=0.7)
    args = ap.parse_args()

    print(f"[INFO] API base = {args.url}, samples = {len(SAMPLES)}")
    results = []
    t0 = time.time()
    for i, s in enumerate(SAMPLES, 1):
        row = {"idx": i, "text": s["text"], "label": s["label"]}
        for m, _ in METHODS:
            resp = call_api(args.url, s["text"], m, args.theta)
            row[m] = extract(resp)
            print(f"  [{i:02d}/{len(SAMPLES)}] {m:<8} gold={s['label']:<8} "
                  f"pred={row[m]['sentiment']} conf={row[m]['confidence']}")
        results.append(row)
    elapsed = time.time() - t0
    print(f"[INFO] done in {elapsed:.1f}s")

    summary = {m: aggregate(results, m) for m, _ in METHODS}

    # ---------- 输出 Markdown 表 ----------
    md = []
    md.append("## 表 7-2 情感分析功能测试用例(30 条全量)\n")
    md.append("| # | 测试文本 | 标注 | 词典判定 | BERT判定 | 级联判定 |")
    md.append("|---|---|---|---|---|---|")
    for r in results:
        def mark(m):
            p = r[m]["sentiment"]
            ok = "✓" if p == r["label"] else "✗"
            return f"{LABEL_CN.get(p, p) or '-'}{ok}"
        md.append(f"| {r['idx']} | {r['text']} | {LABEL_CN[r['label']]} | "
                  f"{mark('lexicon')} | {mark('bert')} | {mark('cascade')} |")

    md.append("\n## 表 7-3 三种模式准确率对比\n")
    md.append("| 测试模式 | 总体准确率 | 正面召回 | 负面召回 | 中性召回 |")
    md.append("|---|---|---|---|---|")
    for m, label in METHODS:
        s = summary[m]
        md.append(f"| {label} | {s['accuracy']*100:.1f}% ({s['correct']}/{s['total']}) | "
                  f"{s['recall']['positive']*100:.1f}% ({int(s['recall']['positive']*10)}/10) | "
                  f"{s['recall']['negative']*100:.1f}% ({int(s['recall']['negative']*10)}/10) | "
                  f"{s['recall']['neutral']*100:.1f}% ({int(s['recall']['neutral']*10)}/10) |")
    md_text = "\n".join(md)
    print("\n" + md_text)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"results": results, "summary": summary,
                   "elapsed_sec": elapsed}, f, ensure_ascii=False, indent=2)
    with open(args.out.replace(".json", ".md"), "w", encoding="utf-8") as f:
        f.write(md_text)
    print(f"\n[INFO] saved: {args.out} and .md")


if __name__ == "__main__":
    main()
