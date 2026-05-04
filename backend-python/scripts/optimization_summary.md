# BERT 微调优化实验总结

## 实验目标
优化 ChineseBERT 三分类情感分析模型，目标 Accuracy > 85%

## 实验结果

| 模型 | 损失函数 | max_len | lr | epochs | Test Acc | Macro F1 |
|------|---------|---------|-----|--------|----------|----------|
| **Baseline** | CE | 128 | 2e-5 | 3 | **88.44%** | **88.48%** |
| v2 (超参优化) | CE | 192 | 3e-5 | 4 | 87.94% | 88.04% |
| v3 (Focal Loss) | FL(γ=2) | 192 | 3e-5 | 3 | 87.54% | 87.58% |

## 各类别 F1

| 类别 | Baseline | v2 | v3 |
|------|----------|-----|-----|
| negative | 90.83% | 90.31% | 90.08% |
| positive | 89.84% | 89.51% | 89.29% |
| neutral | 84.76% | 84.30% | 83.36% |

## 结论

1. **Baseline 表现最优** (88.44%)，已远超 85% 目标
2. v2 超参优化（增加 max_length、调整 lr）反而轻微过拟合，accuracy 下降 0.5%
3. v3 Focal Loss 在三类均衡数据上无优势，accuracy 再降 0.4%
4. **最终决策：采用 Baseline 模型部署**

## 部署变更
- 生产模型目录: `models/chinese-bert-wwm-ext` (与 baseline 相同权重)
- 修复 `model_singleton.py`: num_labels 2→3
- 修复 `unified_sentiment_service.py`: num_labels 2→3, label mapping 修正
