"""
ChineseBERT情感分析微调模块
============================

功能特性：
1. 模型选择：hfl/chinese-bert-wwm-ext预训练模型 + 情感分类头
2. 数据准备：数据增强、类别平衡、微博数据集
3. 微调策略：分层学习率、早停、梯度累积、混合精度
4. 模型评估：准确率、F1、混淆矩阵、ROC曲线

使用示例:
    from backend.models.chinese_bert_sentiment import (
        ChineseBertSentimentModel,
        WeiboSentimentDataset,
        TrainingConfig
    )
    
    # 训练模型
    model = ChineseBertSentimentModel()
    model.train(train_texts, train_labels, val_texts, val_labels)
    
    # 预测
    results = model.predict(["这部电影太好看了！"])
"""
from __future__ import annotations

import os
import json
import logging
import random
import time
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from collections import Counter
from datetime import datetime
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ChineseBertSentiment')

# ==================== 依赖检查 ====================

TORCH_AVAILABLE = False
TRANSFORMERS_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
    from torch.cuda.amp import autocast, GradScaler
    TORCH_AVAILABLE = True
    logger.info(f"PyTorch版本: {torch.__version__}, CUDA: {torch.cuda.is_available()}")
except ImportError:
    torch = None  # 占位，避免 NameError
    nn = None
    F = None
    logger.warning("PyTorch未安装")
    # 提供占位类，使模块定义不报错 (功能在运行时检查 TORCH_AVAILABLE)
    class Dataset:
        pass
    class DataLoader:
        pass

try:
    from transformers import (
        BertTokenizer,
        BertForSequenceClassification,
        BertModel,
        BertConfig,
        AutoTokenizer,
        AutoModelForSequenceClassification,
        get_linear_schedule_with_warmup,
        get_cosine_schedule_with_warmup,
    )
    TRANSFORMERS_AVAILABLE = True
    logger.info("Transformers库已加载")
except ImportError:
    logger.warning("Transformers未安装")


# ==================== 配置类 ====================

@dataclass
class ModelConfig:
    """模型配置"""
    model_name: str = "hfl/chinese-bert-wwm-ext"
    num_labels: int = 3  # positive, neutral, negative
    max_length: int = 128
    dropout_rate: float = 0.1
    hidden_size: int = 768
    
    # 标签映射
    label2id: Dict[str, int] = field(default_factory=lambda: {
        'negative': 0,
        'neutral': 1,
        'positive': 2
    })
    id2label: Dict[int, str] = field(default_factory=lambda: {
        0: 'negative',
        1: 'neutral',
        2: 'positive'
    })


@dataclass
class TrainingConfig:
    """训练配置"""
    # 基础配置
    batch_size: int = 32
    epochs: int = 10
    max_length: int = 128
    
    # 学习率配置（分层学习率）
    bert_learning_rate: float = 2e-5
    classifier_learning_rate: float = 1e-4
    weight_decay: float = 0.01
    
    # 学习率调度
    warmup_ratio: float = 0.1
    scheduler_type: str = 'linear'  # linear, cosine
    
    # 早停配置
    early_stopping_patience: int = 3
    early_stopping_delta: float = 0.001
    
    # 梯度配置
    gradient_accumulation_steps: int = 1
    max_grad_norm: float = 1.0
    
    # 混合精度
    use_fp16: bool = True
    
    # 设备
    device: str = 'auto'  # auto, cuda, cpu
    
    # 保存配置
    save_dir: str = './checkpoints'
    save_best_only: bool = True
    
    # 日志
    logging_steps: int = 100
    eval_steps: int = 500


@dataclass
class DataAugmentConfig:
    """数据增强配置"""
    enable_augmentation: bool = True
    synonym_replace_prob: float = 0.1
    random_delete_prob: float = 0.1
    random_swap_prob: float = 0.1
    back_translation: bool = False  # 需要翻译API
    augment_ratio: float = 0.5  # 增强数据比例


# ==================== 数据集类 ====================

