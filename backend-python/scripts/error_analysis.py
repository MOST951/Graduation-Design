#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BERT 错误分析
============

在 10,000 条测试集上统计 ChineseBERT 的错误样本:
  - 按真实类别分组的错误率
  - 误分方向分布 (混淆矩阵)
  - 错误样本的文本长度分布
  - 错误样本的 BERT 置信度分布
  - 典型错误样本采样

用法:
  cd backend-python
  python scripts/error_analysis.py
"""

import sys
import time
import json
from pathlib import Path
from collections import Counter, defaultdict

import pandas as pd
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from models.chinese_bert_sentiment import ChineseBertSentimentModel

LABEL_CN = {0: '负面', 1: '正面', 2: '中性'}
TEST_SET_PATH = BACKEND_DIR / 'data' / 'test_set_200.csv'


def main():
    df = pd.read_csv(str(TEST_SET_PATH))
    df = df.dropna(subset=['review', 'label'])
    df = df[df['label'].isin([0, 1, 2])]
    df['review'] = df['review'].astype(str)
    print(f'加载测试集: {len(df)} 条')

    # 初始化模型
    model = ChineseBertSentimentModel()
    model._init_model()
    print('BERT 模型已加载')

    # 批量预测 (利用 predict 的批处理)
    texts = df['review'].tolist()
    y_true = df['label'].tolist()

    print('开始批量预测 ...')
    t0 = time.perf_counter()
    # 分批以避免 OOM
    BATCH = 64
    all_results = []
    for i in range(0, len(texts), BATCH):
        batch = texts[i:i+BATCH]
        all_results.extend(model.predict(batch, return_probs=True))
        if (i // BATCH) % 20 == 0:
            print(f'  {i+len(batch)}/{len(texts)}')
    elapsed = time.perf_counter() - t0
    print(f'预测完成, 总耗时 {elapsed:.1f}s ({elapsed/len(texts)*1000:.2f} ms/条)')

    y_pred = [r['label_id'] for r in all_results]
    confidences = [r['confidence'] for r in all_results]
    probs_list = [r['probabilities'] for r in all_results]

    # ==================== 1. 总体指标 ====================
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    acc = correct / len(y_true)
    n_err = len(y_true) - correct

    print()
    print('=' * 68)
    print('   BERT 错误分析报告')
    print('=' * 68)
    print(f'\n总样本: {len(y_true)}  正确: {correct}  错误: {n_err}  Accuracy: {acc:.4f}')

    # ==================== 2. 按真实类别分组错误率 ====================
    print(f'\n--- 按真实类别的错误率 ---')
    print(f'  {"类别":<6} {"总数":>8} {"错误":>8} {"错误率":>10}')
    for c in [0, 1, 2]:
        n_c = sum(1 for t in y_true if t == c)
        err_c = sum(1 for t, p in zip(y_true, y_pred) if t == c and p != c)
        err_rate = err_c / n_c if n_c else 0
        print(f'  {LABEL_CN[c]:<6} {n_c:>8} {err_c:>8} {err_rate:>10.2%}')

    # ==================== 3. 混淆矩阵 ====================
    cm = [[0] * 3 for _ in range(3)]
    for t, p in zip(y_true, y_pred):
        cm[t][p] += 1
    print(f'\n--- 混淆矩阵 (行=真实, 列=预测) ---')
    print(f'  {"":>6} {"负面":>8} {"正面":>8} {"中性":>8}')
    for i in range(3):
        print(f'  {LABEL_CN[i]:>6} {cm[i][0]:>8} {cm[i][1]:>8} {cm[i][2]:>8}')

    # ==================== 4. 错误方向统计 ====================
    err_direction = Counter()
    for t, p in zip(y_true, y_pred):
        if t != p:
            err_direction[f'{LABEL_CN[t]} → {LABEL_CN[p]}'] += 1
    print(f'\n--- 错误方向分布 (Top) ---')
    for k, v in err_direction.most_common():
        print(f'  {k:<20} {v:>6} ({v/n_err:.1%})')

    # ==================== 5. 文本长度分布 ====================
    df_work = df.reset_index(drop=True).copy()
    df_work['y_pred'] = y_pred
    df_work['confidence'] = confidences
    df_work['correct'] = df_work['label'] == df_work['y_pred']
    df_work['text_len'] = df_work['review'].str.len()

    print(f'\n--- 文本长度分布 (正确 vs 错误) ---')
    len_bins = [(0, 20), (20, 50), (50, 100), (100, 200), (200, 10000)]
    print(f'  {"长度区间":<14} {"总数":>8} {"正确":>8} {"错误":>8} {"错误率":>10}')
    for lo, hi in len_bins:
        mask = (df_work['text_len'] >= lo) & (df_work['text_len'] < hi)
        n_t = mask.sum()
        n_c = (mask & df_work['correct']).sum()
        n_e = n_t - n_c
        rate = n_e / n_t if n_t else 0
        label = f'[{lo},{hi if hi < 10000 else "∞"})'
        print(f'  {label:<14} {n_t:>8} {n_c:>8} {n_e:>8} {rate:>10.2%}')

    # ==================== 6. BERT 置信度分布 ====================
    print(f'\n--- BERT 预测置信度分布 ---')
    conf_bins = [(0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]
    print(f'  {"置信区间":<14} {"总数":>8} {"正确":>8} {"错误":>8} {"准确率":>10}')
    for lo, hi in conf_bins:
        mask = (df_work['confidence'] >= lo) & (df_work['confidence'] < hi)
        n_t = mask.sum()
        n_c = (mask & df_work['correct']).sum()
        acc_b = n_c / n_t if n_t else 0
        label = f'[{lo:.1f},{hi:.2f})'
        print(f'  {label:<14} {n_t:>8} {n_c:>8} {n_t-n_c:>8} {acc_b:>10.2%}')

    # ==================== 7. 高置信错误样本 (最可疑) ====================
    err_df = df_work[~df_work['correct']].copy()
    err_df_sorted = err_df.sort_values('confidence', ascending=False)

    print(f'\n--- Top 10 高置信错误 (模型很自信但错了) ---')
    for _, row in err_df_sorted.head(10).iterrows():
        text = row['review']
        if len(text) > 70:
            text = text[:70] + '...'
        print(f'  真实={LABEL_CN[row["label"]]} 预测={LABEL_CN[row["y_pred"]]} '
              f'conf={row["confidence"]:.3f} | {text}')

    # ==================== 8. 低置信错误样本 ====================
    err_df_low = err_df.sort_values('confidence', ascending=True)
    print(f'\n--- Top 10 低置信错误 (模型不确定也错了) ---')
    for _, row in err_df_low.head(10).iterrows():
        text = row['review']
        if len(text) > 70:
            text = text[:70] + '...'
        print(f'  真实={LABEL_CN[row["label"]]} 预测={LABEL_CN[row["y_pred"]]} '
              f'conf={row["confidence"]:.3f} | {text}')

    # ==================== 9. 关键错误模式: 中性 vs 非中性 ====================
    # 统计: 真实中性被误判为正/负 的典型特征
    neu_as_other = err_df[err_df['label'] == 2]
    other_as_neu = err_df[err_df['y_pred'] == 2]

    print(f'\n--- 中性相关错误分析 ---')
    print(f'  中性→非中性 (漏判): {len(neu_as_other)} 条  '
          f'平均文本长度={neu_as_other["text_len"].mean():.1f}')
    print(f'  非中性→中性 (多判): {len(other_as_neu)} 条  '
          f'平均文本长度={other_as_neu["text_len"].mean():.1f}')

    # ==================== 10. 保存结果 ====================
    output = {
        'accuracy': acc,
        'total': len(y_true),
        'errors': n_err,
        'confusion_matrix': cm,
        'error_direction': dict(err_direction),
        'len_bins': [
            {'range': f'[{lo},{hi})',
             'total': int(((df_work['text_len'] >= lo) & (df_work['text_len'] < hi)).sum()),
             'errors': int(((df_work['text_len'] >= lo) & (df_work['text_len'] < hi) & ~df_work['correct']).sum())}
            for lo, hi in len_bins
        ],
        'confidence_bins': [
            {'range': f'[{lo:.1f},{hi:.2f})',
             'total': int(((df_work['confidence'] >= lo) & (df_work['confidence'] < hi)).sum()),
             'correct': int(((df_work['confidence'] >= lo) & (df_work['confidence'] < hi) & df_work['correct']).sum())}
            for lo, hi in conf_bins
        ],
        'high_confidence_errors_top10': [
            {'text': row['review'][:150], 'true': LABEL_CN[row['label']],
             'pred': LABEL_CN[row['y_pred']], 'confidence': row['confidence']}
            for _, row in err_df_sorted.head(10).iterrows()
        ],
        'neutral_related': {
            'neutral_as_other': len(neu_as_other),
            'other_as_neutral': len(other_as_neu),
            'neutral_errors_avg_len': float(neu_as_other['text_len'].mean()) if len(neu_as_other) else 0,
            'other_errors_avg_len': float(other_as_neu['text_len'].mean()) if len(other_as_neu) else 0,
        },
    }

    out_path = BACKEND_DIR / 'scripts' / 'error_analysis_results.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print(f'\n结果已保存: {out_path}')


if __name__ == '__main__':
    main()
