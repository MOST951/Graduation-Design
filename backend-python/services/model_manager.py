"""
全局单例模型管理器 — 便捷 API
================================

对 services/model_singleton.py 的轻量封装，提供：
- get_model()      → 返回已加载的 BERT 模型
- get_tokenizer()  → 返回已加载的 Tokenizer
- get_device()     → 返回推理设备

所有方法首次调用时触发加载，后续直接返回缓存实例。
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_model() -> Optional[Any]:
    """
    获取全局唯一的 BERT 模型实例（首次调用时自动加载）。

    Returns:
        model 或 None（依赖缺失 / 加载失败时）
    """
    from services.model_singleton import get_bert_tokenizer_and_model
    _, model, _ = get_bert_tokenizer_and_model()
    return model


def get_tokenizer() -> Optional[Any]:
    """
    获取全局唯一的 Tokenizer 实例。

    Returns:
        tokenizer 或 None
    """
    from services.model_singleton import get_bert_tokenizer_and_model
    tokenizer, _, _ = get_bert_tokenizer_and_model()
    return tokenizer


def get_device() -> Optional[Any]:
    """
    获取推理设备（cuda / cpu）。

    Returns:
        torch.device 或 None
    """
    from services.model_singleton import get_bert_tokenizer_and_model
    _, _, device = get_bert_tokenizer_and_model()
    return device
