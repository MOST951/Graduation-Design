"""
微博情感分析系统 - 测试配置
============================
提供测试夹具和通用配置
"""

import os
import sys
import pytest
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

# 设置测试环境变量
os.environ['TESTING'] = 'True'
os.environ['FLASK_ENV'] = 'testing'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
os.environ['LOG_LEVEL'] = 'WARNING'


@pytest.fixture(scope='session')
def app():
    """创建测试应用实例"""
    from backend.app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['DEBUG'] = False
    return flask_app


@pytest.fixture(scope='session')
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def sample_weibo_data() -> Dict[str, Any]:
    """示例微博数据"""
    return {
        "id": "4912345678901234",
        "mid": "4912345678901234",
        "text": "今天天气真好，心情愉快！#好心情#",
        "user": {
            "id": "user_001",
            "screen_name": "测试用户",
            "followers_count": 1000,
            "friends_count": 500,
            "verified": False
        },
        "created_at": datetime.now().isoformat(),
        "reposts_count": 10,
        "comments_count": 5,
        "attitudes_count": 20,
        "source": "微博 weibo.com"
    }


@pytest.fixture
def sample_weibo_list(sample_weibo_data) -> list:
    """示例微博列表"""
    return [
        {**sample_weibo_data, "id": f"491234567890123{i}", "text": f"测试微博 {i}"}
        for i in range(5)
    ]


@pytest.fixture
def positive_text_samples() -> list:
    """正面情感文本样本"""
    return [
        "今天天气真好，心情愉快！",
        "这个产品太棒了，强烈推荐！",
        "感谢大家的支持，非常开心！",
        "终于完成了，太激动了！",
        "这家餐厅的服务真的很好！"
    ]


@pytest.fixture
def negative_text_samples() -> list:
    """负面情感文本样本"""
    return [
        "服务太差了，很不满意",
        "这个产品质量太烂了",
        "等了一个小时还没到，太失望了",
        "完全是浪费钱，后悔购买",
        "态度恶劣，再也不会来了"
    ]


@pytest.fixture
def neutral_text_samples() -> list:
    """中性情感文本样本"""
    return [
        "今天是周一",
        "北京的天气是晴天",
        "这个产品的价格是199元",
        "会议定在下午三点",
        "新版本已经发布"
    ]


@pytest.fixture
def mock_sentiment_response() -> Dict[str, Any]:
    """模拟情感分析响应"""
    return {
        "sentiment": "positive",
        "confidence": 0.89,
        "score": 0.75,
        "categories": ["happiness", "optimism"],
        "keywords": ["天气", "心情", "愉快"]
    }


@pytest.fixture
def mock_dual_dimension_result() -> Dict[str, Any]:
    """模拟双维度排序结果"""
    return {
        "topic_id": 1,
        "name": "人工智能",
        "keywords": ["AI", "大模型", "GPT"],
        "composite_score": 0.7234,
        "sentiment_avg": 0.8,
        "popularity_score": 0.5891,
        "rank": 1,
        "trend": "up",
        "post_count": 1500
    }
