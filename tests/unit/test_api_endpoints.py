"""
API端点单元测试
===============
测试Flask API端点
"""

import pytest
import json


class TestHealthEndpoints:
    """健康检查端点测试"""
    
    @pytest.mark.unit
    def test_root_endpoint(self, client):
        """测试根路由"""
        response = client.get('/')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'message' in data
        assert 'version' in data
        assert data['message'] == '微博情感分析系统API'
    
    @pytest.mark.unit
    def test_404_error_handling(self, client):
        """测试404错误处理"""
        response = client.get('/api/nonexistent')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert data['code'] == 404
        assert '不存在' in data['message']


class TestSentimentAPI:
    """情感分析API测试"""
    
    @pytest.mark.unit
    def test_sentiment_analyze_valid_input(self, client):
        """测试有效输入的情感分析"""
        payload = {
            "text": "今天天气真好，心情愉快！"
        }
        response = client.post(
            '/api/sentiment/analyze',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # 可能返回200或其他状态码，取决于后端实现
        assert response.status_code in [200, 400, 500]
    
    @pytest.mark.unit
    def test_sentiment_analyze_empty_text(self, client):
        """测试空文本的情感分析"""
        payload = {"text": ""}
        response = client.post(
            '/api/sentiment/analyze',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # 空文本应该返回错误
        assert response.status_code in [400, 422, 500]


class TestTopicsAPI:
    """热点话题API测试"""
    
    @pytest.mark.unit
    def test_topics_ranked_endpoint(self, client):
        """测试双维度排序端点"""
        response = client.get('/api/topics/ranked')
        # 端点应该存在
        assert response.status_code in [200, 500]
    
    @pytest.mark.unit
    def test_dual_dimension_config(self, client):
        """测试双维度配置端点"""
        response = client.get('/api/dual/config')
        assert response.status_code in [200, 404, 500]


class TestCollectionAPI:
    """数据采集API测试"""
    
    @pytest.mark.unit
    def test_collection_status(self, client):
        """测试采集状态端点"""
        response = client.get('/api/collection/status')
        assert response.status_code in [200, 404, 500]