class WeiboSentimentDataset(Dataset):
    """
    微博情感数据集
    
    支持：
    - 文本编码
    - 数据增强
    - 类别平衡采样
    """
    
    def __init__(self, 
                 texts: List[str], 
                 labels: List[int],
                 tokenizer,
                 max_length: int = 128,
                 augment_config: DataAugmentConfig = None):
        """
        初始化数据集
        
        Args:
            texts: 文本列表
            labels: 标签列表 (0=negative, 1=neutral, 2=positive)
            tokenizer: BERT分词器
            max_length: 最大长度
            augment_config: 数据增强配置
        """
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.augment_config = augment_config or DataAugmentConfig(enable_augmentation=False)
        
        # 数据增强
        if self.augment_config.enable_augmentation:
            self._augment_data()
        
        logger.info(f"数据集大小: {len(self.texts)}, 标签分布: {Counter(self.labels)}")
    
    def _augment_data(self):
        """数据增强"""
        augmented_texts = []
        augmented_labels = []
        
        for text, label in zip(self.texts, self.labels):
            # 原始数据
            augmented_texts.append(text)
            augmented_labels.append(label)
            
            # 随机决定是否增强
            if random.random() < self.augment_config.augment_ratio:
                aug_text = self._augment_text(text)
                if aug_text and aug_text != text:
                    augmented_texts.append(aug_text)
                    augmented_labels.append(label)
        
        self.texts = augmented_texts
        self.labels = augmented_labels
        logger.info(f"数据增强后: {len(self.texts)} 条")
    
    def _augment_text(self, text: str) -> str:
        """
        文本增强
        
        方法：
        1. 同义词替换
        2. 随机删除
        3. 随机交换
        """
        words = list(text)
        
        # 同义词替换（简化版）
        if random.random() < self.augment_config.synonym_replace_prob:
            # 这里可以接入同义词词典
            pass
        
        # 随机删除
        if random.random() < self.augment_config.random_delete_prob and len(words) > 5:
            idx = random.randint(0, len(words) - 1)
            words.pop(idx)
        
        # 随机交换
        if random.random() < self.augment_config.random_swap_prob and len(words) > 2:
            idx1, idx2 = random.sample(range(len(words)), 2)
            words[idx1], words[idx2] = words[idx2], words[idx1]
        
        return ''.join(words)
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch未安装，无法使用数据集")
        
        text = self.texts[idx]
        label = self.labels[idx]
        
        # 编码
        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }
    
    def get_class_weights(self):
        """计算类别权重（用于处理类别不平衡）"""
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch未安装，无法计算类别权重")
        
        label_counts = Counter(self.labels)
        total = len(self.labels)
        num_classes = len(label_counts)
        
        weights = []
        for i in range(num_classes):
            count = label_counts.get(i, 1)
            weight = total / (num_classes * count)
            weights.append(weight)
        
        return torch.tensor(weights, dtype=torch.float)
    
    def get_sample_weights(self) -> List[float]:
        """获取样本权重（用于WeightedRandomSampler）"""
        class_weights = self.get_class_weights()
        return [class_weights[label].item() for label in self.labels]


# ==================== 自定义模型 ====================

# 仅在 PyTorch 可用时定义 BertSentimentClassifier
if TORCH_AVAILABLE:
    class BertSentimentClassifier(nn.Module):
        """
        BERT情感分类器
        
        结构：
        - BERT编码器
        - Dropout
        - 全连接分类头
        """
        
        def __init__(self, config: ModelConfig):
            super().__init__()
            
            self.config = config
            
            # 加载预训练BERT
            self.bert = BertModel.from_pretrained(config.model_name)
            
            # 分类头
            self.dropout = nn.Dropout(config.dropout_rate)
            self.classifier = nn.Linear(config.hidden_size, config.num_labels)
            
            # 初始化分类头权重
            self._init_weights()
        
        def _init_weights(self):
            """初始化分类头权重"""
            nn.init.xavier_uniform_(self.classifier.weight)
            nn.init.zeros_(self.classifier.bias)
        
        def forward(self, input_ids, attention_mask, labels=None):
            """
            前向传播
            
            Args:
                input_ids: 输入ID
                attention_mask: 注意力掩码
                labels: 标签（训练时使用）
                
            Returns:
                loss, logits
            """
            # BERT编码
            outputs = self.bert(
                input_ids=input_ids,
                attention_mask=attention_mask
            )
            
            # 取[CLS]向量
            pooled_output = outputs.pooler_output
            
            # 分类
            pooled_output = self.dropout(pooled_output)
            logits = self.classifier(pooled_output)
            
            # 计算损失
            loss = None
            if labels is not None:
                loss_fn = nn.CrossEntropyLoss()
                loss = loss_fn(logits, labels)
            
            return loss, logits
        
        def freeze_bert_layers(self, num_layers: int = 10):
            """冻结BERT底层"""
            # 冻结embeddings
            for param in self.bert.embeddings.parameters():
                param.requires_grad = False
            
            # 冻结前num_layers层
            for i, layer in enumerate(self.bert.encoder.layer):
                if i < num_layers:
                    for param in layer.parameters():
                        param.requires_grad = False
        
        def unfreeze_all(self):
            """解冻所有层"""
            for param in self.parameters():
                param.requires_grad = True
