# 模型文件目录

## 说明

本项目使用的主模型已上传到 HuggingFace:

**🤗 [`senlou/weibo-sentiment-chinese-bert`](https://huggingface.co/senlou/weibo-sentiment-chinese-bert)**

这是基于 [`hfl/chinese-bert-wwm-ext`](https://huggingface.co/hfl/chinese-bert-wwm-ext) 在微博情感数据集上**已微调好的三分类模型** (negative / positive / neutral), 开箱即用, 测试集 Macro F1 = 0.8783, Accuracy = 87.79%.

模型权重文件过大 (单文件 ~410MB)，**未上传到 GitHub**。请按下述方式下载。

## 目录结构

```
models/
├── chinese-bert-wwm-ext/          # 主模型 (论文使用版本)
│   ├── config.json
│   ├── model.safetensors          # 409 MB - 需下载
│   ├── pytorch_model.bin          # 411 MB - 需下载 (与 safetensors 二选一即可)
│   ├── vocab.txt
│   ├── tokenizer.json
│   ├── tokenizer_config.json
│   └── special_tokens_map.json
├── chinese-bert-wwm-ext-baseline/ # 基线版本 (用于对比实验, 可选)
├── chinese-bert-wwm-ext-v2/       # 微调 v2 (可选)
├── chinese-bert-wwm-ext-v3/       # 微调 v3 (可选)
├── chinese_bert_sentiment.py      # 模型封装类 (已上传)
├── model_evaluation.py            # 评估代码 (已上传)
├── model_manager.py               # 模型管理 (已上传)
└── __init__.py
```

## 下载方式 (三选一)

### 方式 1: HuggingFace CLI 下载已微调模型 ⭐ 推荐

```bash
pip install huggingface_hub

# 下载已微调好的三分类模型 (~410 MB)
huggingface-cli download senlou/weibo-sentiment-chinese-bert \
    --local-dir ./models/chinese-bert-wwm-ext \
    --local-dir-use-symlinks False
```

### 方式 2: Python 代码自动下载并加载

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# 直接加载已微调的三分类模型 (id2label 已预置)
tokenizer = AutoTokenizer.from_pretrained('senlou/weibo-sentiment-chinese-bert')
model = AutoModelForSequenceClassification.from_pretrained(
    'senlou/weibo-sentiment-chinese-bert'
)

# 保存到本地 (供 Spark / Docker 离线使用)
tokenizer.save_pretrained('./models/chinese-bert-wwm-ext')
model.save_pretrained('./models/chinese-bert-wwm-ext')
```

### 方式 3: 国内镜像 (HuggingFace 访问受限时使用)

```bash
# Linux / Mac
export HF_ENDPOINT=https://hf-mirror.com
# Windows PowerShell
$env:HF_ENDPOINT = "https://hf-mirror.com"

huggingface-cli download senlou/weibo-sentiment-chinese-bert \
    --local-dir ./models/chinese-bert-wwm-ext
```

## 直接推理示例

```python
from transformers import pipeline

classifier = pipeline(
    "text-classification",
    model="senlou/weibo-sentiment-chinese-bert",
)
print(classifier("今天天气真好，心情也很棒！"))
# [{'label': 'positive', 'score': 0.98...}]
```

---

## 从头微调 (高级用法, 可选)

如果你想从 **原始未微调的** ChineseBERT 基础模型开始，自行训练微博情感三分类模型:

```bash
# 下载原始基础模型 (未微调)
huggingface-cli download hfl/chinese-bert-wwm-ext \
    --local-dir ./models/chinese-bert-wwm-ext-base

# ModelScope 镜像 (国内推荐)
pip install modelscope
python -c "from modelscope import snapshot_download; snapshot_download('dienstag/chinese-bert-wwm-ext', cache_dir='./model_cache_ms')"
```

然后运行微调脚本 (需先准备训练数据, 详见 `../data/README.md`):

```bash
python scripts/finetune_classifier.py        # v1 微调 (基础)
python scripts/finetune_classifier_v2.py     # v2 微调 (分层学习率)
python scripts/finetune_classifier_v3.py     # v3 微调 (数据增强 + 类别平衡)
```

## 模型性能对比 (测试集 10000 条)

| 模型 | Accuracy | Macro F1 | 说明 |
|------|----------|----------|------|
| 纯词典 | 67.12% | 0.6543 | 基线 |
| hfl/chinese-bert-wwm-ext (未微调) | 52.34% | 0.4521 | 仅做参考 |
| **senlou/weibo-sentiment-chinese-bert** | **87.79%** | **0.8783** | **本项目默认使用** |
| 级联模式 (词典 + BERT) | 85.85% | 0.8594 | 17% 样本词典直出, 平均耗时 6.54 ms/条 |
