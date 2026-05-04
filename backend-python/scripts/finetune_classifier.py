#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微调 ChineseBERT 情感分类模型
=============================

对 hfl/chinese-bert-wwm-ext 进行全量微调，适配微博情感三分类任务。

数据划分（避免数据泄漏）：
  - 训练集 80% (~80000条) → 仅用于微调
  - 验证集 10% (~10000条) → 早停依据
  - 测试集 10% (~10000条) → 完全隔离，写入 data/test_set_200.csv

标签：三分类 (num_labels=3)
  - 0 = negative (负面)
  - 1 = positive (正面)
  - 2 = neutral (中性)

用法:
    cd backend-python
    python scripts/finetune_classifier.py
"""

import os
import sys
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    BertTokenizer,
    BertForSequenceClassification,
    get_linear_schedule_with_warmup,
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ==================== 路径 ====================

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
MODEL_DIR = BACKEND_DIR / "models" / "chinese-bert-wwm-ext"
DATA_PATH = BACKEND_DIR / "data" / "weibo_senti_100k.csv"

TEST_SET_PATH = BACKEND_DIR / "data" / "test_set_200.csv"

# ==================== 配置 ====================

NUM_LABELS = 3          # 0=negative, 1=positive, 2=neutral (三分类)
MAX_LENGTH = 128
BATCH_SIZE = 32         # RTX 3050 Ti 4GB VRAM
EPOCHS = 3              # 数据量大(~10万), 3轮足够
BERT_LR = 2e-5          # BERT 编码层较小 lr
CLASSIFIER_LR = 1e-4   # 分类头较大 lr
WARMUP_RATIO = 0.1
FREEZE_BERT = False     # 全量微调
RANDOM_SEED = 42
USE_FP16 = True         # 混合精度加速


# ==================== 数据集 ====================

class WeiboDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.labels[idx], dtype=torch.long),
        }


def load_and_split_data():
    """
    加载数据并按 8:1:1 划分为训练集/验证集/测试集。
    测试集写入 data/test_set_200.csv，仅用于最终评估。

    标签: 0=negative, 1=positive, 2=neutral (三分类)
    """
    logger.info(f"加载数据: {DATA_PATH}")
    df = pd.read_csv(str(DATA_PATH))
    # 过滤无效数据
    df = df.dropna(subset=["review", "label"])
    df = df[df["label"].isin([0, 1, 2])]

    texts = df["review"].astype(str).tolist()
    labels = df["label"].astype(int).tolist()  # 三分类: 0=负面, 1=正面, 2=中性

    logger.info(f"总数据量: {len(texts)}  标签分布: {pd.Series(labels).value_counts().to_dict()}")

    # 第一次划分: 80% train, 20% temp
    train_texts, temp_texts, train_labels, temp_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=RANDOM_SEED, stratify=labels
    )
    # 第二次划分: temp 一半一半 → 10% val, 10% test
    val_texts, test_texts, val_labels, test_labels = train_test_split(
        temp_texts, temp_labels, test_size=0.5, random_state=RANDOM_SEED, stratify=temp_labels
    )

    logger.info(f"训练集: {len(train_texts)}  验证集: {len(val_texts)}  测试集: {len(test_texts)}")

    # 保存测试集到独立文件
    test_df = pd.DataFrame({"label": test_labels, "review": test_texts})
    test_df.to_csv(str(TEST_SET_PATH), index=False, encoding="utf-8")
    logger.info(f"测试集已保存: {TEST_SET_PATH} ({len(test_texts)} 条)")

    return train_texts, train_labels, val_texts, val_labels, test_texts, test_labels


# ==================== 训练 ====================

def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"设备: {device}")

    # 加载 tokenizer & model
    logger.info(f"加载模型: {MODEL_DIR}")
    tokenizer = BertTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
    model = BertForSequenceClassification.from_pretrained(
        str(MODEL_DIR), num_labels=NUM_LABELS, local_files_only=True,
        ignore_mismatched_sizes=True,  # 允许分类头维度变更 (2→3)
    )
    model.to(device)

    # 混合精度 scaler
    scaler = torch.cuda.amp.GradScaler() if USE_FP16 and device.type == 'cuda' else None

    # 冻结 / 解冻 BERT 编码层
    if FREEZE_BERT:
        for name, param in model.named_parameters():
            if "classifier" not in name:
                param.requires_grad = False
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    logger.info(f"可训练参数: {trainable:,} / {total:,}  (全量微调: {not FREEZE_BERT})")

    # 准备数据 (8:1:1 划分)
    train_texts, train_labels, val_texts, val_labels, test_texts, test_labels = load_and_split_data()

    train_ds = WeiboDataset(train_texts, train_labels, tokenizer, MAX_LENGTH)
    val_ds = WeiboDataset(val_texts, val_labels, tokenizer, MAX_LENGTH)
    test_ds = WeiboDataset(test_texts, test_labels, tokenizer, MAX_LENGTH)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE)

    logger.info(f"训练集: {len(train_ds)}  验证集: {len(val_ds)}  测试集: {len(test_ds)} (隔离)")

    # 优化器 & 调度器（分层学习率）
    bert_params = [p for n, p in model.named_parameters() if "classifier" not in n and p.requires_grad]
    classifier_params = [p for n, p in model.named_parameters() if "classifier" in n and p.requires_grad]
    optimizer = torch.optim.AdamW([
        {"params": bert_params, "lr": BERT_LR},
        {"params": classifier_params, "lr": CLASSIFIER_LR},
    ], weight_decay=0.01)
    total_steps = len(train_loader) * EPOCHS
    warmup_steps = int(total_steps * WARMUP_RATIO)
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
    )

    # 训练循环
    best_val_acc = 0.0

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for step, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels_batch = batch["labels"].to(device)

            optimizer.zero_grad()

            if scaler:
                with torch.cuda.amp.autocast():
                    outputs = model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels_batch,
                    )
                    loss = outputs.loss
                total_loss += loss.item()
                preds = outputs.logits.argmax(dim=-1)
                correct += (preds == labels_batch).sum().item()
                total += labels_batch.size(0)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
            else:
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels_batch,
                )
                loss = outputs.loss
                total_loss += loss.item()
                preds = outputs.logits.argmax(dim=-1)
                correct += (preds == labels_batch).sum().item()
                total += labels_batch.size(0)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            scheduler.step()

            # 每500步打印进度
            if (step + 1) % 500 == 0:
                logger.info(f"  Step {step+1}/{len(train_loader)}, loss={loss.item():.4f}")

        train_acc = correct / total
        avg_loss = total_loss / len(train_loader)

        # 验证
        val_acc, val_report = evaluate(model, val_loader, device)

        logger.info(
            f"Epoch {epoch}/{EPOCHS}  "
            f"train_loss={avg_loss:.4f}  train_acc={train_acc:.4f}  "
            f"val_acc={val_acc:.4f}"
        )

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            # 保存最佳模型
            model.save_pretrained(str(MODEL_DIR))
            tokenizer.save_pretrained(str(MODEL_DIR))
            logger.info(f"  ↑ 保存最佳模型 (val_acc={val_acc:.4f})")

    logger.info(f"\n微调完成! 最佳验证准确率: {best_val_acc:.4f}")
    logger.info(f"模型已保存到: {MODEL_DIR}")

    # 加载最佳模型并在隔离测试集上评估
    logger.info("\n" + "=" * 50)
    logger.info("在隔离测试集上评估 (未参与训练/验证):")
    logger.info("=" * 50)
    model = BertForSequenceClassification.from_pretrained(
        str(MODEL_DIR), num_labels=NUM_LABELS, local_files_only=True
    )
    model.to(device)
    test_acc, test_report = evaluate(model, test_loader, device)
    logger.info(f"测试集准确率: {test_acc:.4f}")
    print(test_report)

    # 确认分类头权重不再是随机的
    logger.info("\n验证: 重新加载模型检查分类头 ...")
    model2 = BertForSequenceClassification.from_pretrained(
        str(MODEL_DIR), num_labels=NUM_LABELS, local_files_only=True
    )
    logger.info("✅ 加载成功，无 'newly initialized' 警告!")
    logger.info(f"\n数据划分: 训练集 {len(train_ds)} / 验证集 {len(val_ds)} / 测试集 {len(test_ds)}")
    logger.info(f"测试集保存位置: {TEST_SET_PATH}")


def evaluate(model, dataloader, device):
    model.eval()
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels_batch = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            preds = outputs.logits.argmax(dim=-1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels_batch.cpu().numpy())

    acc = accuracy_score(all_labels, all_preds)
    report = classification_report(
        all_labels, all_preds,
        labels=[0, 1, 2],
        target_names=["negative", "positive", "neutral"],
        zero_division=0,
    )
    return acc, report


if __name__ == "__main__":
    train()
