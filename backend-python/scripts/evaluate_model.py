#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用模型评估脚本
================

在 10,000 条隔离测试集上评估指定模型目录, 输出:
  - Accuracy
  - 各类别 P/R/F1
  - Macro F1
  - 混淆矩阵
  - 与基线 (chinese-bert-wwm-ext-baseline) 的对比

用法:
  cd backend-python
  python scripts/evaluate_model.py --model-dir models/chinese-bert-wwm-ext-v2
  python scripts/evaluate_model.py --model-dir models/chinese-bert-wwm-ext-v3
  python scripts/evaluate_model.py --model-dir models/chinese-bert-wwm-ext-baseline
"""

import argparse
import time
import logging
from pathlib import Path

import pandas as pd
import torch
from torch.utils.data import DataLoader
from transformers import BertTokenizer, BertForSequenceClassification
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix,
    f1_score,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
DATA_PATH = BACKEND_DIR / "data" / "weibo_senti_100k.csv"
BASELINE_DIR = BACKEND_DIR / "models" / "chinese-bert-wwm-ext-baseline"

NUM_LABELS = 3
MAX_LENGTH = 192
BATCH_SIZE = 64
RANDOM_SEED = 42
CLASS_NAMES = ["negative", "positive", "neutral"]


def get_test_split():
    """使用与训练脚本完全一致的 seed 和比例, 还原出 10,000 条测试集。"""
    df = pd.read_csv(str(DATA_PATH))
    df = df.dropna(subset=["review", "label"])
    df = df[df["label"].isin([0, 1, 2])]
    texts = df["review"].astype(str).tolist()
    labels = df["label"].astype(int).tolist()

    _, temp_texts, _, temp_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=RANDOM_SEED, stratify=labels
    )
    _, test_texts, _, test_labels = train_test_split(
        temp_texts, temp_labels, test_size=0.5, random_state=RANDOM_SEED, stratify=temp_labels
    )
    return test_texts, test_labels


def pretokenize(texts, tokenizer):
    logger.info(f"预分词 {len(texts)} 条 (max_length={MAX_LENGTH}) ...")
    t0 = time.time()
    enc = tokenizer(
        texts,
        truncation=True,
        max_length=MAX_LENGTH,
        padding="max_length",
        return_tensors="pt",
    )
    logger.info(f"  预分词完成: {time.time() - t0:.1f}s")
    return enc


def predict(model, enc, device):
    dataset = torch.utils.data.TensorDataset(enc["input_ids"], enc["attention_mask"])
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, pin_memory=True)
    all_preds = []
    all_probs = []
    model.eval()
    with torch.no_grad():
        for batch in loader:
            ids, mask = batch[0].to(device), batch[1].to(device)
            logits = model(input_ids=ids, attention_mask=mask).logits
            probs = torch.softmax(logits, dim=-1)
            preds = logits.argmax(dim=-1)
            all_preds.extend(preds.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())
    return all_preds, all_probs


def evaluate_single(model_dir: Path, test_texts, test_labels, device):
    """评估单个模型, 返回指标字典。"""
    logger.info(f"加载模型: {model_dir}")
    tokenizer = BertTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = BertForSequenceClassification.from_pretrained(
        str(model_dir), num_labels=NUM_LABELS, local_files_only=True,
        ignore_mismatched_sizes=True,
    )
    model.to(device)

    enc = pretokenize(test_texts, tokenizer)

    t0 = time.time()
    preds, probs = predict(model, enc, device)
    infer_time = time.time() - t0

    acc = accuracy_score(test_labels, preds)
    macro_f1 = f1_score(test_labels, preds, average='macro')
    p, r, f1, sup = precision_recall_fscore_support(
        test_labels, preds, labels=[0, 1, 2], zero_division=0
    )
    cm = confusion_matrix(test_labels, preds, labels=[0, 1, 2])
    report = classification_report(
        test_labels, preds,
        labels=[0, 1, 2],
        target_names=CLASS_NAMES,
        zero_division=0, digits=4,
    )
    return {
        "acc": acc,
        "macro_f1": macro_f1,
        "precision": p,
        "recall": r,
        "f1": f1,
        "support": sup,
        "confusion_matrix": cm,
        "report": report,
        "infer_time": infer_time,
    }


def print_results(name, metrics):
    print("\n" + "=" * 64)
    print(f"  模型: {name}")
    print("=" * 64)
    print(f"  Accuracy:  {metrics['acc']:.4f}  ({metrics['acc']*100:.2f}%)")
    print(f"  Macro F1:  {metrics['macro_f1']:.4f}")
    print(f"  推理耗时:  {metrics['infer_time']:.1f}s")
    print()
    print(metrics["report"])
    print("  混淆矩阵 (行=真实, 列=预测):")
    print(f"  {'':>12s}  {'neg':>6s}  {'pos':>6s}  {'neu':>6s}")
    for i, label in enumerate(CLASS_NAMES):
        row = "  ".join(f"{v:6d}" for v in metrics["confusion_matrix"][i])
        print(f"  {label:>12s}  {row}")
    print()


def print_comparison(target_name, target_m, baseline_m):
    print("=" * 64)
    print(f"  对比: {target_name} vs baseline")
    print("=" * 64)
    header = f"  {'指标':>14s}  {'Baseline':>10s}  {target_name:>10s}  {'Δ':>8s}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    rows = [
        ("Accuracy", baseline_m["acc"], target_m["acc"]),
        ("Macro F1", baseline_m["macro_f1"], target_m["macro_f1"]),
    ]
    for i, cn in enumerate(CLASS_NAMES):
        rows.append((f"{cn} P", baseline_m["precision"][i], target_m["precision"][i]))
        rows.append((f"{cn} R", baseline_m["recall"][i], target_m["recall"][i]))
        rows.append((f"{cn} F1", baseline_m["f1"][i], target_m["f1"][i]))

    for label, bv, tv in rows:
        delta = tv - bv
        sign = "+" if delta >= 0 else ""
        print(f"  {label:>14s}  {bv:10.4f}  {tv:10.4f}  {sign}{delta:7.4f}")
    print()


def main():
    parser = argparse.ArgumentParser(description="通用BERT模型评估")
    parser.add_argument("--model-dir", type=str, required=True,
                        help="模型目录路径 (例: models/chinese-bert-wwm-ext-v2)")
    parser.add_argument("--no-baseline", action="store_true",
                        help="不与基线对比")
    args = parser.parse_args()

    model_path = Path(args.model_dir)
    if not model_path.is_absolute():
        model_path = BACKEND_DIR / args.model_dir

    if not model_path.exists():
        logger.error(f"模型目录不存在: {model_path}")
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"设备: {device}")

    # 获取测试集
    test_texts, test_labels = get_test_split()
    logger.info(f"测试集: {len(test_texts)} 条  标签分布: {pd.Series(test_labels).value_counts().to_dict()}")

    # 评估目标模型
    target_metrics = evaluate_single(model_path, test_texts, test_labels, device)
    print_results(model_path.name, target_metrics)

    # 评估基线并对比
    is_baseline = model_path.resolve() == BASELINE_DIR.resolve()
    if not args.no_baseline and not is_baseline and BASELINE_DIR.exists():
        logger.info("评估基线模型以进行对比 ...")
        baseline_metrics = evaluate_single(BASELINE_DIR, test_texts, test_labels, device)
        print_results("baseline", baseline_metrics)
        print_comparison(model_path.name, target_metrics, baseline_metrics)
    elif is_baseline:
        logger.info("当前评估的就是基线模型, 跳过对比。")


if __name__ == "__main__":
    main()
