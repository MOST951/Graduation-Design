#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合级联策略 — 三分类完整评估
==============================

在隔离测试集 (10,000 条, 3-class) 上对比：
  1. 纯词典 (Lexicon-only)
  2. 纯 ChineseBERT
  3. 混合级联 (θ=0.7): |Sdict| > θ → 词典直出, 否则调 BERT

标签: 0=negative, 1=positive, 2=neutral

用法:
  cd backend-python
  python scripts/evaluate_cascade_3class.py [--threshold 0.7]
"""

import os
import sys
import time
import json
import argparse
import logging
from pathlib import Path
from collections import Counter
from typing import List, Dict, Tuple

import pandas as pd
import numpy as np

# 路径设置
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('CascadeEval3Class')

# 标签映射
LABEL_NAMES = {0: 'negative', 1: 'positive', 2: 'neutral'}
LABEL_CN = {0: '负面', 1: '正面', 2: '中性'}
SENTIMENT_TO_LABEL = {'negative': 0, 'positive': 1, 'neutral': 2}

TEST_SET_PATH = BACKEND_DIR / 'data' / 'test_set_200.csv'


# ==================== 1. 数据加载 ====================

def load_test_set() -> pd.DataFrame:
    """加载隔离测试集"""
    if not TEST_SET_PATH.exists():
        logger.error(f'测试集不存在: {TEST_SET_PATH}')
        logger.error('请先运行: python scripts/finetune_classifier.py')
        sys.exit(1)

    df = pd.read_csv(str(TEST_SET_PATH))
    df = df.dropna(subset=['review', 'label'])
    df = df[df['label'].isin([0, 1, 2])]
    df['review'] = df['review'].astype(str)

    logger.info(f'测试集加载: {len(df)} 条')
    for lbl in [0, 1, 2]:
        cnt = (df['label'] == lbl).sum()
        logger.info(f'  {LABEL_CN[lbl]}(label={lbl}): {cnt}')
    return df


# ==================== 2. 分析器 ====================

class LexiconAnalyzer:
    """词典分析器 (使用 SentimentLexicon)"""

    def __init__(self):
        from spark.sentiment_analyzer import SentimentLexicon
        self._cls = SentimentLexicon

    def analyze(self, text: str) -> Dict:
        """旧接口 (2分类 + 归一化 score), 用于纯词典对比."""
        t0 = time.perf_counter()
        sentiment, score = self._cls.analyze(text)
        elapsed = (time.perf_counter() - t0) * 1000
        label = SENTIMENT_TO_LABEL.get(sentiment, 2)
        return {
            'label': label,
            'score': score,
            'confidence': abs(score),
            'time_ms': elapsed,
        }

    def analyze_3class(self, text: str) -> Dict:
        """3分类级联专用: 返回 {label, confidence, high_confidence, time_ms}."""
        t0 = time.perf_counter()
        label, confidence, high_conf = self._cls.analyze_3class(text)
        elapsed = (time.perf_counter() - t0) * 1000
        return {
            'label': label,
            'confidence': confidence,
            'high_confidence': high_conf,
            'time_ms': elapsed,
        }


class BERTAnalyzer:
    """ChineseBERT 分析器"""

    def __init__(self):
        self._model = None

    def initialize(self):
        from models.chinese_bert_sentiment import ChineseBertSentimentModel
        self._model = ChineseBertSentimentModel()
        # 触发模型加载
        self._model._init_model()
        logger.info('BERT 分析器初始化成功')

    def analyze(self, text: str) -> Dict:
        """返回 {label: int, score: float, confidence: float, time_ms: float}"""
        t0 = time.perf_counter()
        results = self._model.predict(text, return_probs=False)
        elapsed = (time.perf_counter() - t0) * 1000
        r = results[0]
        return {
            'label': r['label_id'],
            'score': r['score'],
            'confidence': r['confidence'],
            'time_ms': elapsed,
        }


class CascadeAnalyzer:
    """
    改进的三分类级联:
      - 使用 SentimentLexicon.analyze_3class() 直接判别
      - high_confidence=True → 词典直出
      - 否则调用 BERT

    不再依赖单一阈值 θ, 而是由 3 条规则联合判定 (空文本/无情感词/
    多正面词/多负面词/负面emoji密集)。
    """

    # BERT 低置信度回退的默认阈值。当 BERT 置信度低于此值且词典
    # 倾向中性时，回退采用词典的中性判断。该值可通过构造函数或
    # find_optimal_bert_fallback_threshold() 方法调整。
    DEFAULT_BERT_FALLBACK_THRESHOLD = 0.55

    def __init__(self, threshold: float = 0.7,
                 bert_fallback_threshold: float = None):
        """
        Args:
            threshold: 词典高置信直出的最低置信度要求
            bert_fallback_threshold: BERT 低置信回退阈值，低于此值时
                                     若词典倾向中性则回退为中性。
                                     默认使用 DEFAULT_BERT_FALLBACK_THRESHOLD。
        """
        self.threshold = threshold
        self.bert_fallback_threshold = (
            bert_fallback_threshold if bert_fallback_threshold is not None
            else self.DEFAULT_BERT_FALLBACK_THRESHOLD
        )
        self.lexicon = LexiconAnalyzer()
        self.bert = BERTAnalyzer()
        self.bert.initialize()

    def analyze(self, text: str) -> Dict:
        lex = self.lexicon.analyze_3class(text)

        # 高置信度 → 词典直出
        if lex['high_confidence'] and lex['confidence'] >= self.threshold:
            return {
                'label': lex['label'],
                'confidence': lex['confidence'],
                'time_ms': lex['time_ms'],
                'method': 'lexicon',
            }

        # 否则调 BERT
        bert = self.bert.analyze(text)
        bert_label = bert['label']
        bert_conf = bert['confidence']
        method = 'bert'

        # ---- BERT 置信度回退 ----
        # 当 BERT 非常不确定 (< bert_fallback_threshold) 且词典给出了方向性线索,
        # 退回到"默认中性"(在微博场景中, 语义模糊的文本更可能是中性陈述)
        if bert_conf < self.bert_fallback_threshold:
            # 若词典倾向中性 (label=2) 且 BERT 也没有强烈反对 (非中性概率低)
            # 则采信词典的中性判断
            if lex['label'] == 2 and bert_label != 2:
                bert_label = 2
                method = 'bert+fallback_neutral'

        return {
            'label': bert_label,
            'score': bert.get('score', 0.0),
            'confidence': bert_conf,
            'time_ms': lex['time_ms'] + bert['time_ms'],
            'method': method,
        }

    @staticmethod
    def find_optimal_bert_fallback_threshold(
        texts: List[str], y_true: List[int],
        lexicon: 'LexiconAnalyzer', bert: 'BERTAnalyzer',
        candidates: List[float] = None,
    ) -> Tuple[float, float]:
        """
        在验证集上搜索最优 BERT 回退阈值。

        对每个候选阈值，模拟级联逻辑并计算 Accuracy，
        返回最优阈值及对应 Accuracy。

        Args:
            texts: 验证集文本列表
            y_true: 验证集真实标签列表
            lexicon: 已初始化的 LexiconAnalyzer
            bert: 已初始化的 BERTAnalyzer
            candidates: 候选阈值列表，默认 [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]

        Returns:
            (最优阈值, 最优 Accuracy)
        """
        if candidates is None:
            candidates = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]

        # 预计算所有样本的词典和 BERT 结果（避免重复推理）
        lex_results = [lexicon.analyze_3class(t) for t in texts]
        bert_results = [bert.analyze(t) for t in texts]

        best_threshold = 0.55
        best_acc = 0.0

        for thr in candidates:
            correct = 0
            for i in range(len(texts)):
                lex_r = lex_results[i]
                bert_r = bert_results[i]

                # 模拟级联
                if lex_r['high_confidence'] and lex_r['confidence'] >= 0.7:
                    pred = lex_r['label']
                else:
                    pred = bert_r['label']
                    if bert_r['confidence'] < thr:
                        if lex_r['label'] == 2 and pred != 2:
                            pred = 2

                if pred == y_true[i]:
                    correct += 1

            acc = correct / len(texts)
            if acc > best_acc:
                best_acc = acc
                best_threshold = thr

        return best_threshold, best_acc


# ==================== 3. 指标计算 ====================

def compute_metrics(y_true: List[int], y_pred: List[int], classes=(0, 1, 2)) -> Dict:
    """计算三分类指标"""
    n = len(y_true)
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / n if n else 0

    precision = {}
    recall = {}
    f1 = {}

    for c in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == c and p == c)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != c and p == c)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == c and p != c)

        p_val = tp / (tp + fp) if (tp + fp) > 0 else 0
        r_val = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_val = 2 * p_val * r_val / (p_val + r_val) if (p_val + r_val) > 0 else 0

        name = LABEL_CN[c]
        precision[name] = p_val
        recall[name] = r_val
        f1[name] = f1_val

    macro_p = np.mean(list(precision.values()))
    macro_r = np.mean(list(recall.values()))
    macro_f1 = np.mean(list(f1.values()))

    # 混淆矩阵 3x3
    cm = [[0] * len(classes) for _ in classes]
    for t, p in zip(y_true, y_pred):
        if t in classes and p in classes:
            cm[list(classes).index(t)][list(classes).index(p)] += 1

    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'macro_precision': float(macro_p),
        'macro_recall': float(macro_r),
        'macro_f1': float(macro_f1),
        'confusion_matrix': cm,
        'total': n,
        'correct': correct,
    }


# ==================== 4. 主评估 ====================

def evaluate(df: pd.DataFrame, threshold: float = 0.7) -> Dict:
    cascade = CascadeAnalyzer(threshold=threshold)

    y_true = df['label'].tolist()
    texts = df['review'].tolist()
    total = len(texts)

    lex_preds, bert_preds, cas_preds = [], [], []
    lex_times, bert_times, cas_times = [], [], []
    cas_methods = []

    logger.info(f'开始评估 {total} 条 (θ={threshold}) ...')

    for i, text in enumerate(texts):
        if (i + 1) % 2000 == 0:
            logger.info(f'  进度: {i+1}/{total}')

        # 纯词典
        lex_r = cascade.lexicon.analyze(text)
        lex_preds.append(lex_r['label'])
        lex_times.append(lex_r['time_ms'])

        # 纯 BERT
        bert_r = cascade.bert.analyze(text)
        bert_preds.append(bert_r['label'])
        bert_times.append(bert_r['time_ms'])

        # 级联
        cas_r = cascade.analyze(text)
        cas_preds.append(cas_r['label'])
        cas_times.append(cas_r['time_ms'])
        cas_methods.append(cas_r['method'])

    # 指标
    lex_m = compute_metrics(y_true, lex_preds)
    bert_m = compute_metrics(y_true, bert_preds)
    cas_m = compute_metrics(y_true, cas_preds)

    # 将 bert+fallback_neutral 归入 bert 路径
    bert_path_mask = [m.startswith('bert') for m in cas_methods]
    lex_path_mask = [m == 'lexicon' for m in cas_methods]
    fallback_n = sum(1 for m in cas_methods if m == 'bert+fallback_neutral')

    lex_path_n = sum(lex_path_mask)
    bert_path_n = sum(bert_path_mask)
    lex_ratio = lex_path_n / total
    bert_ratio = bert_path_n / total

    lex_path_ok = sum(1 for t, p, is_lex in zip(y_true, cas_preds, lex_path_mask)
                      if is_lex and t == p)
    bert_path_ok = sum(1 for t, p, is_bert in zip(y_true, cas_preds, bert_path_mask)
                       if is_bert and t == p)

    return {
        'dataset': {
            'total': total,
            'per_class': {LABEL_CN[c]: int((df['label'] == c).sum()) for c in [0, 1, 2]},
        },
        'threshold': threshold,
        'lexicon_only': {**lex_m, 'avg_time_ms': float(np.mean(lex_times))},
        'bert_only': {**bert_m, 'avg_time_ms': float(np.mean(bert_times))},
        'cascade': {
            **cas_m,
            'avg_time_ms': float(np.mean(cas_times)),
            'lexicon_path_ratio': lex_ratio,
            'bert_path_ratio': bert_ratio,
            'lexicon_path_samples': lex_path_n,
            'lexicon_path_accuracy': lex_path_ok / lex_path_n if lex_path_n else 0,
            'bert_path_samples': bert_path_n,
            'bert_path_accuracy': bert_path_ok / bert_path_n if bert_path_n else 0,
            'fallback_neutral_samples': fallback_n,
        },
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    }


# ==================== 5. 报告输出 ====================

def print_report(r: Dict):
    ds = r['dataset']
    θ = r['threshold']

    print()
    print('=' * 72)
    print('   混合级联策略三分类评估报告')
    print('=' * 72)
    print(f'\n测试集: {ds["total"]} 条  '
          + '  '.join(f'{n}={c}' for n, c in ds['per_class'].items()))
    print(f'级联阈值 θ = {θ}')

    # 各方法详细指标
    for title, key in [('纯词典 (Lexicon-only)', 'lexicon_only'),
                       ('纯 ChineseBERT', 'bert_only'),
                       (f'混合级联 (θ={θ})', 'cascade')]:
        m = r[key]
        print(f'\n{"─" * 72}')
        print(f'  {title}')
        print(f'{"─" * 72}')
        print(f'  Accuracy:        {m["accuracy"]:.4f}  ({m["accuracy"]:.1%})')
        print(f'  Macro Precision: {m["macro_precision"]:.4f}')
        print(f'  Macro Recall:    {m["macro_recall"]:.4f}')
        print(f'  Macro F1:        {m["macro_f1"]:.4f}')
        print(f'  平均延迟:         {m["avg_time_ms"]:.2f} ms/条')

        print(f'\n  {"类别":<10} {"Precision":>10} {"Recall":>10} {"F1":>10}')
        for cls_name in ['负面', '正面', '中性']:
            print(f'  {cls_name:<10} {m["precision"][cls_name]:>10.4f} '
                  f'{m["recall"][cls_name]:>10.4f} {m["f1"][cls_name]:>10.4f}')

        # 混淆矩阵
        print(f'\n  混淆矩阵 (行=真实, 列=预测):')
        print(f'  {"":>10} {"负面":>8} {"正面":>8} {"中性":>8}')
        for i, row_name in enumerate(['负面', '正面', '中性']):
            row = m['confusion_matrix'][i]
            print(f'  {row_name:>10} {row[0]:>8} {row[1]:>8} {row[2]:>8}')

    # 级联分路径
    cas = r['cascade']
    print(f'\n{"─" * 72}')
    print(f'  级联分路径统计')
    print(f'{"─" * 72}')
    print(f'  词典直出: {cas["lexicon_path_samples"]:>6} 条 '
          f'({cas["lexicon_path_ratio"]:.1%})  准确率={cas["lexicon_path_accuracy"]:.4f}')
    print(f'  BERT调用: {cas["bert_path_samples"]:>6} 条 '
          f'({cas["bert_path_ratio"]:.1%})  准确率={cas["bert_path_accuracy"]:.4f}')
    if cas.get('fallback_neutral_samples', 0) > 0:
        print(f'  其中 BERT 低置信回退中性: {cas["fallback_neutral_samples"]} 条')

    # 对比总结表
    lex = r['lexicon_only']
    bert = r['bert_only']
    print(f'\n{"=" * 72}')
    print(f'  对比总结')
    print(f'{"=" * 72}')
    print(f'  {"方法":<20} {"Accuracy":>10} {"Macro F1":>10} {"延迟(ms)":>10} {"相对速度":>10}')
    print(f'  {"─" * 60}')

    bert_t = bert['avg_time_ms']
    rows = [
        ('纯词典',           lex['accuracy'],  lex['macro_f1'],  lex['avg_time_ms']),
        ('纯 ChineseBERT',   bert['accuracy'], bert['macro_f1'], bert['avg_time_ms']),
        (f'混合级联(θ={θ})',  cas['accuracy'],  cas['macro_f1'],  cas['avg_time_ms']),
    ]
    for name, acc, f1, t in rows:
        speed = f'{bert_t / t:.1f}x' if t > 0 else '-'
        print(f'  {name:<20} {acc:>10.1%} {f1:>10.4f} {t:>10.2f} {speed:>10}')

    print(f'\n{"=" * 72}')
    print()


# ==================== main ====================

def main():
    parser = argparse.ArgumentParser(description='混合级联策略三分类评估')
    parser.add_argument('--threshold', type=float, default=0.7, help='级联阈值 θ')
    parser.add_argument('--output', type=str, default=None, help='JSON 输出路径')
    args = parser.parse_args()

    # 1. 加载
    df = load_test_set()

    # 2. 评估
    results = evaluate(df, threshold=args.threshold)

    # 3. 报告
    print_report(results)

    # 4. 保存 JSON
    out = args.output or str(BACKEND_DIR / 'scripts' / 'evaluate_cascade_3class_results.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f'结果已保存: {out}')


if __name__ == '__main__':
    main()
