#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微调 ChineseBERT v3 — Focal Loss 版
====================================

与 v2 完全相同的超参数, 唯一变化: 损失函数 CrossEntropy → FocalLoss(γ=2.0)
  - max_length=192, batch_size=24, lr=3e-5, warmup=0.05, epochs=3
  - Focal Loss gamma=2.0, alpha=1/3 per class (均衡)
  - 输出: models/chinese-bert-wwm-ext-v3/
  - 日志: scripts/training_v3.log

用法:
  cd backend-python
  python -u scripts/finetune_classifier_v3.py 2>&1 | Tee-Object -FilePath scripts/training_v3.log
"""

import os
import sys
import time
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from transformers import (
    BertTokenizer,
    BertForSequenceClassification,
    get_linear_schedule_with_warmup,
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, f1_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ==================== 路径 ====================
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
BASELINE_MODEL_DIR = BACKEND_DIR / "models" / "chinese-bert-wwm-ext-baseline"
OUTPUT_MODEL_DIR = BACKEND_DIR / "models" / "chinese-bert-wwm-ext-v3"
DATA_PATH = BACKEND_DIR / "data" / "weibo_senti_100k.csv"

# ==================== 配置 ====================
NUM_LABELS = 3
MAX_LENGTH = 192
BATCH_SIZE = 24
EPOCHS = 3
BERT_LR = 3e-5
CLASSIFIER_LR = 1e-4
WARMUP_RATIO = 0.05
RANDOM_SEED = 42
USE_FP16 = True
EARLY_STOP_PATIENCE = 2

# Focal Loss 参数
FOCAL_GAMMA = 2.0
FOCAL_ALPHA = torch.tensor([1.0 / 3, 1.0 / 3, 1.0 / 3])  # 三类均衡


# ==================== Focal Loss ====================
class FocalLoss(nn.Module):
    """
    Focal Loss for multi-class classification.
    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)

    gamma > 0 降低简单样本权重, 聚焦难分样本
    """
    def __init__(self, gamma=2.0, alpha=None):
        super().__init__()
        self.gamma = gamma
        if alpha is not None:
            self.register_buffer("alpha", alpha.float())
        else:
            self.alpha = None

    def forward(self, inputs, targets):
        ce_loss = F.cross_entropy(inputs, targets, reduction='none')
        pt = torch.exp(-ce_loss)
        focal_loss = ((1 - pt) ** self.gamma) * ce_loss
        if self.alpha is not None:
            alpha = self.alpha.to(inputs.device)
            focal_loss = alpha[targets] * focal_loss
        return focal_loss.mean()


# ==================== 数据集 (预分词版) ====================
def pretokenize(texts, labels, tokenizer, max_length, desc="tokenizing"):
    """一次性将所有文本编码为张量, 避免训练时逐条分词的瓶颈。"""
    logger.info(f"预分词 {len(texts)} 条 ({desc}, max_length={max_length}) ...")
    t0 = time.time()
    enc = tokenizer(
        texts,
        truncation=True,
        max_length=max_length,
        padding="max_length",
        return_tensors="pt",
    )
    labels_t = torch.tensor(labels, dtype=torch.long)
    elapsed = time.time() - t0
    logger.info(f"  预分词完成: {elapsed:.1f}s  input_ids shape={enc['input_ids'].shape}")
    return torch.utils.data.TensorDataset(enc["input_ids"], enc["attention_mask"], labels_t)


def load_and_split_data():
    logger.info(f"加载数据: {DATA_PATH}")
    df = pd.read_csv(str(DATA_PATH))
    df = df.dropna(subset=["review", "label"])
    df = df[df["label"].isin([0, 1, 2])]

    texts = df["review"].astype(str).tolist()
    labels = df["label"].astype(int).tolist()

    logger.info(f"总数据量: {len(texts)}  标签分布: {pd.Series(labels).value_counts().to_dict()}")

    # 与 v1/v2 相同的 seed → 相同的测试集, 保证可比性
    train_texts, temp_texts, train_labels, temp_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=RANDOM_SEED, stratify=labels
    )
    val_texts, test_texts, val_labels, test_labels = train_test_split(
        temp_texts, temp_labels, test_size=0.5, random_state=RANDOM_SEED, stratify=temp_labels
    )

    logger.info(f"训练集: {len(train_texts)}  验证集: {len(val_texts)}  测试集: {len(test_texts)}")
    return train_texts, train_labels, val_texts, val_labels, test_texts, test_labels


def evaluate(model, dataloader, device):
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for batch in dataloader:
            input_ids, attention_mask, labels_batch = (
                batch[0].to(device), batch[1].to(device), batch[2].to(device)
            )
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            preds = outputs.logits.argmax(dim=-1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels_batch.cpu().numpy())

    acc = accuracy_score(all_labels, all_preds)
    macro_f1 = f1_score(all_labels, all_preds, average='macro')
    report = classification_report(
        all_labels, all_preds,
        labels=[0, 1, 2],
        target_names=["negative", "positive", "neutral"],
        zero_division=0, digits=4,
    )
    return acc, macro_f1, report


def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"设备: {device}")
    logger.info(f"配置: max_length={MAX_LENGTH}, batch_size={BATCH_SIZE}, epochs={EPOCHS}, "
                f"bert_lr={BERT_LR}, warmup_ratio={WARMUP_RATIO}")
    logger.info(f"损失函数: FocalLoss(γ={FOCAL_GAMMA}, α=[1/3,1/3,1/3])")

    # 加载 tokenizer & model (从 baseline 备份加载)
    logger.info(f"加载基础模型: {BASELINE_MODEL_DIR}")
    tokenizer = BertTokenizer.from_pretrained(str(BASELINE_MODEL_DIR), local_files_only=True)
    model = BertForSequenceClassification.from_pretrained(
        str(BASELINE_MODEL_DIR), num_labels=NUM_LABELS, local_files_only=True,
        ignore_mismatched_sizes=True,
    )
    model.to(device)

    scaler = torch.cuda.amp.GradScaler() if USE_FP16 and device.type == 'cuda' else None

    # Focal Loss
    criterion = FocalLoss(gamma=FOCAL_GAMMA, alpha=FOCAL_ALPHA)
    criterion = criterion.to(device)
    logger.info(f"FocalLoss 已创建: gamma={FOCAL_GAMMA}, alpha={FOCAL_ALPHA.tolist()}")

    # 数据 — 预分词
    train_texts, train_labels, val_texts, val_labels, test_texts, test_labels = load_and_split_data()
    train_ds = pretokenize(train_texts, train_labels, tokenizer, MAX_LENGTH, desc="train")
    val_ds = pretokenize(val_texts, val_labels, tokenizer, MAX_LENGTH, desc="val")
    test_ds = pretokenize(test_texts, test_labels, tokenizer, MAX_LENGTH, desc="test")
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              pin_memory=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, pin_memory=True)

    # 优化器 - 分层学习率
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

    OUTPUT_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    best_val_acc = 0.0
    best_val_f1 = 0.0
    patience = 0

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        epoch_start = time.time()

        for step, batch in enumerate(train_loader):
            input_ids, attention_mask, labels_batch = (
                batch[0].to(device), batch[1].to(device), batch[2].to(device)
            )

            optimizer.zero_grad()

            if scaler:
                with torch.cuda.amp.autocast():
                    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                    loss = criterion(outputs.logits, labels_batch)
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
                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                loss = criterion(outputs.logits, labels_batch)
                total_loss += loss.item()
                preds = outputs.logits.argmax(dim=-1)
                correct += (preds == labels_batch).sum().item()
                total += labels_batch.size(0)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            scheduler.step()

            if (step + 1) % 500 == 0:
                logger.info(f"  Epoch {epoch} Step {step+1}/{len(train_loader)}, loss={loss.item():.4f}")

        train_acc = correct / total
        avg_loss = total_loss / len(train_loader)
        epoch_elapsed = time.time() - epoch_start

        # 验证
        val_acc, val_f1, val_report = evaluate(model, val_loader, device)

        logger.info(
            f"Epoch {epoch}/{EPOCHS}  "
            f"train_loss={avg_loss:.4f}  train_acc={train_acc:.4f}  "
            f"val_acc={val_acc:.4f}  val_f1={val_f1:.4f}  time={epoch_elapsed:.0f}s"
        )

        # 保存最佳模型 (以 Macro F1 为准)
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_val_acc = val_acc
            model.save_pretrained(str(OUTPUT_MODEL_DIR))
            tokenizer.save_pretrained(str(OUTPUT_MODEL_DIR))
            logger.info(f"  ↑ 保存最佳模型 (val_f1={val_f1:.4f}, val_acc={val_acc:.4f})")
            patience = 0
        else:
            patience += 1
            logger.info(f"  未提升 (patience={patience}/{EARLY_STOP_PATIENCE})")
            if patience >= EARLY_STOP_PATIENCE:
                logger.info(f"  早停触发, 停止训练")
                break

    logger.info(f"\n微调完成! 最佳 val_f1={best_val_f1:.4f}, val_acc={best_val_acc:.4f}")

    # 在测试集上评估最佳模型
    logger.info("\n" + "=" * 60)
    logger.info("在隔离测试集上评估最佳模型:")
    logger.info("=" * 60)
    best_model = BertForSequenceClassification.from_pretrained(
        str(OUTPUT_MODEL_DIR), num_labels=NUM_LABELS, local_files_only=True
    )
    best_model.to(device)
    test_acc, test_f1, test_report = evaluate(best_model, test_loader, device)
    logger.info(f"测试集 Accuracy: {test_acc:.4f}")
    logger.info(f"测试集 Macro F1: {test_f1:.4f}")
    print(test_report)


if __name__ == "__main__":
    train()
