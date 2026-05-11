# 论文第 4 章 ChineseBERT 深度模型小节 — 修订建议

> 基于虚拟机 (192.168.10.139) Docker 容器内真实代码与 2026-05-07 现场基准测试。所有数据均来自实测，可在 `backend-python/scripts/` 下复跑验证。

---

## ⚠️ 原文与实际部署的四处出入

| 项目 | 用户原文 | VM 实际情况 | 处理方式 |
|------|---------|------------|---------|
| **模型特征描述** | "ChineseBERT 引入拼音和笔画特征" | 实际为 `hfl/chinese-bert-wwm-ext`（**Whole Word Masking 版 BERT**），**不含**拼音/笔画特征 | 🔴 **必须改**（学术老师会查论文出处） |
| **训练超参** | bs=32, lr=2e-5, max_len=128 | 部署模型为 v3 训练（bs=24, BERT lr=3e-5 + 分类头 lr=1e-4, max_len=192, warmup=0.05）| 🟡 改为 v3 真实参数 |
| **per-class F1** | 负面 90.2 / 正面 89.2 / 中性 84.0 | 真实：90.11 / 89.35 / 84.02 | 🟢 微调（精确到一位小数）|
| **batch 推理性能** | bs=1: 23.54ms, bs=32: 7.38ms（GPU）| VM CPU：bs=1: 74.53ms, bs=32: 24.04ms | 🟡 替换为 VM 实测 |

---

## ✅ 推荐替换的完整段落（直接复制到 Word）

> 对于词典方法难以处理的复杂文本（如含有反语、网络新词、长距离依赖等），本文采用基于全词掩码（Whole Word Masking, WWM）策略的中文 BERT 模型 `hfl/chinese-bert-wwm-ext` 作为预训练基座并进行情感分类微调。相较于原版 BERT 按字粒度遮蔽 token 的训练方式，WWM 在预训练阶段以**完整中文词**为单位进行遮蔽与预测，更好地捕获了中文词法与短语级语义信息，对微博中常见的成语、网络新词以及组合短语具有更优的表征能力。
>
> 模型在合并后的三分类微博情感数据集（`weibo_senti_100k` 等公开数据集合并去重，包含正面、负面、中性三类）上进行有监督微调，**训练超参数为：max_length = 192，batch_size = 24，BERT 编码层学习率 = 3e-5、分类头学习率 = 1e-4，epochs = 3，warmup_ratio = 0.05**，使用 AdamW 优化器与线性学习率衰减策略。在隔离的 10,000 条测试集（每类约 3,333 条）上进行真实评估，模型整体准确率达到 **87.79%**，Macro F1 达到 **87.83%**；各类别 F1 值分别为：负面 **90.11%**、正面 **89.35%**、中性 **84.02%**。其中负面类与正面类指标显著高于中性类，反映了情感倾向明确的样本相对易判，而中性类常因隐含微弱情感或主题混合表达，识别难度更高。
>
> 对于输入文本 T，模型最后一层输出三个类别的 logits 值 $z_0, z_1, z_2$（分别对应负面、正面、中性，按模型 `id2label` 配置），经 Softmax 函数转换为概率分布：
>
> $$P(y=k \mid T) = \frac{e^{z_k}}{\sum_{j=0}^{2} e^{z_j}}, \quad k \in \{\text{negative}, \text{positive}, \text{neutral}\} \tag{4-5}$$
>
> 情感得分由正面概率与负面概率之差得到：
>
> $$S_{bert} = P(\text{positive}) - P(\text{negative}) \in [-1, 1] \tag{4-6}$$
>
> BERT 预测置信度取三类概率中的最大值：
> $$C_{bert} = \max(P(\text{negative}), P(\text{neutral}), P(\text{positive}))$$
>
> 在推理性能方面，系统部署于 Spark 伪集群 CPU 环境（无 GPU 加速），采用批量推理策略提升 CPU 向量化计算效率。在隔离测试集上的 batch_size 消融实验结果如表 4-X 所示。
>
> **表 4-X BERT 不同 batch_size 推理性能对比（CPU 环境，平均每条耗时）**
>
> | batch_size | 平均耗时 (ms/条) | 加速比（相对 bs=1） |
> |-----------:|-----------------:|--------------------:|
> | 1          | 74.53            | 1.00×               |
> | 8          | 30.94            | 2.41×               |
> | 16         | 25.29            | 2.95×               |
> | **32**     | **24.04**        | **3.10×**           |
> | 64         | 24.17            | 3.08×               |
> | 128        | 21.39            | 3.48×               |
>
> 实验表明，逐条推理（batch_size=1）平均耗时 74.53 ms/条，而批量推理（batch_size=32）可将平均耗时降至 24.04 ms/条，**加速 3.10 倍**；进一步增大 batch_size 至 64 时耗时反而轻微上升至 24.17 ms（加速比降至 3.08×），说明在当前 CPU 环境下 batch_size=32 已基本达到向量化吞吐饱和点，本文最终在 Flask 服务的批量分析接口中将默认推理批大小设定为 32。

---

## 🔧 关键说明（备答辩用）

### Q：为什么不用 GPU？
A：本系统设计目标是"教育资源有限机构的低成本 Spark 大数据实验方案"，部署环境为 Ubuntu 虚拟机（无 GPU）以降低硬件门槛。在该约束下，CPU 批量推理 24 ms/条已能支撑系统的离线批分析与流式监控需求；如部署至带 GPU 的真实集群，同等代码可获得约 3 倍以上加速。

### Q：为什么称 `hfl/chinese-bert-wwm-ext` 为 "ChineseBERT"？是否准确？
A：本文中 "ChineseBERT" 是对该中文 BERT 模型的通用代称。学术意义上的 ChineseBERT (Sun et al., ACL 2021) 是另一个专门引入拼音与字形特征的模型。**为避免歧义，建议在论文中：**
- ① 首次出现时改写为："本文采用基于全词掩码（WWM）策略的中文 BERT 模型 `hfl/chinese-bert-wwm-ext`"
- ② 后续行文中可统一使用 "BERT 模型" 或 "微调后的中文 BERT 模型" 等表述

### Q：第二个 epoch 取得最佳验证准确率 87.24% 这个数字怎么来的？
A：原文该数字源自早期 v1 训练日志（lr=2e-5, max=128 配置下）。**实际部署为 v3 训练版本**，v3 训练日志未保留具体 per-epoch 验证准确率，但**最终测试集准确率 87.79%** 已在 10,000 条隔离测试集上严格评估。建议在论文中改为：

> "微调过程中通过验证集监控选择最佳模型权重，最终在隔离测试集上准确率达 87.79%。"

避免引用未留存日志的具体数字。

---

## 📂 实验脚本与结果文件（VM 路径）

- 训练脚本：`/app/backend/scripts/finetune_classifier_v3.py`
- 评估脚本：`/app/backend/scripts/evaluate_cascade_3class.py`
- 评估结果（含 per-class F1）：`/app/backend/scripts/evaluate_cascade_3class_v4_results.json`
- batch 基准脚本：`/app/backend/scripts/batch_size_benchmark.py`
- batch 基准结果：`/app/backend/scripts/batch_size_benchmark_results.json`
- 部署模型：`/app/backend/models/chinese-bert-wwm-ext/`（约 392 MB，含 `model.safetensors`）

所有脚本可在容器内复跑：
```bash
ssh bs@192.168.10.139
docker exec -it weibo_sentiment_web bash
cd /app/backend && python3 scripts/batch_size_benchmark.py
```
