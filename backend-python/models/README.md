# 模型文件目录

## 说明

本项目使用 ChineseBERT (`hfl/chinese-bert-wwm-ext`) 作为情感分析基础模型。
**模型权重文件过大** (单文件 ~410MB)，**未上传到 GitHub**。

请按下述方式自行下载。

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

## 下载方式

### 方式 1: 使用 transformers 库自动下载 (推荐)

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification

tokenizer = AutoTokenizer.from_pretrained('hfl/chinese-bert-wwm-ext')
model = AutoModelForSequenceClassification.from_pretrained(
    'hfl/chinese-bert-wwm-ext',
    num_labels=3,
    id2label={0: 'negative', 1: 'positive', 2: 'neutral'},
    label2id={'negative': 0, 'positive': 1, 'neutral': 2},
)

# 保存到本地
tokenizer.save_pretrained('./models/chinese-bert-wwm-ext')
model.save_pretrained('./models/chinese-bert-wwm-ext')
```

### 方式 2: HuggingFace CLI 下载

```bash
pip install huggingface_hub
huggingface-cli download hfl/chinese-bert-wwm-ext \
    --local-dir ./models/chinese-bert-wwm-ext \
    --local-dir-use-symlinks False
```

### 方式 3: ModelScope 镜像下载 (国内推荐)

```bash
pip install modelscope
python -c "from modelscope import snapshot_download; snapshot_download('dienstag/chinese-bert-wwm-ext', cache_dir='./model_cache_ms')"
```

下载完成后会得到 `model_cache_ms/dienstag/chinese-bert-wwm-ext/`，将内容复制到 `models/chinese-bert-wwm-ext/` 即可。

## 微调

如需复现论文实验中的三分类微调，运行：

```bash
python scripts/finetune_classifier.py        # v1 微调
python scripts/finetune_classifier_v2.py     # v2 微调
python scripts/finetune_classifier_v3.py     # v3 微调
```

需先下载训练数据 `weibo_senti_100k.csv`，详见 `../data/README.md`。
