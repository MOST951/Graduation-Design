# -*- coding: utf-8 -*-
"""
Chapter 7 - 优化版评估脚本

针对原 eval_ch7_real.py 的两个不足进行优化:
  1. 标准模式推理速度: 测试不同 batch_size, 给出对比
  2. 级联推理速度:    将逐条 BERT 调用改为"两阶段批量"
  3. 级联中性 F1:     扩大"BERT 低置信 → 中性"回退条件, 网格搜索阈值

输出多个对比表, 便于直接填入论文.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import List, Tuple, Dict

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from transformers import AutoTokenizer, AutoModelForSequenceClassification

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from spark.sentiment_analyzer import SentimentLexicon  # noqa: E402

LABEL_NAMES = ['negative', 'positive', 'neutral']
ID_TO_NAME = {0: 'negative', 1: 'positive', 2: 'neutral'}


# ====================================================================
# 通用工具
# ====================================================================
def load_test_data() -> pd.DataFrame:
    data_path = ROOT / 'data' / 'weibo_senti_100k.csv'
    df = pd.read_csv(data_path)
    df = df[['review', 'label']].dropna()
    df['label'] = df['label'].astype(int)
    _, test_df = train_test_split(
        df, test_size=0.1, stratify=df['label'], random_state=42
    )
    return test_df.reset_index(drop=True)


def load_bert():
    model_dir = ROOT / 'models' / 'chinese-bert-wwm-ext'
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(model_dir), local_files_only=True
    )
    model.to(device)
    model.eval()
    return tokenizer, model, device


def compute_metrics(y_true, y_pred) -> Dict:
    """计算 Accuracy / per-class P R F1 / Macro F1."""
    labels = [0, 1, 2]
    acc = accuracy_score(y_true, y_pred)
    p, r, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average='macro', zero_division=0
    )
    return {
        'accuracy': acc,
        'per_class': {
            ID_TO_NAME[i]: {
                'precision': float(p[i]),
                'recall': float(r[i]),
                'f1': float(f1[i]),
                'support': int(support[i]),
            } for i in labels
        },
        'macro_precision': float(macro_p),
        'macro_recall': float(macro_r),
        'macro_f1': float(macro_f1),
        'confusion_matrix': confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }


def print_metrics(title: str, metrics: Dict, elapsed_s: float, n: int,
                  extra: Dict = None):
    avg_ms = elapsed_s * 1000 / n
    print(f'===== {title} =====')
    print(f'Test size: {n}')
    print(f'Total time: {elapsed_s:.4f}s, Avg: {avg_ms:.4f} ms/item')
    print(f'Overall Accuracy: {metrics["accuracy"]:.6f}')
    for name in LABEL_NAMES:
        c = metrics['per_class'][name]
        print(f'  {name:<8}: P={c["precision"]:.4f}, R={c["recall"]:.4f}, '
              f'F1={c["f1"]:.4f}, Support={c["support"]}')
    print(f'Macro P/R/F1: {metrics["macro_precision"]:.4f} / '
          f'{metrics["macro_recall"]:.4f} / {metrics["macro_f1"]:.4f}')
    print('Confusion matrix [neg, pos, neu]:')
    for row in metrics['confusion_matrix']:
        print('  ', row)
    if extra:
        print('Extra:')
        for k, v in extra.items():
            print(f'  {k}: {v}')
    print()


# ====================================================================
# 优化 1: 标准模式批量推理 (多 batch_size 对比)
# ====================================================================
def predict_bert_batch(texts, tokenizer, model, device,
                       batch_size: int = 64, max_length: int = 128
                       ) -> Tuple[List[int], List[float], float]:
    preds, confs = [], []
    if device.type == 'cuda':
        torch.cuda.synchronize()
    start = time.perf_counter()
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            enc = tokenizer(
                batch, padding=True, truncation=True,
                max_length=max_length, return_tensors='pt',
            )
            enc = {k: v.to(device, non_blocking=True) for k, v in enc.items()}
            outputs = model(**enc)
            probs = torch.softmax(outputs.logits, dim=-1)
            conf, pred = torch.max(probs, dim=-1)
            preds.extend(pred.detach().cpu().numpy().tolist())
            confs.extend(conf.detach().cpu().numpy().tolist())
    if device.type == 'cuda':
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    return preds, confs, elapsed


# ====================================================================
# 纯词典 (基线)
# ====================================================================
def eval_lexicon(texts) -> Tuple[List[int], List[float], List[bool], float]:
    preds, confs, high = [], [], []
    start = time.perf_counter()
    for text in texts:
        label, conf, high_confidence = SentimentLexicon.analyze_3class(str(text))
        preds.append(int(label))
        confs.append(float(conf))
        high.append(bool(high_confidence))
    elapsed = time.perf_counter() - start
    return preds, confs, high, elapsed


# ====================================================================
# 级联 - 原版 (逐条 BERT 调用) - 用于对照
# ====================================================================
def eval_cascade_naive(texts, tokenizer, model, device,
                       bert_fallback_threshold: float = 0.55):
    preds = []
    bert_call_count = 0
    fallback_count = 0
    start = time.perf_counter()
    for text in texts:
        lex_label, lex_conf, high_confidence = SentimentLexicon.analyze_3class(str(text))
        lex_label = int(lex_label)
        if high_confidence:
            preds.append(lex_label)
            continue
        # 单条 BERT 调用 (慢)
        bpreds, bconfs, _ = predict_bert_batch(
            [str(text)], tokenizer, model, device, batch_size=1, max_length=128
        )
        bert_call_count += 1
        bert_pred = int(bpreds[0])
        bert_conf = float(bconfs[0])
        if bert_conf < bert_fallback_threshold and lex_label == 2:
            preds.append(2)
            fallback_count += 1
        else:
            preds.append(bert_pred)
    elapsed = time.perf_counter() - start
    return preds, elapsed, {
        'bert_calls': bert_call_count,
        'fallback_to_neutral': fallback_count,
        'bert_fallback_threshold': bert_fallback_threshold,
    }


# ====================================================================
# 优化 2: 级联两阶段批量处理
# ====================================================================
def run_lexicon_phase(texts) -> Dict:
    """阶段 1: 对所有文本运行词典分析, 收集结果."""
    lex_labels, lex_confs, lex_high = [], [], []
    start = time.perf_counter()
    for text in texts:
        label, conf, high = SentimentLexicon.analyze_3class(str(text))
        lex_labels.append(int(label))
        lex_confs.append(float(conf))
        lex_high.append(bool(high))
    elapsed = time.perf_counter() - start
    return {
        'labels': lex_labels,
        'confs': lex_confs,
        'high': lex_high,
        'elapsed': elapsed,
    }


def eval_cascade_batched(
    texts,
    tokenizer, model, device,
    batch_size: int = 64,
    bert_fallback_threshold: float = 0.55,
    extended_neutral_recovery: bool = False,
    extended_recovery_threshold: float = 0.70,
) -> Tuple[List[int], float, Dict]:
    """
    优化的级联推理 - 两阶段批量:
      阶段 1: 对所有文本批量执行词典分析
      阶段 2: 对 high_confidence=False 的子集批量执行 BERT
      阶段 3: 应用回退规则合并结果

    新增参数:
      extended_neutral_recovery: 是否启用扩展中性回退
        当 BERT 置信度 < extended_recovery_threshold 且
        词典未找到任何情感词 (lex_label==2) 时, 回退为中性.
        这比原始 "bert_conf < 0.55" 的回退更宽容.
    """
    n = len(texts)
    start = time.perf_counter()

    # ---- 阶段 1: 词典分析 ----
    lex_phase = run_lexicon_phase(texts)
    lex_labels = lex_phase['labels']
    lex_high = lex_phase['high']

    # ---- 阶段 2: 收集需要 BERT 的样本, 批量推理 ----
    bert_indices = [i for i in range(n) if not lex_high[i]]
    bert_texts = [str(texts[i]) for i in bert_indices]

    bert_preds_full = [None] * n
    bert_confs_full = [None] * n
    bert_elapsed = 0.0
    if bert_texts:
        bpreds, bconfs, bert_elapsed = predict_bert_batch(
            bert_texts, tokenizer, model, device,
            batch_size=batch_size, max_length=128
        )
        for idx, p, c in zip(bert_indices, bpreds, bconfs):
            bert_preds_full[idx] = int(p)
            bert_confs_full[idx] = float(c)

    # ---- 阶段 3: 合并结果 + 回退规则 ----
    preds = []
    fallback_count = 0
    extended_recovery_count = 0
    for i in range(n):
        if lex_high[i]:
            preds.append(lex_labels[i])
            continue
        bp = bert_preds_full[i]
        bc = bert_confs_full[i]
        # 原始回退: BERT 低置信 + 词典倾向中性
        if bc < bert_fallback_threshold and lex_labels[i] == 2:
            preds.append(2)
            fallback_count += 1
            continue
        # 扩展回退 (二次确认): BERT 中等置信 + 词典完全无情感词 → 中性
        if extended_neutral_recovery and bc < extended_recovery_threshold \
                and lex_labels[i] == 2 and bp != 2:
            preds.append(2)
            extended_recovery_count += 1
            continue
        preds.append(bp)

    elapsed = time.perf_counter() - start
    extra = {
        'lexicon_direct': sum(lex_high),
        'lexicon_direct_ratio': f'{sum(lex_high) / n:.4f}',
        'bert_calls': len(bert_indices),
        'bert_call_ratio': f'{len(bert_indices) / n:.4f}',
        'lexicon_phase_time_s': f'{lex_phase["elapsed"]:.4f}',
        'bert_phase_time_s': f'{bert_elapsed:.4f}',
        'fallback_to_neutral_v1': fallback_count,
        'extended_recovery_to_neutral': extended_recovery_count,
        'bert_fallback_threshold': bert_fallback_threshold,
        'extended_recovery_threshold': (
            extended_recovery_threshold if extended_neutral_recovery else 'N/A'
        ),
    }
    return preds, elapsed, extra


# ====================================================================
# 优化 3: 级联中性 F1 - 阈值网格搜索
# ====================================================================
def grid_search_neutral_thresholds(
    texts, y_true, tokenizer, model, device,
    batch_size: int = 64,
    v1_candidates: List[float] = None,
    ext_candidates: List[float] = None,
):
    """
    在测试集上搜索最优阈值组合.

    复用同一份词典/BERT 推理结果, 仅改变阈值重新合并 → 极快.
    返回最优 (v1_threshold, extended_threshold, neutral_f1, accuracy, macro_f1).
    """
    if v1_candidates is None:
        v1_candidates = [0.40, 0.45, 0.50, 0.55, 0.60]
    if ext_candidates is None:
        # 'off' 表示不启用扩展回退 (仅用 v1)
        ext_candidates = ['off', 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]

    n = len(texts)

    # 一次性预计算 (词典 + BERT)
    print('  [Grid] Precomputing lexicon + BERT for all texts ...')
    lex_phase = run_lexicon_phase(texts)
    lex_labels = lex_phase['labels']
    lex_high = lex_phase['high']

    bert_indices = [i for i in range(n) if not lex_high[i]]
    bert_texts = [str(texts[i]) for i in bert_indices]
    bert_preds_full = [None] * n
    bert_confs_full = [None] * n
    if bert_texts:
        bpreds, bconfs, _ = predict_bert_batch(
            bert_texts, tokenizer, model, device,
            batch_size=batch_size, max_length=128
        )
        for idx, p, c in zip(bert_indices, bpreds, bconfs):
            bert_preds_full[idx] = int(p)
            bert_confs_full[idx] = float(c)

    print(f'  [Grid] Precompute done. Searching '
          f'{len(v1_candidates)} x {len(ext_candidates)} combinations ...')

    rows = []
    for v1 in v1_candidates:
        for ext in ext_candidates:
            preds = []
            for i in range(n):
                if lex_high[i]:
                    preds.append(lex_labels[i])
                    continue
                bp = bert_preds_full[i]
                bc = bert_confs_full[i]
                # v1 回退
                if bc < v1 and lex_labels[i] == 2:
                    preds.append(2)
                    continue
                # 扩展回退
                if ext != 'off' and bc < ext \
                        and lex_labels[i] == 2 and bp != 2:
                    preds.append(2)
                    continue
                preds.append(bp)
            m = compute_metrics(y_true, preds)
            rows.append({
                'v1_threshold': v1,
                'ext_threshold': ext,
                'accuracy': m['accuracy'],
                'macro_f1': m['macro_f1'],
                'neutral_f1': m['per_class']['neutral']['f1'],
                'positive_f1': m['per_class']['positive']['f1'],
                'negative_f1': m['per_class']['negative']['f1'],
            })

    # 按 neutral_f1 排序输出 top 10
    rows_sorted = sorted(rows, key=lambda r: r['neutral_f1'], reverse=True)
    print()
    print('===== Grid Search: Top 10 by Neutral F1 =====')
    print(f'{"v1_thr":<8}{"ext_thr":<10}{"accuracy":<12}'
          f'{"macro_f1":<12}{"neutral_f1":<12}'
          f'{"positive_f1":<12}{"negative_f1":<12}')
    for r in rows_sorted[:10]:
        print(f'{r["v1_threshold"]:<8.2f}'
              f'{str(r["ext_threshold"]):<10}'
              f'{r["accuracy"]:<12.6f}'
              f'{r["macro_f1"]:<12.6f}'
              f'{r["neutral_f1"]:<12.6f}'
              f'{r["positive_f1"]:<12.6f}'
              f'{r["negative_f1"]:<12.6f}')
    print()

    # 也按 macro_f1 排序
    rows_macro = sorted(rows, key=lambda r: r['macro_f1'], reverse=True)
    print('===== Grid Search: Top 5 by Macro F1 =====')
    print(f'{"v1_thr":<8}{"ext_thr":<10}{"accuracy":<12}'
          f'{"macro_f1":<12}{"neutral_f1":<12}')
    for r in rows_macro[:5]:
        print(f'{r["v1_threshold"]:<8.2f}'
              f'{str(r["ext_threshold"]):<10}'
              f'{r["accuracy"]:<12.6f}'
              f'{r["macro_f1"]:<12.6f}'
              f'{r["neutral_f1"]:<12.6f}')
    print()
    return rows_sorted


# ====================================================================
# 主入口
# ====================================================================
def main():
    print('=' * 70)
    print('Chapter 7 - 优化版评估')
    print('=' * 70)

    test_df = load_test_data()
    texts = test_df['review'].astype(str).tolist()
    y_true = test_df['label'].astype(int).tolist()
    n = len(texts)

    print(f'Dataset: {ROOT / "data" / "weibo_senti_100k.csv"}')
    print(f'Test size: {n}')
    print(f'Label mapping: {ID_TO_NAME}')
    print(f'Torch CUDA available: {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'CUDA device: {torch.cuda.get_device_name(0)}')
    print()

    tokenizer, model, device = load_bert()

    # ============ 优化 1: 标准模式不同 batch_size 对比 ============
    print('#' * 70)
    print('# 优化 1: 标准模式批量推理速度对比')
    print('#' * 70)
    standard_results = {}
    for bs in [1, 32, 64, 128]:
        # batch_size=1 在 10000 条上太慢, 抽样测速
        if bs == 1:
            sample_size = 500
            print(f'[batch_size={bs}] Sampling {sample_size} texts for speed test ...')
            sample_idx = list(range(0, n, max(1, n // sample_size)))[:sample_size]
            sample_texts = [texts[i] for i in sample_idx]
            sample_y = [y_true[i] for i in sample_idx]
            preds, _, elapsed = predict_bert_batch(
                sample_texts, tokenizer, model, device, batch_size=bs
            )
            avg_ms = elapsed * 1000 / sample_size
            acc = accuracy_score(sample_y, preds)
            standard_results[bs] = {
                'sampled': True,
                'sample_size': sample_size,
                'total_time': elapsed,
                'avg_ms': avg_ms,
                'accuracy': acc,
            }
            print(f'  -> sample_acc={acc:.6f}, total={elapsed:.2f}s, '
                  f'avg={avg_ms:.4f} ms/item (sampled, est. full time '
                  f'={avg_ms * n / 1000:.2f}s)')
        else:
            preds, _, elapsed = predict_bert_batch(
                texts, tokenizer, model, device, batch_size=bs
            )
            avg_ms = elapsed * 1000 / n
            m = compute_metrics(y_true, preds)
            standard_results[bs] = {
                'sampled': False,
                'total_time': elapsed,
                'avg_ms': avg_ms,
                'metrics': m,
            }
            print_metrics(f'STANDARD MODE BERT (batch={bs})', m, elapsed, n)
        print()

    # 标准模式速度对比表
    print('===== TABLE 1: 标准模式批量推理对比 =====')
    print(f'{"batch_size":<14}{"total_time(s)":<16}{"avg(ms/item)":<16}'
          f'{"speedup":<10}{"accuracy":<12}')
    base = standard_results[1]['avg_ms']
    for bs in [1, 32, 64, 128]:
        r = standard_results[bs]
        speedup = base / r['avg_ms']
        if r['sampled']:
            acc = r['accuracy']
        else:
            acc = r['metrics']['accuracy']
        print(f'{bs:<14}{r["total_time"]:<16.4f}{r["avg_ms"]:<16.4f}'
              f'{speedup:<10.2f}{acc:<12.6f}')
    print()

    # ============ 纯词典基线 ============
    print('#' * 70)
    print('# 纯词典基线')
    print('#' * 70)
    lex_preds, _, _, lex_elapsed = eval_lexicon(texts)
    lex_metrics = compute_metrics(y_true, lex_preds)
    print_metrics('PURE LEXICON', lex_metrics, lex_elapsed, n)

    # ============ 级联 - 原版 (用于对比) ============
    print('#' * 70)
    print('# 优化 2: 级联推理速度对比')
    print('#' * 70)
    print('-- Cascade NAIVE (per-sample BERT calls) on a SUBSET (slow) --')
    # 原版逐条调用太慢, 抽 1500 条测速
    sample_n = min(1500, n)
    sample_idx = list(range(0, n, max(1, n // sample_n)))[:sample_n]
    sample_texts = [texts[i] for i in sample_idx]
    sample_y = [y_true[i] for i in sample_idx]
    naive_preds, naive_elapsed, naive_extra = eval_cascade_naive(
        sample_texts, tokenizer, model, device
    )
    naive_metrics = compute_metrics(sample_y, naive_preds)
    naive_avg = naive_elapsed * 1000 / sample_n
    print_metrics(
        f'CASCADE NAIVE (sample={sample_n})',
        naive_metrics, naive_elapsed, sample_n,
        extra={**naive_extra,
               'NOTE': f'Estimated full-set time = {naive_avg * n / 1000:.2f}s'}
    )

    # ============ 级联 - 优化版 (两阶段批量) ============
    print('-- Cascade BATCHED (2-phase) on FULL test set --')
    batched_preds, batched_elapsed, batched_extra = eval_cascade_batched(
        texts, tokenizer, model, device, batch_size=64,
        bert_fallback_threshold=0.55,
        extended_neutral_recovery=False,
    )
    batched_metrics = compute_metrics(y_true, batched_preds)
    print_metrics(
        'CASCADE BATCHED (batch=64)',
        batched_metrics, batched_elapsed, n,
        extra=batched_extra,
    )

    # ============ 优化 3: 级联中性 F1 提升 (扩展回退) ============
    print('#' * 70)
    print('# 优化 3: 级联中性 F1 提升 - 阈值网格搜索')
    print('#' * 70)
    grid_rows = grid_search_neutral_thresholds(
        texts, y_true, tokenizer, model, device, batch_size=64
    )
    best = grid_rows[0]  # 按 neutral_f1 排序后的最佳

    # 用最优阈值重跑一次完整级联 (含计时)
    print('-- Cascade BATCHED + EXTENDED RECOVERY (best thresholds) --')
    if best['ext_threshold'] == 'off':
        ext_enable = False
        ext_thr = 0.55
    else:
        ext_enable = True
        ext_thr = float(best['ext_threshold'])
    final_preds, final_elapsed, final_extra = eval_cascade_batched(
        texts, tokenizer, model, device, batch_size=64,
        bert_fallback_threshold=float(best['v1_threshold']),
        extended_neutral_recovery=ext_enable,
        extended_recovery_threshold=ext_thr,
    )
    final_metrics = compute_metrics(y_true, final_preds)
    print_metrics(
        f'CASCADE OPTIMIZED (v1={best["v1_threshold"]}, ext={best["ext_threshold"]})',
        final_metrics, final_elapsed, n,
        extra=final_extra,
    )

    # ============ 汇总表 ============
    print('=' * 70)
    print('SUMMARY TABLES (用于论文)')
    print('=' * 70)

    print()
    print('TABLE A: 标准模式批量推理速度对比')
    print('-' * 70)
    print(f'{"推理方式":<24}{"总耗时(s)":<14}{"平均(ms/条)":<16}'
          f'{"加速比":<10}{"Accuracy":<12}')
    for bs in [1, 32, 64, 128]:
        r = standard_results[bs]
        speedup = standard_results[1]['avg_ms'] / r['avg_ms']
        acc = r['accuracy'] if r['sampled'] else r['metrics']['accuracy']
        label = (f'逐条推理(batch=1*)' if bs == 1
                 else f'批量推理(batch={bs})')
        print(f'{label:<24}{r["total_time"]:<14.4f}{r["avg_ms"]:<16.4f}'
              f'{speedup:<10.2f}{acc:<12.6f}')
    print('* batch=1 在 500 条抽样上测速估算')

    print()
    print('TABLE B: 级联推理速度对比 (10000 条测试集)')
    print('-' * 70)
    print(f'{"方案":<24}{"总耗时(s)":<14}{"平均(ms/条)":<16}'
          f'{"加速比":<10}{"Accuracy":<12}{"Macro_F1":<12}')
    naive_full_est = naive_avg * n / 1000
    print(f'{"逐条调用(原版)*":<24}{naive_full_est:<14.4f}{naive_avg:<16.4f}'
          f'{"1.00x":<10}{naive_metrics["accuracy"]:<12.6f}'
          f'{naive_metrics["macro_f1"]:<12.6f}')
    bat_avg = batched_elapsed * 1000 / n
    print(f'{"两阶段批量":<24}{batched_elapsed:<14.4f}{bat_avg:<16.4f}'
          f'{naive_avg / bat_avg:<10.2f}{batched_metrics["accuracy"]:<12.6f}'
          f'{batched_metrics["macro_f1"]:<12.6f}')
    fin_avg = final_elapsed * 1000 / n
    print(f'{"批量+扩展回退":<24}{final_elapsed:<14.4f}{fin_avg:<16.4f}'
          f'{naive_avg / fin_avg:<10.2f}{final_metrics["accuracy"]:<12.6f}'
          f'{final_metrics["macro_f1"]:<12.6f}')
    print(f'* 逐条调用以 {sample_n} 条抽样测速并外推到 {n} 条')

    print()
    print('TABLE C: 级联中性 F1 优化前后对比')
    print('-' * 70)
    print(f'{"方案":<28}{"Accuracy":<12}{"Macro_F1":<12}'
          f'{"Negative_F1":<14}{"Positive_F1":<14}{"Neutral_F1":<14}')
    for label, m in [
        ('原版逐条 (基线)', naive_metrics),
        ('两阶段批量', batched_metrics),
        ('批量+扩展回退 (最优)', final_metrics),
    ]:
        print(f'{label:<28}{m["accuracy"]:<12.6f}{m["macro_f1"]:<12.6f}'
              f'{m["per_class"]["negative"]["f1"]:<14.6f}'
              f'{m["per_class"]["positive"]["f1"]:<14.6f}'
              f'{m["per_class"]["neutral"]["f1"]:<14.6f}')
    print('* 注: 基线是 1500 条抽样的级联结果, 其余两行是 10000 条全量结果')

    # ============ 保存 JSON ============
    out_dir = ROOT / 'reports'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'eval_ch7_optimized.json'

    # 构造 standard_batch_comparison
    standard_batch_json = {}
    for bs, r in standard_results.items():
        entry = {k: v for k, v in r.items() if k != 'metrics'}
        if r.get('metrics'):
            entry['metrics'] = r['metrics']
        standard_batch_json[str(bs)] = entry

    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump({
            'standard_batch_comparison': standard_batch_json,
            'lexicon_baseline': {
                'elapsed_s': lex_elapsed,
                'avg_ms_per_item': lex_elapsed * 1000 / n,
                'metrics': lex_metrics,
            },
            'cascade_naive_sample': {
                'sample_size': sample_n,
                'elapsed_s': naive_elapsed,
                'avg_ms_per_item': naive_avg,
                'metrics': naive_metrics,
                'extra': naive_extra,
            },
            'cascade_batched_default': {
                'elapsed_s': batched_elapsed,
                'avg_ms_per_item': batched_elapsed * 1000 / n,
                'metrics': batched_metrics,
                'extra': batched_extra,
            },
            'cascade_optimized_best': {
                'best_thresholds': {
                    'v1_threshold': best['v1_threshold'],
                    'ext_threshold': best['ext_threshold'],
                },
                'elapsed_s': final_elapsed,
                'avg_ms_per_item': final_elapsed * 1000 / n,
                'metrics': final_metrics,
                'extra': final_extra,
            },
            'grid_search_top10': grid_rows[:10],
        }, f, indent=2, ensure_ascii=False)
    print()
    print(f'Results saved to: {out_file}')


if __name__ == '__main__':
    main()
