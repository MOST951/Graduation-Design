#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载 hfl/chinese-bert-wwm-ext 到本地目录
=========================================

下载策略（按优先级）：
  1. ModelScope 阿里云模型仓库（国内直连快）
  2. HF-Mirror 镜像站
  3. HuggingFace 官方

用法:
    cd backend-python
    python scripts/download_model.py

下载目标: ./models/chinese-bert-wwm-ext/
"""

import os
import sys
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
MODEL_DIR = BACKEND_DIR / "models" / "chinese-bert-wwm-ext"

HF_MODEL_NAME = "hfl/chinese-bert-wwm-ext"
MS_MODEL_NAME = "dienstag/chinese-bert-wwm-ext"  # modelscope mirror


def download_via_modelscope() -> bool:
    """方法1: 通过 ModelScope 下载"""
    print("=" * 50)
    print("[策略1] 通过 ModelScope 下载 ...")
    print("=" * 50)

    try:
        from modelscope import snapshot_download
    except ImportError:
        print("  ✗ modelscope 未安装，跳过")
        return False

    # modelscope 上 hfl/chinese-bert-wwm-ext 的镜像 ID
    ms_candidates = [
        "dienstag/chinese-bert-wwm-ext",
        "AI-ModelScope/chinese-bert-wwm-ext",
        "damo/nlp_bert_backbone_chinese-bert-wwm-ext",
    ]

    for ms_id in ms_candidates:
        try:
            print(f"  尝试: {ms_id} ...")
            local_dir = snapshot_download(ms_id, cache_dir=str(BACKEND_DIR / "model_cache_ms"))
            print(f"  ✓ 下载成功: {local_dir}")
            _convert_to_target(Path(local_dir))
            return True
        except Exception as e:
            print(f"  ✗ {ms_id} 失败: {e}")
            continue

    return False


def download_via_hf_mirror() -> bool:
    """方法2: 通过 hf-mirror.com 下载"""
    print("=" * 50)
    print("[策略2] 通过 hf-mirror.com 下载 ...")
    print("=" * 50)

    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoConfig
    except ImportError:
        print("  ✗ transformers 未安装")
        return False

    try:
        print("  [1/3] 下载 config ...")
        config = AutoConfig.from_pretrained(HF_MODEL_NAME)
        config.save_pretrained(str(MODEL_DIR))
        print("         ✓ config.json")

        print("  [2/3] 下载 tokenizer ...")
        tokenizer = AutoTokenizer.from_pretrained(HF_MODEL_NAME)
        tokenizer.save_pretrained(str(MODEL_DIR))
        print("         ✓ tokenizer")

        print("  [3/3] 下载模型权重 (~400MB) ...")
        model = AutoModelForSequenceClassification.from_pretrained(
            HF_MODEL_NAME, num_labels=2
        )
        model.save_pretrained(str(MODEL_DIR))
        print("         ✓ model weights")
        return True
    except Exception as e:
        print(f"  ✗ hf-mirror 失败: {e}")
        return False
    finally:
        os.environ.pop("HF_ENDPOINT", None)


def download_via_hf_official() -> bool:
    """方法3: 通过 HuggingFace 官方下载"""
    print("=" * 50)
    print("[策略3] 通过 HuggingFace 官方下载 ...")
    print("=" * 50)

    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoConfig
    except ImportError:
        print("  ✗ transformers 未安装")
        return False

    try:
        config = AutoConfig.from_pretrained(HF_MODEL_NAME)
        config.save_pretrained(str(MODEL_DIR))
        tokenizer = AutoTokenizer.from_pretrained(HF_MODEL_NAME)
        tokenizer.save_pretrained(str(MODEL_DIR))
        model = AutoModelForSequenceClassification.from_pretrained(
            HF_MODEL_NAME, num_labels=2
        )
        model.save_pretrained(str(MODEL_DIR))
        return True
    except Exception as e:
        print(f"  ✗ HuggingFace 官方失败: {e}")
        return False


def _convert_to_target(src_dir: Path):
    """将 modelscope 下载目录中的文件复制到标准 MODEL_DIR"""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # modelscope 下载的目录结构可能有 config.json, pytorch_model.bin, vocab.txt 等
    needed_patterns = [
        "config.json", "vocab.txt", "tokenizer.json", "tokenizer_config.json",
        "special_tokens_map.json", "*.bin", "*.safetensors",
        "added_tokens.json",
    ]
    import glob

    copied = 0
    for pat in needed_patterns:
        for f in src_dir.glob(pat):
            dst = MODEL_DIR / f.name
            if not dst.exists() or f.stat().st_size != dst.stat().st_size:
                shutil.copy2(str(f), str(dst))
                copied += 1
                print(f"    复制: {f.name} ({f.stat().st_size / 1024 / 1024:.1f} MB)")

    # 如果 modelscope 没有 tokenizer_config.json，用 transformers 手动生成
    if not (MODEL_DIR / "tokenizer_config.json").exists():
        try:
            from transformers import BertTokenizer
            tok = BertTokenizer(str(MODEL_DIR / "vocab.txt"))
            tok.save_pretrained(str(MODEL_DIR))
            print("    生成: tokenizer 配置文件")
        except Exception:
            pass

    # 需要给模型加上 num_labels=2 的分类头配置
    _ensure_classification_config()

    print(f"  共复制 {copied} 个文件到 {MODEL_DIR}")


def _ensure_classification_config():
    """确保 config.json 中包含 num_labels=2（情感二分类）"""
    import json
    config_path = MODEL_DIR / "config.json"
    if not config_path.exists():
        return

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    changed = False
    if cfg.get("num_labels") != 2:
        cfg["num_labels"] = 2
        changed = True
    if "id2label" not in cfg or len(cfg["id2label"]) != 2:
        cfg["id2label"] = {"0": "negative", "1": "positive"}
        cfg["label2id"] = {"negative": 0, "positive": 1}
        changed = True

    if changed:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print("    更新: config.json (num_labels=2, label mapping)")


def verify_model():
    """验证模型可从本地加载"""
    print()
    print("=" * 50)
    print("验证本地加载 ...")
    print("=" * 50)

    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    mod = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR))
    inputs = tok("这是一条测试文本", return_tensors="pt", truncation=True, max_length=128)
    outputs = mod(**inputs)
    print(f"  Tokenizer vocab size: {tok.vocab_size}")
    print(f"  Model num_labels:     {mod.config.num_labels}")
    print(f"  Output logits shape:  {outputs.logits.shape}")
    print(f"  Model type:           {mod.config.model_type}")

    # 列出文件
    print(f"\n文件列表 ({MODEL_DIR}):")
    total_size = 0
    for f in sorted(MODEL_DIR.iterdir()):
        if f.is_file():
            size = f.stat().st_size
            total_size += size
            print(f"  {f.name:<40} {size / 1024 / 1024:>8.1f} MB")
    print(f"  {'合计':<40} {total_size / 1024 / 1024:>8.1f} MB")


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print(f"目标模型:  {HF_MODEL_NAME}")
    print(f"保存目录:  {MODEL_DIR}")
    print()

    # 如果目标目录已经有 config.json + 权重文件，跳过下载
    has_config = (MODEL_DIR / "config.json").exists()
    has_weights = any(MODEL_DIR.glob("*.bin")) or any(MODEL_DIR.glob("*.safetensors"))
    if has_config and has_weights:
        print("模型文件已存在，跳过下载。")
        verify_model()
        print(f"\n✅ 模型就绪! 路径: {MODEL_DIR}")
        return

    # 尝试多种下载方式
    success = download_via_modelscope()
    if not success:
        success = download_via_hf_mirror()
    if not success:
        success = download_via_hf_official()

    if not success:
        print("\n❌ 所有下载方式均失败!")
        print("   请手动下载模型文件到:", MODEL_DIR)
        print("   所需文件: config.json, vocab.txt, pytorch_model.bin / model.safetensors")
        print("   可从以下地址下载:")
        print("     https://modelscope.cn/models/dienstag/chinese-bert-wwm-ext")
        print("     https://hf-mirror.com/hfl/chinese-bert-wwm-ext")
        sys.exit(1)

    verify_model()
    print(f"\n✅ 模型下载完成! 路径: {MODEL_DIR}")


if __name__ == "__main__":
    main()
