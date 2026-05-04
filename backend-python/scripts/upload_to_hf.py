# -*- coding: utf-8 -*-
"""
上传 ChineseBERT 三分类微调模型到 HuggingFace Hub.

使用:
    python scripts/upload_to_hf.py
    # 程序会在终端交互式提示你粘贴 token (输入时不回显)

安全提示:
    - Token 在终端交互式输入, 不写入 shell 历史 / 环境变量 / 文件
    - 也可通过 HF_TOKEN 环境变量传入 (CI/CD 场景)
    - 上传完成后请在 https://huggingface.co/settings/tokens 重置 token
"""

import os
import sys
from getpass import getpass
from pathlib import Path

from huggingface_hub import HfApi, create_repo

# ========== 配置 ==========
REPO_ID = "senlou/weibo-sentiment-chinese-bert"
REPO_TYPE = "model"
MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "chinese-bert-wwm-ext"

# pytorch_model.bin 与 model.safetensors 内容等价, 仅上传 safetensors 可节省 ~50% 时间
IGNORE_PATTERNS = [
    "pytorch_model.bin",   # 冗余 (已有 safetensors)
    "*.msgpack",           # Flax 权重 (若有)
    "*.h5",                # TF 权重 (若有)
    "__pycache__",
    ".git",
    ".DS_Store",
]

# ========== 模型卡 (README.md) ==========
MODEL_CARD = """---
language: zh
license: apache-2.0
library_name: transformers
pipeline_tag: text-classification
tags:
  - bert
  - chinese
  - sentiment-analysis
  - weibo
  - text-classification
datasets:
  - weibo_senti_100k
base_model: hfl/chinese-bert-wwm-ext
widget:
  - text: "今天天气真好，心情也很棒！"
    example_title: "正面样例"
  - text: "这个产品质量太差了，非常失望。"
    example_title: "负面样例"
  - text: "今天上午开会讨论了新项目的进度安排。"
    example_title: "中性样例"
---

# Weibo Sentiment ChineseBERT (三分类)

基于 [`hfl/chinese-bert-wwm-ext`](https://huggingface.co/hfl/chinese-bert-wwm-ext)
在微博情感数据集上微调的**三分类**情感分析模型 (negative / positive / neutral).

本模型为本科毕业设计《基于 Spark 的微博舆情分析系统》的配套模型.
完整项目代码: [MOST951/Graduation-Design](https://github.com/MOST951/Graduation-Design)

## 标签映射

| id | label    | 中文  |
|----|----------|------|
| 0  | negative | 负面  |
| 1  | positive | 正面  |
| 2  | neutral  | 中性  |

## 使用方式

### 方式 1: pipeline (最简单)

```python
from transformers import pipeline

classifier = pipeline(
    "text-classification",
    model="MOST951/weibo-sentiment-chinese-bert",
)
result = classifier("今天天气真好，心情也很棒！")
print(result)
# [{'label': 'positive', 'score': 0.98...}]
```

### 方式 2: AutoModel (可批量 + 可控)

```python
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

tokenizer = AutoTokenizer.from_pretrained("MOST951/weibo-sentiment-chinese-bert")
model = AutoModelForSequenceClassification.from_pretrained("MOST951/weibo-sentiment-chinese-bert")
model.eval()

texts = [
    "今天天气真好，心情也很棒！",
    "这个产品质量太差了，非常失望。",
    "今天上午开会讨论了新项目的进度安排。",
]

with torch.no_grad():
    enc = tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors="pt")
    logits = model(**enc).logits
    probs = torch.softmax(logits, dim=-1)
    preds = probs.argmax(dim=-1).tolist()

id2label = model.config.id2label
for text, pred, prob in zip(texts, preds, probs):
    print(f"{id2label[pred]:<10} ({prob[pred]:.4f})  {text}")
```

## 训练数据

- 数据集: [weibo_senti_100k](https://github.com/SophonPlus/ChineseNlpCorpus/tree/master/datasets/weibo_senti_100k)
- 规模: 10 万条微博, 按 8:1:1 划分训练/验证/测试
- 原始为二分类 (正 / 负), 通过规则补全中性样本构造三分类

## 评估结果 (测试集 10,000 条)

### 标准模式 (纯 BERT)

| 指标 | negative | positive | neutral | Macro |
|------|----------|----------|---------|-------|
| Precision | 0.8945 | 0.9233 | 0.8213 | 0.8797 |
| Recall    | 0.9103 | 0.8632 | 0.8602 | 0.8779 |
| F1        | 0.9023 | 0.8922 | 0.8403 | 0.8783 |

**总体准确率: 87.79%**

### 推理速度 (RTX 3050 Ti, batch_size=32)

| batch_size | 平均耗时 | 加速比 |
|-----------|---------|--------|
| 1         | 23.54 ms/条 | 1.00× |
| 32        | 7.38 ms/条  | **3.19×** |
| 64        | 7.75 ms/条  | 3.04× |

### 级联模式 (词典 + BERT 两阶段批量化)

- 平均耗时: **6.54 ms/条** (17% 样本被词典直出, 无需 BERT)
- Accuracy: 85.85%, Macro F1: 0.8594

## 训练超参

| 参数 | 值 |
|------|---|
| 基础模型 | hfl/chinese-bert-wwm-ext |
| max_length | 128 |
| batch_size | 32 |
| learning_rate | 2e-5 |
| epochs | 3 |
| optimizer | AdamW |
| warmup_ratio | 0.1 |
| 硬件 | NVIDIA RTX 3050 Ti (CUDA 11.8) |

## 许可证

Apache 2.0

## 引用

如果你在研究中使用了本模型, 请引用:

```bibtex
@misc{weibo-sentiment-chinese-bert-2026,
  title={基于 Spark 的微博舆情分析系统},
  author={senlou},
  year={2026},
  howpublished={\\url{https://github.com/MOST951/Graduation-Design}}
}
```
"""