else:
    # 占位类，避免导入错误
    class BertSentimentClassifier:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyTorch未安装，无法使用BertSentimentClassifier")


# ==================== 早停类 ====================

class EarlyStopping:
    """早停机制"""
    
    def __init__(self, patience: int = 3, delta: float = 0.001, mode: str = 'min'):
        """
        Args:
            patience: 容忍次数
            delta: 最小改进量
            mode: 'min'或'max'
        """
        self.patience = patience
        self.delta = delta
        self.mode = mode
        self.counter = 0
        self.best_score = None
        self.early_stop = False
    
    def __call__(self, score):
        if self.best_score is None:
            self.best_score = score
            return False
        
        if self.mode == 'min':
            improved = score < self.best_score - self.delta
        else:
            improved = score > self.best_score + self.delta
        
        if improved:
            self.best_score = score
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        
        return self.early_stop


# ==================== 评估指标 ====================

class MetricsCalculator:
    """评估指标计算器"""
    
    @staticmethod
    def calculate_metrics(y_true: List[int], y_pred: List[int], 
                          y_prob: np.ndarray = None) -> Dict:
        """
        计算评估指标
        
        Args:
            y_true: 真实标签
            y_pred: 预测标签
            y_prob: 预测概率
            
        Returns:
            指标字典
        """
        from collections import Counter
        
        # 基础指标
        correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        accuracy = correct / len(y_true) if y_true else 0
        
        # 每个类别的指标
        labels = sorted(set(y_true) | set(y_pred))
        precision_per_class = {}
        recall_per_class = {}
        f1_per_class = {}
        
        for label in labels:
            tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
            fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
            fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            precision_per_class[label] = precision
            recall_per_class[label] = recall
            f1_per_class[label] = f1
        
        # 宏平均
        macro_precision = sum(precision_per_class.values()) / len(labels) if labels else 0
        macro_recall = sum(recall_per_class.values()) / len(labels) if labels else 0
        macro_f1 = sum(f1_per_class.values()) / len(labels) if labels else 0
        
        # 混淆矩阵
        confusion_matrix = {}
        for t in labels:
            confusion_matrix[t] = {}
            for p in labels:
                confusion_matrix[t][p] = sum(1 for true, pred in zip(y_true, y_pred) 
                                             if true == t and pred == p)
        
        return {
            'accuracy': accuracy,
            'macro_precision': macro_precision,
            'macro_recall': macro_recall,
            'macro_f1': macro_f1,
            'precision_per_class': precision_per_class,
            'recall_per_class': recall_per_class,
            'f1_per_class': f1_per_class,
            'confusion_matrix': confusion_matrix,
            'total_samples': len(y_true)
        }
    
    @staticmethod
    def print_metrics(metrics: Dict, label_names: Dict[int, str] = None):
        """打印评估指标"""
        print("\n" + "=" * 50)
        print("评估指标")
        print("=" * 50)
        print(f"准确率: {metrics['accuracy']:.4f}")
        print(f"宏平均精确率: {metrics['macro_precision']:.4f}")
        print(f"宏平均召回率: {metrics['macro_recall']:.4f}")
        print(f"宏平均F1: {metrics['macro_f1']:.4f}")
        
        print("\n各类别指标:")
        for label in sorted(metrics['precision_per_class'].keys()):
            name = label_names.get(label, str(label)) if label_names else str(label)
            print(f"  {name}:")
            print(f"    精确率: {metrics['precision_per_class'][label]:.4f}")
            print(f"    召回率: {metrics['recall_per_class'][label]:.4f}")
            print(f"    F1: {metrics['f1_per_class'][label]:.4f}")
        
        print("\n混淆矩阵:")
        labels = sorted(metrics['confusion_matrix'].keys())
        header = "真实\\预测"
        for label in labels:
            name = label_names.get(label, str(label)) if label_names else str(label)
            header += f"\t{name}"
        print(header)
        
        for t in labels:
            name = label_names.get(t, str(t)) if label_names else str(t)
            row = f"{name}"
            for p in labels:
                row += f"\t{metrics['confusion_matrix'][t][p]}"
            print(row)
        
        print("=" * 50)


