"""
模型管理器 - 预加载与缓存优化

解决问题：
1. 模型加载耗时长（2-3秒）
2. 答辩演示等待时间过长

优化方案：
1. 应用启动时预加载模型
2. 单例模式缓存模型实例
3. 懒加载 + 预热机制
4. ONNX Runtime加速（可选）

作者：毕业设计
日期：2024-12
"""

import os
import sys
import time
import threading
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from functools import wraps
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局单例模型加载器
_SINGLETON_AVAILABLE = False
try:
    from services.model_singleton import (
        get_bert_tokenizer_and_model as _singleton_load,
        is_bert_available as _singleton_bert_available,
        get_model_info as _singleton_info,
    )
    _SINGLETON_AVAILABLE = True
except ImportError:
    pass


class ModelStatus(Enum):
    """模型状态"""
    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


@dataclass
class ModelInfo:
    """模型信息"""
    name: str
    status: ModelStatus = ModelStatus.NOT_LOADED
    instance: Any = None
    load_time: float = 0.0
    last_used: float = 0.0
    use_count: int = 0
    error_message: str = ""


class ModelManager:
    """
    模型管理器（单例模式）
    
    功能：
    1. 统一管理所有模型的加载和缓存
    2. 支持预加载和懒加载
    3. 提供模型预热功能
    4. 线程安全
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._models: Dict[str, ModelInfo] = {}
        self._loaders: Dict[str, Callable] = {}
        self._warmup_funcs: Dict[str, Callable] = {}
        self._model_lock = threading.Lock()
        self._initialized = True
        
        # 注册默认模型
        self._register_default_models()
        
        logger.info("ModelManager初始化完成")
    
    def _register_default_models(self):
        """注册默认模型加载器"""
        
        # 1. 情感词典
        self.register_model(
            "sentiment_lexicon",
            self._load_sentiment_lexicon,
            self._warmup_lexicon
        )
        
        # 2. ChineseBERT情感分析
        self.register_model(
            "chinese_bert",
            self._load_chinese_bert,
            self._warmup_bert
        )
        
        # 3. 混合情感分析器
        self.register_model(
            "hybrid_analyzer",
            self._load_hybrid_analyzer,
            self._warmup_hybrid
        )
        
        # 4. 三维度模型
        self.register_model(
            "tri_dimension",
            self._load_tri_dimension,
            self._warmup_tri_dimension
        )
    
    def register_model(
        self,
        name: str,
        loader: Callable,
        warmup_func: Callable = None
    ):
        """
        注册模型
        
        Args:
            name: 模型名称
            loader: 加载函数
            warmup_func: 预热函数（可选）
        """
        self._models[name] = ModelInfo(name=name)
        self._loaders[name] = loader
        if warmup_func:
            self._warmup_funcs[name] = warmup_func
        logger.info(f"模型已注册: {name}")
    
    def get_model(self, name: str, auto_load: bool = True) -> Any:
        """
        获取模型实例
        
        Args:
            name: 模型名称
            auto_load: 是否自动加载
            
        Returns:
            模型实例
        """
        if name not in self._models:
            raise ValueError(f"未知模型: {name}")
        
        model_info = self._models[name]
        
        # 如果已加载，直接返回
        if model_info.status == ModelStatus.READY and model_info.instance:
            model_info.last_used = time.time()
            model_info.use_count += 1
            return model_info.instance
        
        # 自动加载
        if auto_load:
            return self.load_model(name)
        
        return None
    
    def load_model(self, name: str) -> Any:
        """
        加载模型
        
        Args:
            name: 模型名称
            
        Returns:
            模型实例
        """
        if name not in self._loaders:
            raise ValueError(f"未注册的模型: {name}")
        
        model_info = self._models[name]
        
        # 避免重复加载
        with self._model_lock:
            if model_info.status == ModelStatus.READY:
                return model_info.instance
            
            if model_info.status == ModelStatus.LOADING:
                # 等待加载完成
                while model_info.status == ModelStatus.LOADING:
                    time.sleep(0.1)
                return model_info.instance
            
            model_info.status = ModelStatus.LOADING
        
        try:
            logger.info(f"开始加载模型: {name}")
            start_time = time.time()
            
            # 调用加载函数
            instance = self._loaders[name]()
            
            load_time = time.time() - start_time
            
            with self._model_lock:
                model_info.instance = instance
                model_info.status = ModelStatus.READY
                model_info.load_time = load_time
                model_info.last_used = time.time()
            
            logger.info(f"模型加载完成: {name}, 耗时: {load_time:.2f}秒")
            return instance
            
        except Exception as e:
            with self._model_lock:
                model_info.status = ModelStatus.ERROR
                model_info.error_message = str(e)
            logger.error(f"模型加载失败: {name}, 错误: {e}")
            raise
    
    def preload_all(self, async_load: bool = True):
        """
        预加载所有模型
        
        Args:
            async_load: 是否异步加载
        """
        logger.info("开始预加载所有模型...")
        
        if async_load:
            threads = []
            for name in self._loaders.keys():
                t = threading.Thread(target=self.load_model, args=(name,))
                t.start()
                threads.append(t)
            
            # 等待所有加载完成
            for t in threads:
                t.join()
        else:
            for name in self._loaders.keys():
                try:
                    self.load_model(name)
                except Exception as e:
                    logger.error(f"预加载失败: {name}, {e}")
        
        logger.info("所有模型预加载完成")
    
    def preload_essential(self):
        """预加载核心模型（答辩演示必需）"""
        essential_models = ["sentiment_lexicon", "tri_dimension"]
        
        logger.info("预加载核心模型...")
        for name in essential_models:
            try:
                self.load_model(name)
            except Exception as e:
                logger.error(f"核心模型加载失败: {name}, {e}")
        
        logger.info("核心模型预加载完成")
    
    def warmup_model(self, name: str):
        """
        预热模型（执行一次推理）
        
        Args:
            name: 模型名称
        """
        if name not in self._warmup_funcs:
            logger.warning(f"模型 {name} 没有预热函数")
            return
        
        model = self.get_model(name)
        if model:
            logger.info(f"预热模型: {name}")
            start = time.time()
            self._warmup_funcs[name](model)
            logger.info(f"模型预热完成: {name}, 耗时: {time.time()-start:.2f}秒")
    
    def warmup_all(self):
        """预热所有已加载的模型"""
        for name, info in self._models.items():
            if info.status == ModelStatus.READY:
                self.warmup_model(name)
    
    def get_status(self) -> Dict[str, Any]:
        """获取所有模型状态"""
        status = {}
        for name, info in self._models.items():
            status[name] = {
                "status": info.status.value,
                "load_time": round(info.load_time, 2),
                "use_count": info.use_count,
                "last_used": info.last_used,
                "error": info.error_message if info.status == ModelStatus.ERROR else None,
            }
        return status
    
    def unload_model(self, name: str):
        """卸载模型释放内存"""
        if name in self._models:
            with self._model_lock:
                self._models[name].instance = None
                self._models[name].status = ModelStatus.NOT_LOADED
            logger.info(f"模型已卸载: {name}")
    
    # ==================== 模型加载函数 ====================
    
    def _load_sentiment_lexicon(self):
        """加载情感词典"""
        try:
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from spark.sentiment_analyzer import SentimentLexicon
            
            # 预编译词典
            lexicon = {
                "positive": dict(SentimentLexicon.POSITIVE_WORDS),
                "negative": dict(SentimentLexicon.NEGATIVE_WORDS),
                "degree": dict(SentimentLexicon.DEGREE_WORDS),
                "negation": list(SentimentLexicon.NEGATION_WORDS),
            }
            return lexicon
        except Exception as e:
            logger.warning(f"情感词典加载失败: {e}, 使用默认词典")
            return self._get_default_lexicon()
    
    def _get_default_lexicon(self):
        """获取默认词典"""
        return {
            "positive": {"好": 1, "棒": 1, "赞": 1, "喜欢": 1, "优秀": 1.5},
            "negative": {"差": -1, "烂": -1, "糟糕": -1.5, "失望": -1},
            "degree": {"很": 1.5, "非常": 2, "特别": 2, "有点": 0.5},
            "negation": ["不", "没", "无", "别"],
        }
    
    def _load_chinese_bert(self):
        """加载ChineseBERT模型，优先委托全局单例"""
        # 优先使用全局单例（实际会复用 ChineseBertSentimentAnalyzer 内部的单例）
        if _SINGLETON_AVAILABLE:
            try:
                tokenizer, model, device = _singleton_load()
                if tokenizer is not None and model is not None:
                    logger.info("[ModelManager] ChineseBERT已从全局单例获取")
            except Exception as e:
                logger.warning(f"[ModelManager] 全局单例加载失败: {e}")
        
        try:
            from spark.chinese_bert_sentiment import ChineseBertSentimentAnalyzer
            analyzer = ChineseBertSentimentAnalyzer()
            analyzer.initialize()
            return analyzer
        except ImportError:
            logger.warning("ChineseBERT模块未安装，使用模拟分析器")
            return MockBertAnalyzer()
        except Exception as e:
            logger.warning(f"ChineseBERT加载失败: {e}, 使用模拟分析器")
            return MockBertAnalyzer()
    
    def _load_hybrid_analyzer(self):
        """加载混合分析器，内部会自动复用全局单例"""
        try:
            from services.hybrid_analyzer import HybridSentimentAnalyzer
            analyzer = HybridSentimentAnalyzer()
            return analyzer
        except ImportError:
            try:
                from spark.chinese_bert_sentiment import HybridSentimentAnalyzer
                analyzer = HybridSentimentAnalyzer()
                analyzer.initialize()
                return analyzer
            except ImportError:
                logger.warning("混合分析器模块未安装")
                return None
        except Exception as e:
            logger.warning(f"混合分析器加载失败: {e}")
            return None
    
    def _load_tri_dimension(self):
        """加载三维度模型"""
        try:
            from spark.tri_dimension_model_v2 import TriDimensionModelV2
            model = TriDimensionModelV2()
            return model
        except ImportError:
            logger.warning("三维度模型模块未安装")
            return MockTriDimensionModel()
        except Exception as e:
            logger.warning(f"三维度模型加载失败: {e}")
            return MockTriDimensionModel()
    
    # ==================== 预热函数 ====================
    
    def _warmup_lexicon(self, lexicon):
        """预热词典"""
        test_text = "这个产品非常好，我很喜欢"
        # 模拟词典查询
        for word in test_text:
            _ = lexicon["positive"].get(word, 0)
            _ = lexicon["negative"].get(word, 0)
    
    def _warmup_bert(self, analyzer):
        """预热BERT模型"""
        test_texts = [
            "这个产品非常好",
            "服务态度很差",
            "一般般吧",
        ]
        if hasattr(analyzer, 'analyze_batch'):
            analyzer.analyze_batch(test_texts, batch_size=3)
        elif hasattr(analyzer, 'analyze'):
            for text in test_texts:
                analyzer.analyze(text)
    
    def _warmup_hybrid(self, analyzer):
        """预热混合分析器"""
        if analyzer and hasattr(analyzer, 'analyze'):
            analyzer.analyze("测试文本预热")
    
    def _warmup_tri_dimension(self, model):
        """预热三维度模型"""
        if model and hasattr(model, 'calculate_tri_score'):
            model.calculate_tri_score(0.5, 0.5)


class MockBertAnalyzer:
    """模拟BERT分析器（用于BERT不可用时）"""
    
    def __init__(self):
        self.is_mock = True
    
    def analyze(self, text: str) -> Dict:
        """模拟分析"""
        import random
        score = random.uniform(-1, 1)
        return {
            "text": text,
            "label": "positive" if score > 0.2 else "negative" if score < -0.2 else "neutral",
            "score": score,
            "confidence": random.uniform(0.6, 0.95),
            "is_mock": True,
        }
    
    def analyze_batch(self, texts: list, batch_size: int = 32) -> list:
        """模拟批量分析"""
        return [self.analyze(text) for text in texts]


class MockTriDimensionModel:
    """模拟三维度模型"""
    
    def __init__(self):
        self.is_mock = True
    
    def calculate_tri_score(self, sentiment: float, heat: float) -> float:
        return 0.5 * sentiment + 0.5 * heat


# ==================== 装饰器 ====================

def with_model(model_name: str):
    """
    模型注入装饰器
    
    自动获取模型并注入到函数参数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = ModelManager()
            model = manager.get_model(model_name)
            return func(model, *args, **kwargs)
        return wrapper
    return decorator