def prompt_token() -> str:
    """
    读取 HuggingFace Token.
    优先顺序:
      1. 环境变量 HF_TOKEN / HUGGING_FACE_HUB_TOKEN (便于 CI/CD)
      2. 终端交互式输入 (不回显, 不写入 shell 历史)
    """
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token:
        print("[token] 从环境变量读取 HF_TOKEN")
        return token.strip()

    print()
    print("请粘贴 HuggingFace Token (输入时不回显, 回车确认)")
    print("获取地址: https://huggingface.co/settings/tokens")
    print("需要具备 Write 权限 (勾选 'Write access' 或选择 Classic Token type=Write)")
    print()
    try:
        token = getpass("HF Token: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消.", file=sys.stderr)
        sys.exit(1)

    if not token:
        print("ERROR: Token 为空, 已退出.", file=sys.stderr)
        sys.exit(1)
    if not token.startswith("hf_"):
        print("WARNING: Token 不以 'hf_' 开头, 可能无效. 仍继续尝试 ...",
              file=sys.stderr)
    return token


def main():
    # 1. 读取 token
    token = prompt_token()

    if not MODEL_DIR.exists():
        print(f"ERROR: 模型目录不存在: {MODEL_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Model dir: {MODEL_DIR}")
    print(f"Target repo: {REPO_ID}")
    print()

    # 2. 写入 README.md (模型卡) 到模型目录
    readme_path = MODEL_DIR / "README.md"
    readme_path.write_text(MODEL_CARD, encoding="utf-8")
    print(f"[1/3] 已写入模型卡: {readme_path}")

    # 3. 创建仓库 (若 token 无 create 权限, 假定用户已在网页上手动创建并继续)
    api = HfApi(token=token)
    print(f"[2/3] 创建/确认 HuggingFace 仓库 ...")
    try:
        create_repo(
            repo_id=REPO_ID,
            repo_type=REPO_TYPE,
            exist_ok=True,
            token=token,
        )
        print(f"      仓库就绪: https://huggingface.co/{REPO_ID}")
    except Exception as e:
        msg = str(e)
        if "403" in msg or "Forbidden" in msg or "don't have the rights" in msg:
            print(f"      [WARN] Token 无创建仓库权限, 假定仓库已在网页上手动创建.")
            print(f"      继续尝试直接上传到: https://huggingface.co/{REPO_ID}")
            # 验证仓库存在
            try:
                api.repo_info(repo_id=REPO_ID, repo_type=REPO_TYPE, token=token)
                print(f"      仓库已存在, 继续 ...")
            except Exception as probe_err:
                print(f"ERROR: 仓库 {REPO_ID} 不存在. 请先访问", file=sys.stderr)
                print(f"  https://huggingface.co/new", file=sys.stderr)
                print(f"  手动创建一个名为 'weibo-sentiment-chinese-bert' 的 public 模型仓库后重试.",
                      file=sys.stderr)
                print(f"  (原始错误: {probe_err})", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"ERROR: 创建仓库失败: {e}", file=sys.stderr)
            sys.exit(1)

    # 4. 上传文件夹
    print(f"[3/3] 开始上传 (忽略 pytorch_model.bin 以节省带宽) ...")
    print(f"      预计上传: ~409 MB (model.safetensors + tokenizer)")
    print(f"      慢速网络下大约 10-30 分钟, 请耐心等待 ...")
    try:
        api.upload_folder(
            folder_path=str(MODEL_DIR),
            repo_id=REPO_ID,
            repo_type=REPO_TYPE,
            ignore_patterns=IGNORE_PATTERNS,
            commit_message="Upload fine-tuned ChineseBERT 3-class sentiment model",
            token=token,
        )
    except Exception as e:
        print(f"ERROR: 上传失败: {e}", file=sys.stderr)
        sys.exit(1)

    print()
    print("=" * 60)
    print("上传完成! 访问:")
    print(f"   https://huggingface.co/{REPO_ID}")
    print("=" * 60)
    print()
    print("安全提示:")
    print("   请立即重置你的 HF Token:")
    print("   https://huggingface.co/settings/tokens")


if __name__ == "__main__":
    main()
