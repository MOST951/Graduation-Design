#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChineseBERT batch_size 推理性能基准测试
用于论文第 4 章 BERT 深度模型小节的批量推理性能数据。

测试 batch_size ∈ {1, 8, 16, 32, 64, 128}，记录平均每条耗时。
"""
import os, sys, time, random, json
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.model_singleton import get_bert_tokenizer_and_model

# 模型 singleton 返回 (device, tokenizer, model)
tokenizer, model, DEVICE = get_bert_tokenizer_and_model()
print(f"[Device] {DEVICE}")
model.eval()

# 准备测试样本：从测试集采样
test_path = "/app/backend/scripts/test_set_3class_10k.csv"
samples = []
if os.path.exists(test_path):
    import csv
    with open(test_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            samples.append(row.get("text") or row.get("content") or "")
            if len(samples) >= 1000:
                break

if not samples:
    # fallback: 生成合成微博文本
    samples = [
        "今天的天气真好，心情非常愉快！",
        "这个新闻让人感到非常愤怒和失望。",
        "学校举办了一场普通的活动，没什么特别的。",
        "感谢大家一直以来的支持和帮助！",
        "这部电影简直就是浪费时间。",
    ] * 200

print(f"[Samples] {len(samples)} 条")

def benchmark_batch(bs: int, n_total: int = 320) -> float:
    """跑 n_total 条文本，按 batch_size=bs 推理，返回平均每条耗时(ms)"""
    n_total = max(n_total, bs * 4)
    texts = (samples * (n_total // len(samples) + 1))[:n_total]

    # warmup
    with torch.no_grad():
        for i in range(0, min(bs * 2, len(texts)), bs):
            batch = texts[i:i + bs]
            enc = tokenizer(batch, padding=True, truncation=True, max_length=128, return_tensors="pt").to(DEVICE)
            _ = model(**enc)
    if DEVICE.type == "cuda":
        torch.cuda.synchronize()

    start = time.perf_counter()
    with torch.no_grad():
        for i in range(0, n_total, bs):
            batch = texts[i:i + bs]
            enc = tokenizer(batch, padding=True, truncation=True, max_length=128, return_tensors="pt").to(DEVICE)
            _ = model(**enc)
    if DEVICE.type == "cuda":
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    return (elapsed / n_total) * 1000.0  # ms/sample

results = {}
for bs in [1, 8, 16, 32, 64, 128]:
    t = benchmark_batch(bs)
    results[bs] = t
    print(f"[bs={bs:>3}]  {t:.3f} ms/条")

baseline = results[1]
print("\n=== 加速比汇总 (相对 batch_size=1) ===")
for bs, t in results.items():
    print(f"  bs={bs:>3}  {t:.2f} ms/条  加速 {baseline / t:.2f}×")

out_path = "/app/backend/scripts/batch_size_benchmark_results.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({
        "device": str(DEVICE),
        "model": "hfl/chinese-bert-wwm-ext (本地)",
        "results_ms_per_sample": results,
        "speedup_vs_bs1": {bs: baseline / t for bs, t in results.items()}
    }, f, indent=2, ensure_ascii=False)
print(f"\n结果保存: {out_path}")
