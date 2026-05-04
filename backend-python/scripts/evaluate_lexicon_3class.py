#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯词典方法 (analyze_3class) 三分类评估
=====================================

在与级联评估相同的 10,000 条测试集 (test_set_200.csv) 上,
直接使用 SentimentLexicon.analyze_3class() 的判定结果作为最终预测
(忽略 high_confidence 标志, 低置信样本也采用词典的 tentative 预测)。

输出:
  - 各类别 Precision / Recall / F1
  - Overall Accuracy 和 Macro F1
  - 3x3 混淆矩阵
  - 高/低置信样本分布

用法:
  cd backend-python
  python scripts/evaluate_lexicon_3class.py
"""

import sys
import time
import json
from pathlib import Path
from collections import Counter

import pandas as pd
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from spark.sentiment_analyzer import SentimentLexicon

TEST_SET_PATH = BACKEND_DIR / 'data' / 'test_set_200.csv'
LABEL_CN = {0: '负面', 1: '正面', 2: '中性'}


def load_test_set() -> pd.DataFrame:
    df = pd.read_csv(str(TEST_SET_PATH))
    df = df.dropna(subset=['review', 'label'])
    df = df[df['label'].isin([0, 1, 2])]
    df['review'] = df['review'].astype(str)
    return df


def compute_metrics(y_true, y_pred, classes=(0, 1, 2)):
    n = len(y_true)
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / n if n else 0

    precision, recall, f1 = {}, {}, {}
    for c in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == c and p == c)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != c and p == c)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == c and p != c)

        p_val = tp / (tp + fp) if (tp + fp) > 0 else 0
        r_val = tp / (tp + fn) if (tp + fn) > 0 else 0
        f_val = 2 * p_val * r_val / (p_val + r_val) if (p_val + r_val) > 0 else 0

        name = LABEL_CN[c]
        precision[name] = p_val
        recall[name] = r_val
        f1[name] = f_val

    macro_p = float(np.mean(list(precision.values())))
    macro_r = float(np.mean(list(recall.values())))
    macro_f1 = float(np.mean(list(f1.values())))

    cm = [[0] * len(classes) for _ in classes]
    for t, p in zip(y_true, y_pred):
        if t in classes and p in classes:
            cm[list(classes).index(t)][list(classes).index(p)] += 1

    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'macro_precision': macro_p,
        'macro_recall': macro_r,
        'macro_f1': macro_f1,
        'confusion_matrix': cm,
        'total': n,
        'correct': correct,
    }


def main():
    df = load_test_set()
    total = len(df)
    print(f'测试集: {total} 条  ', end='')
    for c in [0, 1, 2]:
        print(f'{LABEL_CN[c]}={int((df["label"] == c).sum())}  ', end='')
    print()

    y_true = df['label'].tolist()
    texts = df['review'].tolist()

    y_pred = []
    high_conf_flags = []
    times = []

    t_start = time.perf_counter()
    for text in texts:
        t0 = time.perf_counter()
        label, conf, high_conf = SentimentLexicon.analyze_3class(text)
        times.append((time.perf_counter() - t0) * 1000)
        y_pred.append(label)
        high_conf_flags.append(high_conf)
    total_elapsed = time.perf_counter() - t_start

    m = compute_metrics(y_true, y_pred)

    # 报告
    print()
    print('=' * 68)
    print('   纯词典方法 (analyze_3class) 三分类评估报告')
    print('=' * 68)
    print(f'\nOverall Accuracy: {m["accuracy"]:.4f}  ({m["accuracy"]:.2%})')
    print(f'Macro Precision:  {m["macro_precision"]:.4f}')
    print(f'Macro Recall:     {m["macro_recall"]:.4f}')
    print(f'Macro F1:         {m["macro_f1"]:.4f}')
    print(f'总耗时:           {total_elapsed:.2f} s')
    print(f'平均延迟:          {np.mean(times):.3f} ms/条')

    print(f'\n各类别指标:')
    print(f'  {"类别":<6} {"Precision":>12} {"Recall":>12} {"F1":>12} {"Support":>10}')
    print(f'  {"-" * 54}')
    for c in [0, 1, 2]:
        name = LABEL_CN[c]
        support = int((df['label'] == c).sum())
        print(f'  {name:<6} {m["precision"][name]:>12.4f} '
              f'{m["recall"][name]:>12.4f} {m["f1"][name]:>12.4f} {support:>10}')
    print(f'  {"-" * 54}')
    print(f'  {"Macro":<6} {m["macro_precision"]:>12.4f} '
          f'{m["macro_recall"]:>12.4f} {m["macro_f1"]:>12.4f} {total:>10}')

    print(f'\n混淆矩阵 (行=真实, 列=预测):')
    print(f'  {"":>8} {"负面":>8} {"正面":>8} {"中性":>8}')
    for i, row_name in enumerate(['负面', '正面', '中性']):
        row = m['confusion_matrix'][i]
        print(f'  {row_name:>8} {row[0]:>8} {row[1]:>8} {row[2]:>8}')

    # 高/低置信分布
    hi = sum(1 for x in high_conf_flags if x)
    lo = total - hi
    hi_correct = sum(1 for t, p, h in zip(y_true, y_pred, high_conf_flags) if h and t == p)
    lo_correct = sum(1 for t, p, h in zip(y_true, y_pred, high_conf_flags) if not h and t == p)
    hi_acc = hi_correct / hi if hi else 0
    lo_acc = lo_correct / lo if lo else 0

    print(f'\n高/低置信分布 (词典内部判断):')
    print(f'  高置信 (high_confidence=True): {hi:>5} 条 ({hi/total:.1%}) 准确率={hi_acc:.4f}')
    print(f'  低置信 (high_confidence=False): {lo:>5} 条 ({lo/total:.1%}) 准确率={lo_acc:.4f}')

    print()
    print('=' * 68)
    print(f'  纯词典 Accuracy = {m["accuracy"]:.2%} | Macro F1 = {m["macro_f1"]:.4f}')
    print('=' * 68)

    # 保存 JSON
    out = BACKEND_DIR / 'scripts' / 'evaluate_lexicon_3class_results.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({
            **m,
            'total_time_s': total_elapsed,
            'avg_time_ms': float(np.mean(times)),
            'high_confidence_samples': hi,
            'high_confidence_ratio': hi / total,
            'high_confidence_accuracy': hi_acc,
            'low_confidence_samples': lo,
            'low_confidence_accuracy': lo_acc,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        }, f, ensure_ascii=False, indent=2)
    print(f'\n结果已保存: {out}')


if __name__ == '__main__':
    main()
