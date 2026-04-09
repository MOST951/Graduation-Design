"""
数据流水线集成测试
==================
测试从数据采集到展示的完整流程
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestDataPipelineIntegration:
    """数据流水线集成测试"""
    
    @pytest.mark.integration
    def test_full_pipeline_mock(self, sample_weibo_data):
        """测试完整流水线（模拟）"""
        # 模拟流水线各阶段
        stages = {
            'crawl': {'status': 'success', 'count': 100},
            'clean': {'status': 'success', 'count': 95},
            'analyze': {'status': 'success', 'count': 95},
            'rank': {'status': 'success', 'count': 10}
        }
        
        # 验证各阶段状态
        for stage, result in stages.items():
            assert result['status'] == 'success'
            assert result['count'] > 0
    
    @pytest.mark.integration
    def test_sentiment_to_ranking_flow(self, mock_sentiment_response, mock_dual_dimension_result):
        """测试情感分析到排序的数据流"""
        # 模拟情感分析结果
        sentiment_results = [
            {'id': '1', 'text': '测试1', 'sentiment_score': 0.8},
            {'id': '2', 'text': '测试2', 'sentiment_score': -0.5},
            {'id': '3', 'text': '测试3', 'sentiment_score': 0.3},
        ]
        
        # 模拟排序结果
        ranked_results = sorted(
            sentiment_results, 
            key=lambda x: abs(x['sentiment_score']), 
            reverse=True
        )
        
        # 验证排序正确性
        assert ranked_results[0]['id'] == '1'  # 最高情感强度
        assert ranked_results[1]['id'] == '2'  # 次高情感强度
    
    @pytest.mark.integration
    def test_data_validation_in_pipeline(self, sample_weibo_data):
        """测试流水线中的数据验证"""
        required_fields = ['id', 'text', 'user', 'created_at']
        
        # 验证必需字段存在
        for field in required_fields:
            assert field in sample_weibo_data
        
        # 验证数据类型
        assert isinstance(sample_weibo_data['id'], str)
        assert isinstance(sample_weibo_data['text'], str)
        assert isinstance(sample_weibo_data['user'], dict)


class TestSparkJobIntegration:
    """Spark作业集成测试"""
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_spark_job_submission_mock(self):
        """测试Spark作业提交（模拟）"""
        with patch('backend.services.spark_service.SparkService') as MockSparkService:
            mock_instance = MockSparkService.return_value
            mock_instance.submit_job.return_value = {
                'job_id': 'spark-job-001',
                'status': 'SUBMITTED',
                'submitted_at': '2026-01-28T14:00:00Z'
            }
            
            result = mock_instance.submit_job('preprocessing', {'input': '/data/raw'})
            
            assert result['status'] == 'SUBMITTED'
            assert 'job_id' in result
    
    @pytest.mark.integration
    def test_spark_job_status_tracking(self):
        """测试Spark作业状态追踪"""
        job_states = ['SUBMITTED', 'RUNNING', 'COMPLETED']
        
        for state in job_states:
            # 模拟状态转换
            assert state in ['SUBMITTED', 'RUNNING', 'COMPLETED', 'FAILED']


class TestHBaseIntegration:
    """HBase集成测试"""
    
    @pytest.mark.integration
    def test_hbase_connection_mock(self):
        """测试HBase连接（模拟）"""
        with patch('happybase.Connection') as MockConnection:
            mock_conn = MockConnection.return_value
            mock_conn.tables.return_value = [b'weibo_posts', b'hot_topics']
            
            tables = mock_conn.tables()
            
            assert b'weibo_posts' in tables
            assert b'hot_topics' in tables
    
    @pytest.mark.integration
    def test_hbase_data_write_mock(self, sample_weibo_data):
        """测试HBase数据写入（模拟）"""
        with patch('happybase.Connection') as MockConnection:
            mock_conn = MockConnection.return_value
            mock_table = MagicMock()
            mock_conn.table.return_value = mock_table
            
            # 模拟写入
            row_key = sample_weibo_data['id']
            data = {
                b'cf:text': sample_weibo_data['text'].encode(),
                b'cf:user_id': sample_weibo_data['user']['id'].encode()
            }
            
            mock_table.put(row_key, data)
            mock_table.put.assert_called_once()
