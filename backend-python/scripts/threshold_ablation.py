#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
级联策略阈值消融实验 (Threshold Ablation Study)
=================================================

在 10,000 条隔离测试集上扫描 θ ∈ {0.5, 0.6, 0.7, 0.8, 0.9}，
记录各阈值下的：
  - Accuracy / Macro F1
  - 词典直出比例 (lexicon path ratio)
  - BERT 调用比例 (bert path ratio)
  - 平均推理耗时 (ms/条)

为避免 5×BERT 重复推理，本脚本一次性跑完纯词典与纯 BERT 两条主路径，
然后基于两路结果在内存中模拟不同 θ 的级联决策（约 3-5 分钟）。

输出: scripts/threshold_ablation_results.json + 终端 Markdown 表格

用法:
  cd backend-python
  python scripts/threshold_ablation.py
"""

import sys
import time
import json
import logging
from pathlib import Path
from typing import List, Dict

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('ThresholdAblation')

LABEL_CN = {0: '负面', 1: '正面', 2: '中性'}
TEST_SET_PATH = BACKEND_DIR / 'data' / 'test_set_200.csv'
OUTPUT_PATH = SCRIPT_DIR / 'threshold_ablation_results.json'

THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9]


def load_test_set() -> pd.DataFrame:
    df = pd.read_csv(str(TEST_SET_PATH))
    df = df.dropna(subset=['review', 'label'])
    df = df[df['label'].isin([0, 1, 2])]
    df['review'] = df['review'].astype(str)
    logger.info(f'测试集: {len(df)} 条')
    return df


def compute_accuracy(y_true: List[int], y_pred: List[int]) -> Dict:
    """三分类指标"""
    n = len(y_true)
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / n if n else 0
    f1_per_class = []
    for c in [0, 1, 2]:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == c and p == c)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != c and p == c)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == c and p != c)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        f1_per_class.append(f1)
    return {
        'accuracy': accuracy,
        'macro_f1': float(np.mean(f1_per_class)),
        'correct': correct,
        'total': n,
    }


def main():
    from scripts.evaluate_cascade_3class import LexiconAnalyzer, BERTAnalyzer

    df = load_test_set()
    texts = df['review'].tolist()
    y_true = df['label'].tolist()
    n = len(texts)

    # ---- 1. 一次性预计算词典与 BERT 结果 ----
    logger.info('Step 1/3: 预计算词典分析结果 ...')
    lex = LexiconAnalyzer()
    lex_results = []
    t0 = time.perf_counter()
    for i, text in enumerate(texts):
        if (i + 1) % 2000 == 0:
            logger.info(f'  词典进度 {i+1}/{n}')
        lex_results.append(lex.analyze_3class(text))
    lex_time_total = time.perf_counter() - t0
    lex_avg_ms = lex_time_total / n * 1000
    logger.info(f'  词典平均: {lex_avg_ms:.3f} ms/条')

    logger.info('Step 2/3: 预计算 BERT 分析结果 ...')
    bert = BERTAnalyzer()
    bert.initialize()
    bert_results = []
    t0 = time.perf_counter()
    for i, text in enumerate(texts):
        if (i + 1) % 1000 == 0:
            logger.info(f'  BERT 进度 {i+1}/{n}')
        bert_results.append(bert.analyze(text))
    bert_time_total = time.perf_counter() - t0
    bert_avg_ms = bert_time_total / n * 1000
    logger.info(f'  BERT 平均: {bert_avg_ms:.2f} ms/条')

    # ---- 2. 纯词典 / 纯 BERT 基线指标 ----
    lex_preds = [r['label'] for r in lex_results]
    bert_preds = [r['label'] for r in bert_results]
    lex_metrics = compute_accuracy(y_true, lex_preds)
    bert_metrics = compute_accuracy(y_true, bert_preds)

    # ---- 3. 扫描 θ ----
    logger.info(f'Step 3/3: 扫描 θ ∈ {THRESHOLDS} ...')
    bert_fallback_threshold = 0.55  # 与 evaluate_cascade_3class.py 保持一致
    sweep_rows = []
    for theta in THRESHOLDS:
        cas_preds = []
        lex_path = 0
        bert_path = 0
        for i in range(n):
            lex_r = lex_results[i]
            bert_r = bert_results[i]
            # 级联门控: high_confidence AND confidence >= θ → 词典直出
            if lex_r['high_confidence'] and lex_r['confidence'] >= theta:
                cas_preds.append(lex_r['label'])
                lex_path += 1
            else:
                pred = bert_r['label']
                # BERT 低置信回退中性
                if bert_r['confidence'] < bert_fallback_threshold and lex_r['label'] == 2 and pred != 2:
                    pred = 2
                cas_preds.append(pred)
                bert_path += 1

        m = compute_accuracy(y_true, cas_preds)
        # 平均耗时 = 词典恒定 + (BERT 调用比例 × BERT 耗时)
        avg_ms = lex_avg_ms + (bert_path / n) * bert_avg_ms
        speedup = bert_avg_ms / avg_ms if avg_ms > 0 else 0
        sweep_rows.append({
            'theta': theta,
            'accuracy': m['accuracy'],
            'macro_f1': m['macro_f1'],
            'lex_path_ratio': lex_path / n,
            'bert_path_ratio': bert_path / n,
            'avg_time_ms': avg_ms,
            'speedup_vs_bert': speedup,
        })
        logger.info(
            f'  θ={theta}: acc={m["accuracy"]:.4f}, F1={m["macro_f1"]:.4f}, '
            f'BERT调用={bert_path/n:.1%}, 耗时={avg_ms:.2f}ms ({speedup:.2f}× vs 纯BERT)'
        )

    # ---- 4. 输出 ----
    result = {
        'dataset_size': n,
        'class_distribution': {LABEL_CN[c]: int((df['label'] == c).sum()) for c in [0, 1, 2]},
        'baselines': {
            'lexicon_only': {**lex_metrics, 'avg_time_ms': lex_avg_ms},
            'bert_only': {**bert_metrics, 'avg_time_ms': bert_avg_ms},
        },
        'threshold_sweep': sweep_rows,
        'bert_fallback_threshold': bert_fallback_threshold,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f'结果已保存: {OUTPUT_PATH}')

    # ---- 5. Markdown 表格输出 (论文可直接粘贴) ----
    print()
    print('=' * 78)
    print('  阈值消融实验结果 (Markdown 表格 — 可直接粘贴论文)')
    print('=' * 78)
    print()
    print('| θ阈值 | 准确率 | Macro F1 | 词典直出 | BERT调用 | 平均耗时 | 相对加速 |')
    print('|------|--------|----------|---------|---------|---------|---------|')
    print(f'| 纯词典 (基线) | {lex_metrics["accuracy"]:.2%} | {lex_metrics["macro_f1"]:.4f} | 100.0% | 0.0% | {lex_avg_ms:.2f}ms | — |')
    for row in sweep_rows:
        print(
            f'| {row["theta"]} | {row["accuracy"]:.2%} | {row["macro_f1"]:.4f} | '
            f'{row["lex_path_ratio"]:.1%} | {row["bert_path_ratio"]:.1%} | '
            f'{row["avg_time_ms"]:.2f}ms | {row["speedup_vs_bert"]:.2f}× |'
        )
    print(f'| 纯 BERT (基线) | {bert_metrics["accuracy"]:.2%} | {bert_metrics["macro_f1"]:.4f} | 0.0% | 100.0% | {bert_avg_ms:.2f}ms | 1.00× |')
    print()
    print('=' * 78)


if __name__ == '__main__':
    main()