# ==================== 主模型类 ====================

class ChineseBertSentimentModel:
    """
    ChineseBERT情感分析模型
    
    功能：
    - 模型训练（支持微调策略）
    - 模型评估
    - 情感预测
    - 模型保存/加载
    """
    
    def __init__(self, 
                 model_config: ModelConfig = None,
                 training_config: TrainingConfig = None):
        """
        初始化模型
        
        Args:
            model_config: 模型配置
            training_config: 训练配置
        """
        if not TORCH_AVAILABLE or not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("请安装PyTorch和Transformers: pip install torch transformers")
        
        self.model_config = model_config or ModelConfig()
        self.training_config = training_config or TrainingConfig()
        
        # 设备
        self.device = self._get_device()
        logger.info(f"使用设备: {self.device}")
        
        # 加载分词器
        cache_dir = os.environ.get("TRANSFORMERS_CACHE", "./model_cache")
        self.tokenizer = BertTokenizer.from_pretrained(self.model_config.model_name, cache_dir=cache_dir)
        
        # 模型（延迟初始化）
        self.model = None
        
        # 训练状态
        self.training_history = []
        self.best_metrics = None
    
    def _get_device(self):
        """获取计算设备"""
        if self.training_config.device == 'auto':
            return torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        return torch.device(self.training_config.device)
    
    def _init_model(self):
        """初始化模型"""
        if self.model is None:
            # 使用自定义分类器或transformers内置
            self.model = BertForSequenceClassification.from_pretrained(
                self.model_config.model_name,
                num_labels=self.model_config.num_labels,
                id2label=self.model_config.id2label,
                label2id=self.model_config.label2id
            )
            self.model.to(self.device)
    
    def _get_optimizer(self):
        """
        获取优化器（分层学习率）
        
        BERT层使用较小学习率，分类头使用较大学习率
        """
        # 分组参数
        no_decay = ['bias', 'LayerNorm.weight']
        
        optimizer_grouped_parameters = [
            # BERT参数（带权重衰减）
            {
                'params': [p for n, p in self.model.bert.named_parameters() 
                          if not any(nd in n for nd in no_decay)],
                'lr': self.training_config.bert_learning_rate,
                'weight_decay': self.training_config.weight_decay
            },
            # BERT参数（不带权重衰减）
            {
                'params': [p for n, p in self.model.bert.named_parameters() 
                          if any(nd in n for nd in no_decay)],
                'lr': self.training_config.bert_learning_rate,
                'weight_decay': 0.0
            },
            # 分类头参数
            {
                'params': [p for n, p in self.model.classifier.named_parameters()],
                'lr': self.training_config.classifier_learning_rate,
                'weight_decay': self.training_config.weight_decay
            }
        ]
        
        return torch.optim.AdamW(optimizer_grouped_parameters)
    
    def _get_scheduler(self, optimizer, num_training_steps: int):
        """获取学习率调度器"""
        num_warmup_steps = int(num_training_steps * self.training_config.warmup_ratio)
        
        if self.training_config.scheduler_type == 'linear':
            return get_linear_schedule_with_warmup(
                optimizer,
                num_warmup_steps=num_warmup_steps,
                num_training_steps=num_training_steps
            )
        elif self.training_config.scheduler_type == 'cosine':
            return get_cosine_schedule_with_warmup(
                optimizer,
                num_warmup_steps=num_warmup_steps,
                num_training_steps=num_training_steps
            )
        else:
            return None
    
    def train(self,
              train_texts: List[str],
              train_labels: List[int],
              val_texts: List[str] = None,
              val_labels: List[int] = None,
              augment_config: DataAugmentConfig = None) -> Dict:
        """
        训练模型
        
        Args:
            train_texts: 训练文本
            train_labels: 训练标签
            val_texts: 验证文本
            val_labels: 验证标签
            augment_config: 数据增强配置
            
        Returns:
            训练历史
        """
        logger.info("开始训练...")
        
        # 初始化模型
        self._init_model()
        
        # 创建数据集
        train_dataset = WeiboSentimentDataset(
            train_texts, train_labels, self.tokenizer,
            max_length=self.training_config.max_length,
            augment_config=augment_config
        )
        
        val_dataset = None
        if val_texts and val_labels:
            val_dataset = WeiboSentimentDataset(
                val_texts, val_labels, self.tokenizer,
                max_length=self.training_config.max_length
            )
        
        # 类别平衡采样
        sample_weights = train_dataset.get_sample_weights()
        sampler = WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True
        )
        
        # 数据加载器
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.training_config.batch_size,
            sampler=sampler,
            num_workers=0,  # Windows兼容
            pin_memory=True if self.device.type == 'cuda' else False
        )
        
        val_loader = None
        if val_dataset:
            val_loader = DataLoader(
                val_dataset,
                batch_size=self.training_config.batch_size,
                shuffle=False,
                num_workers=0
            )
        
        # 优化器和调度器
        optimizer = self._get_optimizer()
        num_training_steps = len(train_loader) * self.training_config.epochs // self.training_config.gradient_accumulation_steps
        scheduler = self._get_scheduler(optimizer, num_training_steps)
        
        # 混合精度
        scaler = GradScaler() if self.training_config.use_fp16 and self.device.type == 'cuda' else None
        
        # 早停
        early_stopping = EarlyStopping(
            patience=self.training_config.early_stopping_patience,
            delta=self.training_config.early_stopping_delta,
            mode='max'  # 监控F1
        )
        
        # 训练循环
        global_step = 0
        best_f1 = 0
        
        for epoch in range(self.training_config.epochs):
            logger.info(f"\nEpoch {epoch + 1}/{self.training_config.epochs}")
            
            # 训练阶段
            self.model.train()
            total_loss = 0
            optimizer.zero_grad()
            
            for step, batch in enumerate(train_loader):
                # 移动到设备
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                # 前向传播（混合精度）
                if scaler:
                    with autocast():
                        outputs = self.model(
                            input_ids=input_ids,
                            attention_mask=attention_mask,
                            labels=labels
                        )
                        loss = outputs.loss / self.training_config.gradient_accumulation_steps
                    
                    scaler.scale(loss).backward()
                else:
                    outputs = self.model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels
                    )
                    loss = outputs.loss / self.training_config.gradient_accumulation_steps
                    loss.backward()
                
                total_loss += loss.item()
                
                # 梯度累积
                if (step + 1) % self.training_config.gradient_accumulation_steps == 0:
                    # 梯度裁剪
                    if scaler:
                        scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(),
                        self.training_config.max_grad_norm
                    )
                    
                    # 更新参数
                    if scaler:
                        scaler.step(optimizer)
                        scaler.update()
                    else:
                        optimizer.step()
                    
                    if scheduler:
                        scheduler.step()
                    
                    optimizer.zero_grad()
                    global_step += 1
                    
                    # 日志
                    if global_step % self.training_config.logging_steps == 0:
                        avg_loss = total_loss / (step + 1)
                        lr = optimizer.param_groups[0]['lr']
                        logger.info(f"Step {global_step}, Loss: {avg_loss:.4f}, LR: {lr:.2e}")
            
            # 验证阶段
            if val_loader:
                val_metrics = self.evaluate(val_loader)
                logger.info(f"验证集 - Acc: {val_metrics['accuracy']:.4f}, F1: {val_metrics['macro_f1']:.4f}")
                
                # 保存最佳模型
                if val_metrics['macro_f1'] > best_f1:
                    best_f1 = val_metrics['macro_f1']
                    self.best_metrics = val_metrics
                    if self.training_config.save_best_only:
                        self.save_model(os.path.join(self.training_config.save_dir, 'best_model'))
                
                # 早停检查
                if early_stopping(val_metrics['macro_f1']):
                    logger.info(f"早停触发，最佳F1: {best_f1:.4f}")
                    break
                
                # 记录历史
                self.training_history.append({
                    'epoch': epoch + 1,
                    'train_loss': total_loss / len(train_loader),
                    'val_accuracy': val_metrics['accuracy'],
                    'val_f1': val_metrics['macro_f1']
                })
        
        logger.info(f"训练完成，最佳F1: {best_f1:.4f}")
        return {'history': self.training_history, 'best_metrics': self.best_metrics}
    
    def evaluate(self, data_loader: DataLoader = None,
                 texts: List[str] = None,
                 labels: List[int] = None) -> Dict:
        """
        评估模型
        
        Args:
            data_loader: 数据加载器
            texts: 文本列表
            labels: 标签列表
            
        Returns:
            评估指标
        """
        if data_loader is None and texts is not None and labels is not None:
            dataset = WeiboSentimentDataset(
                texts, labels, self.tokenizer,
                max_length=self.training_config.max_length
            )
            data_loader = DataLoader(dataset, batch_size=self.training_config.batch_size)
        
        self._init_model()
        self.model.eval()
        
        all_preds = []
        all_labels = []
        all_probs = []
        
        with torch.no_grad():
            for batch in data_loader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask
                )
                
                probs = F.softmax(outputs.logits, dim=-1)
                preds = torch.argmax(probs, dim=-1)
                
                all_preds.extend(preds.cpu().numpy().tolist())
                all_labels.extend(labels.cpu().numpy().tolist())
                all_probs.extend(probs.cpu().numpy().tolist())
        
        metrics = MetricsCalculator.calculate_metrics(all_labels, all_preds, np.array(all_probs))
        return metrics
    
    def predict(self, texts: Union[str, List[str]], 
                return_probs: bool = True) -> List[Dict]:
        """
        预测情感
        
        Args:
            texts: 文本或文本列表
            return_probs: 是否返回概率
            
        Returns:
            预测结果列表
        """
        if isinstance(texts, str):
            texts = [texts]
        
        self._init_model()
        self.model.eval()
        
        results = []
        
        with torch.no_grad():
            for text in texts:
                # 编码
                encoding = self.tokenizer.encode_plus(
                    text,
                    add_special_tokens=True,
                    max_length=self.training_config.max_length,
                    padding='max_length',
                    truncation=True,
                    return_attention_mask=True,
                    return_tensors='pt'
                )
                
                input_ids = encoding['input_ids'].to(self.device)
                attention_mask = encoding['attention_mask'].to(self.device)
                
                # 预测
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask
                )
                
                probs = F.softmax(outputs.logits, dim=-1)
                pred_id = torch.argmax(probs, dim=-1).item()
                pred_label = self.model_config.id2label[pred_id]
                
                # 计算情感得分 [-1, 1]
                prob_values = probs[0].cpu().numpy()
                score = prob_values[2] - prob_values[0]  # positive - negative
                
                result = {
                    'text': text,
                    'label': pred_label,
                    'label_id': pred_id,
                    'score': float(score),
                    'confidence': float(prob_values[pred_id])
                }
                
                if return_probs:
                    result['probabilities'] = {
                        'negative': float(prob_values[0]),
                        'neutral': float(prob_values[1]),
                        'positive': float(prob_values[2])
                    }
                
                results.append(result)
        
        return results
    
    def save_model(self, save_path: str):
        """保存模型"""
        os.makedirs(save_path, exist_ok=True)
        
        # 保存模型
        self.model.save_pretrained(save_path)
        self.tokenizer.save_pretrained(save_path)
        
        # 保存配置
        config = {
            'model_config': asdict(self.model_config),
            'training_config': asdict(self.training_config),
            'training_history': self.training_history,
            'best_metrics': self.best_metrics
        }
        
        with open(os.path.join(save_path, 'config.json'), 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        logger.info(f"模型已保存到: {save_path}")
    
    def load_model(self, load_path: str):
        """加载模型"""
        # 加载配置
        config_path = os.path.join(load_path, 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.training_history = config.get('training_history', [])
                self.best_metrics = config.get('best_metrics')
        
        # 加载模型
        self.model = BertForSequenceClassification.from_pretrained(load_path)
        self.tokenizer = BertTokenizer.from_pretrained(load_path)
        self.model.to(self.device)
        
        logger.info(f"模型已从 {load_path} 加载")
    
    def error_analysis(self, texts: List[str], labels: List[int]) -> Dict:
        """
        错误分析
        
        Args:
            texts: 文本列表
            labels: 真实标签
            
        Returns:
            错误分析结果
        """
        predictions = self.predict(texts)
        
        errors = {
            'false_positive': [],  # 预测正面但实际不是
            'false_negative': [],  # 预测负面但实际不是
            'confusion': []        # 其他混淆
        }
        
        for text, true_label, pred in zip(texts, labels, predictions):
            pred_label = pred['label_id']
            
            if true_label != pred_label:
                error_info = {
                    'text': text,
                    'true_label': self.model_config.id2label[true_label],
                    'pred_label': pred['label'],
                    'confidence': pred['confidence'],
                    'probabilities': pred.get('probabilities', {})
                }
                
                if pred_label == 2 and true_label != 2:
                    errors['false_positive'].append(error_info)
                elif pred_label == 0 and true_label != 0:
                    errors['false_negative'].append(error_info)
                else:
                    errors['confusion'].append(error_info)
        
        # 统计
        total_errors = len(errors['false_positive']) + len(errors['false_negative']) + len(errors['confusion'])
        
        return {
            'total_samples': len(texts),
            'total_errors': total_errors,
            'error_rate': total_errors / len(texts) if texts else 0,
            'false_positive_count': len(errors['false_positive']),
            'false_negative_count': len(errors['false_negative']),
            'confusion_count': len(errors['confusion']),
            'errors': errors
        }


# ==================== 便捷函数 ====================

def create_model(model_name: str = "hfl/chinese-bert-wwm-ext",
                 num_labels: int = 3) -> ChineseBertSentimentModel:
    """创建模型"""
    model_config = ModelConfig(model_name=model_name, num_labels=num_labels)
    return ChineseBertSentimentModel(model_config=model_config)


def quick_predict(texts: Union[str, List[str]], 
                  model_path: str = None) -> List[Dict]:
    """快速预测"""
    model = ChineseBertSentimentModel()
    if model_path:
        model.load_model(model_path)
    return model.predict(texts)


# ==================== 模块初始化文件 ====================

def create_init_file():
    """创建__init__.py"""
    init_content = '''"""
BERT情感分析模型模块
"""

from .chinese_bert_sentiment import (
    ChineseBertSentimentModel,
    WeiboSentimentDataset,
    ModelConfig,
    TrainingConfig,
    DataAugmentConfig,
    MetricsCalculator,
    create_model,
    quick_predict,
)

__all__ = [
    'ChineseBertSentimentModel',
    'WeiboSentimentDataset',
    'ModelConfig',
    'TrainingConfig',
    'DataAugmentConfig',
    'MetricsCalculator',
    'create_model',
    'quick_predict',
]
'''
    return init_content


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ChineseBERT情感分析')
    parser.add_argument('--mode', type=str, choices=['train', 'predict', 'evaluate'], default='predict')
    parser.add_argument('--model_path', type=str, default=None, help='模型路径')
    parser.add_argument('--text', type=str, default=None, help='待预测文本')
    parser.add_argument('--data_path', type=str, default=None, help='数据路径')
    
    args = parser.parse_args()
    
    if args.mode == 'predict':
        if args.text:
            model = ChineseBertSentimentModel()
            if args.model_path:
                model.load_model(args.model_path)
            
            results = model.predict(args.text)
            for result in results:
                print(f"\n文本: {result['text']}")
                print(f"情感: {result['label']}")
                print(f"得分: {result['score']:.4f}")
                print(f"置信度: {result['confidence']:.4f}")
                if 'probabilities' in result:
                    print(f"概率分布: {result['probabilities']}")
        else:
            # 测试用例
            test_texts = [
                "这部电影真的太好看了！强烈推荐！",
                "服务态度太差了，非常失望",
                "还可以吧，一般般",
                "虽然有点贵，但是质量真的很好",
            ]
            
            print("=" * 60)
            print("ChineseBERT情感分析测试")
            print("=" * 60)
            print("\n注意：首次运行需要下载预训练模型，请确保网络连接正常")
            print("如果下载失败，可以手动下载模型到本地后指定路径")
            
            try:
                model = ChineseBertSentimentModel()
                results = model.predict(test_texts)
                
                for result in results:
                    print(f"\n文本: {result['text']}")
                    print(f"情感: {result['label']} (置信度: {result['confidence']:.4f})")
                    print(f"得分: {result['score']:.4f}")
            except Exception as e:
                print(f"\n运行出错: {e}")
                print("请确保已安装: pip install torch transformers")
    
    elif args.mode == 'train':
        print("训练模式需要提供训练数据")
        print("示例代码:")
        print("""
from backend.models.chinese_bert_sentiment import (
    ChineseBertSentimentModel, 
    TrainingConfig,
    DataAugmentConfig
)

# 准备数据
train_texts = ["好评", "差评", "一般"]
train_labels = [2, 0, 1]  # 2=positive, 0=negative, 1=neutral

# 创建模型
model = ChineseBertSentimentModel()

# 训练
model.train(
    train_texts, train_labels,
    val_texts=train_texts, val_labels=train_labels,
    augment_config=DataAugmentConfig(enable_augmentation=True)
)

# 保存
model.save_model('./my_model')
        """)