def ensure_model_loaded(model_name: str):
    """
    确保模型已加载的装饰器
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = ModelManager()
            manager.get_model(model_name)  # 确保加载
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ==================== 预加载脚本 ====================

def preload_models_on_startup():
    """
    应用启动时预加载模型
    
    在app.py中调用此函数
    """
    # 设置 TRANSFORMERS_CACHE 环境变量，避免重复下载
    if not os.environ.get("TRANSFORMERS_CACHE"):
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model_cache")
        os.environ["TRANSFORMERS_CACHE"] = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    manager = ModelManager()
    
    # 异步预加载核心模型
    def _preload():
        # 先通过全局单例加载 BERT（只加载一次）
        try:
            from services.model_singleton import preload as singleton_preload
            singleton_preload()
        except ImportError:
            logger.warning("model_singleton 不可用，跳过 BERT 单例预加载")
        except Exception as e:
            logger.warning(f"BERT 单例预加载失败: {e}")

        manager.preload_essential()
        manager.warmup_all()
    
    thread = threading.Thread(target=_preload, daemon=True)
    thread.start()
    
    logger.info("模型预加载任务已启动（后台运行）")


def preload_models_sync():
    """
    同步预加载模型（阻塞式）
    
    用于确保模型在使用前已加载
    """
    manager = ModelManager()
    manager.preload_essential()
    manager.warmup_all()
    logger.info("模型预加载完成（同步）")


# ==================== 便捷函数 ====================

def get_model_manager() -> ModelManager:
    """获取模型管理器实例"""
    return ModelManager()


def get_sentiment_lexicon():
    """获取情感词典"""
    return ModelManager().get_model("sentiment_lexicon")


def get_bert_analyzer():
    """获取BERT分析器"""
    return ModelManager().get_model("chinese_bert")


def get_hybrid_analyzer():
    """获取混合分析器"""
    return ModelManager().get_model("hybrid_analyzer")


def get_tri_dimension_model():
    """获取三维度模型"""
    return ModelManager().get_model("tri_dimension")


# ==================== 测试 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("模型管理器测试")
    print("=" * 60)
    
    manager = ModelManager()
    
    # 测试预加载
    print("\n1. 预加载核心模型...")
    start = time.time()
    manager.preload_essential()
    print(f"预加载耗时: {time.time() - start:.2f}秒")
    
    # 测试获取模型
    print("\n2. 获取模型（应该立即返回）...")
    start = time.time()
    lexicon = manager.get_model("sentiment_lexicon")
    print(f"获取词典耗时: {time.time() - start:.4f}秒")
    
    start = time.time()
    tri_model = manager.get_model("tri_dimension")
    print(f"获取三维度模型耗时: {time.time() - start:.4f}秒")
    
    # 测试预热
    print("\n3. 预热模型...")
    manager.warmup_all()
    
    # 查看状态
    print("\n4. 模型状态:")
    status = manager.get_status()
    for name, info in status.items():
        print(f"  {name}: {info['status']}, 加载耗时: {info['load_time']}秒, 使用次数: {info['use_count']}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
