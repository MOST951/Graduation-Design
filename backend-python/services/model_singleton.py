"""
ChineseBERT 全局单例模型加载器
================================

解决问题：
1. 多处重复加载同一预训练模型，浪费内存和启动时间
2. 无统一缓存目录，每次可能重新下载权重
3. pipeline_service / hybrid_analyzer / model_manager 各自独立初始化

设计思路：
- 模块级变量 + threading.Lock 实现懒加载单例
- 首次 get_bert_tokenizer_and_model() 时加载，后续直接返回缓存实例
- 通过 TRANSFORMERS_CACHE 环境变量控制下载目录
- 对外暴露简洁 API，内部屏蔽 GPU/CPU、FP16 等差异

作者：毕业设计
日期：2024-12
"""

import os
import sys
import time
import logging
import threading
from typing import Tuple, Optional, Any

logger = logging.getLogger(__name__)

# ==================== 环境变量 & 缓存目录 ====================

def _resolve_cache_dir() -> str:
    """
    确定模型缓存目录，优先级：
    1. TRANSFORMERS_CACHE 环境变量
    2. config.model.model_cache_dir
    3. 项目根目录下 ./model_cache
    """
    env_cache = os.environ.get("TRANSFORMERS_CACHE")
    if env_cache:
        return env_cache

    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from config import config
        cache_dir = config.model.model_cache_dir
    except Exception:
        cache_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "model_cache"
        )

    # 同步写回环境变量，让 transformers 库自动复用
    os.environ["TRANSFORMERS_CACHE"] = cache_dir
    return cache_dir


def _resolve_model_name() -> str:
    """
    获取模型名称或本地路径，优先级：
    1. config.model.default_sentiment_model
    2. 本地 ./models/chinese-bert-wwm-ext 目录（如果存在）
    3. bert-base-chinese（兜底）
    """
    # 尝试从 config 读取
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from config import config
        candidate = config.model.default_sentiment_model
        # 如果是本地路径，检查是否存在
        if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, "config.json")):
            return candidate
    except Exception:
        pass

    # 尝试本地目录
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_model = os.path.join(backend_dir, "models", "chinese-bert-wwm-ext")
    if os.path.isdir(local_model) and os.path.isfile(os.path.join(local_model, "config.json")):
        return local_model

    return "bert-base-chinese"


# ==================== 单例状态 ====================

_lock = threading.Lock()
_tokenizer: Any = None
_model: Any = None
_device: Any = None
_initialized: bool = False
_use_fallback: bool = False
_model_name: str = ""
_load_time: float = 0.0


def _setup_device():
    """自动选择 GPU / CPU"""
    try:
        import torch
        if torch.cuda.is_available():
            dev = torch.device("cuda")
            logger.info(f"[ModelSingleton] 使用 GPU: {torch.cuda.get_device_name(0)}")
        else:
            dev = torch.device("cpu")
            logger.info("[ModelSingleton] 使用 CPU")
        return dev
    except ImportError:
        return None


def _do_load() -> Tuple[Any, Any, Any]:
    """
    实际执行模型加载（仅被调用一次）。

    Returns:
        (tokenizer, model, device)
    """
    global _use_fallback

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
    except ImportError as e:
        logger.warning(f"[ModelSingleton] 深度学习依赖缺失: {e}，回退到词典模式")
        _use_fallback = True
        return None, None, None

    cache_dir = _resolve_cache_dir()
    model_name = _resolve_model_name()
    os.makedirs(cache_dir, exist_ok=True)

    is_local = os.path.isdir(model_name)
    logger.info(f"[ModelSingleton] 加载模型: {model_name}  本地: {is_local}  缓存目录: {cache_dir}")

    device = _setup_device()

    start = time.time()
    try:
        load_kwargs = {"local_files_only": True} if is_local else {"cache_dir": cache_dir}
        tokenizer = AutoTokenizer.from_pretrained(
            model_name, **load_kwargs
        )
        model = AutoModelForSequenceClassification.from_pretrained(
            model_name, num_labels=3, **load_kwargs
        )
        model.to(device)
        model.eval()

        # FP16 加速（仅 GPU）
        if device and device.type == "cuda":
            try:
                model.half()
                logger.info("[ModelSingleton] 已启用 FP16 半精度推理")
            except Exception:
                pass

        elapsed = time.time() - start
        global _model_name, _load_time
        _model_name = model_name
        _load_time = elapsed
        logger.info(f"[ModelSingleton] 模型加载完成，耗时 {elapsed:.2f}s")
        return tokenizer, model, device

    except Exception as e:
        logger.error(f"[ModelSingleton] 模型加载失败: {e}，回退到词典模式")
        _use_fallback = True
        return None, None, None


# ==================== 公共 API ====================

def get_bert_tokenizer_and_model() -> Tuple[Any, Any, Any]:
    """
    获取全局唯一的 (tokenizer, model, device) 三元组。

    首次调用时加载，后续直接返回缓存。线程安全。

    Returns:
        (tokenizer, model, device)  —— 加载失败时全部为 None
    """
    global _tokenizer, _model, _device, _initialized

    if _initialized:
        return _tokenizer, _model, _device

    with _lock:
        # double-check
        if _initialized:
            return _tokenizer, _model, _device

        _tokenizer, _model, _device = _do_load()
        _initialized = True

    return _tokenizer, _model, _device


def is_bert_available() -> bool:
    """模型是否可用（已加载且未回退）"""
    if not _initialized:
        get_bert_tokenizer_and_model()
    return not _use_fallback and _model is not None


def get_model_info() -> dict:
    """获取模型加载信息（供 /api/models/status 使用）"""
    return {
        "initialized": _initialized,
        "use_fallback": _use_fallback,
        "model_name": _model_name,
        "load_time_sec": round(_load_time, 2),
        "cache_dir": os.environ.get("TRANSFORMERS_CACHE", ""),
        "device": str(_device) if _device else "N/A",
    }


def preload() -> None:
    """
    显式预加载。可在 app 启动时调用::

        from services.model_singleton import preload
        preload()
    """
    get_bert_tokenizer_and_model()
    # 预热：跑一次推理让 CUDA kernel / JIT 编译就绪
    if is_bert_available():
        _warmup()


def _warmup():
    """对模型执行一次小批量推理以预热"""
    try:
        import torch

        texts = ["测试文本", "这个产品非常好", "服务态度很差"]
        inputs = _tokenizer(
            texts, padding=True, truncation=True,
            max_length=128, return_tensors="pt"
        )
        inputs = {k: v.to(_device) for k, v in inputs.items()}
        with torch.no_grad():
            _model(**inputs)
        logger.info("[ModelSingleton] 模型预热完成")
    except Exception as e:
        logger.warning(f"[ModelSingleton] 预热失败: {e}")
