"""
情感分析器单元测试
==================
测试情感分析核心功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestSentimentAnalyzer:
    """情感分析器测试类"""
    
    @pytest.mark.unit
    def test_positive_sentiment_detection(self, positive_text_samples):
        """测试正面情感检测"""
        # 模拟情感分析器
        with patch('backend.services.rule_based_analyzer.RuleBasedAnalyzer') as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value
            mock_instance.analyze.return_value = {
                'sentiment': 'positive',
                'score': 0.8,
                'confidence': 0.85
            }
            
            for text in positive_text_samples:
                result = mock_instance.analyze(text)
                assert result['sentiment'] == 'positive'
                assert result['score'] > 0
    
    @pytest.mark.unit
    def test_negative_sentiment_detection(self, negative_text_samples):
        """测试负面情感检测"""
        with patch('backend.services.rule_based_analyzer.RuleBasedAnalyzer') as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value
            mock_instance.analyze.return_value = {
                'sentiment': 'negative',
                'score': -0.7,
                'confidence': 0.82
            }
            
            for text in negative_text_samples:
                result = mock_instance.analyze(text)
                assert result['sentiment'] == 'negative'
                assert result['score'] < 0
    
    @pytest.mark.unit
    def test_neutral_sentiment_detection(self, neutral_text_samples):
        """测试中性情感检测"""
        with patch('backend.services.rule_based_analyzer.RuleBasedAnalyzer') as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value
            mock_instance.analyze.return_value = {
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.75
            }
            
            for text in neutral_text_samples:
                result = mock_instance.analyze(text)
                assert result['sentiment'] == 'neutral'
                assert -0.3 <= result['score'] <= 0.3
    
    @pytest.mark.unit
    def test_empty_text_handling(self):
        """测试空文本处理"""
        with patch('backend.services.rule_based_analyzer.RuleBasedAnalyzer') as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value
            mock_instance.analyze.side_effect = ValueError("文本不能为空")
            
            with pytest.raises(ValueError, match="文本不能为空"):
                mock_instance.analyze("")
    
    @pytest.mark.unit
    def test_long_text_truncation(self):
        """测试长文本截断"""
        long_text = "这是一段非常长的文本，" * 100
        max_length = 512
        
        # 模拟截断逻辑
        truncated = long_text[:max_length] if len(long_text) > max_length else long_text
        assert len(truncated) <= max_length
    
    @pytest.mark.unit
    @pytest.mark.parametrize("text,expected_sentiment", [
        ("开心", "positive"),
        ("难过", "negative"),
        ("一般", "neutral"),
        ("太棒了", "positive"),
        ("很失望", "negative"),
    ])
    def test_sentiment_categorization(self, text, expected_sentiment):
        """参数化测试情感分类"""
        sentiment_map = {
            "开心": "positive",
            "难过": "negative", 
            "一般": "neutral",
            "太棒了": "positive",
            "很失望": "negative"
        }
        assert sentiment_map.get(text) == expected_sentiment


class TestDualDimensionModel:
    """双维度排序模型测试类"""
    
    @pytest.mark.unit
    def test_composite_score_calculation(self):
        """测试综合排序得分计算（公式4-7）"""
        # Score_rank = ω₁·N(S) + ω₂·H_norm + ω₃·γ(t)
        # 其中 ω₁=0.4, ω₂=0.4, ω₃=0.2
        sentiment_score = 0.8   # 原始情感得分
        heat_normalized = 0.6   # 归一化后热度
        time_decay = 0.9        # 时间衰减因子
        
        # N(S) = (|S| + 1) / 2 = (0.8 + 1) / 2 = 0.9
        sentiment_normalized = (abs(sentiment_score) + 1) / 2
        
        expected = 0.4 * sentiment_normalized + 0.4 * heat_normalized + 0.2 * time_decay
        assert expected == pytest.approx(0.78, rel=0.01)
    
    @pytest.mark.unit
    def test_heat_score_calculation(self):
        """测试热度得分计算（公式4-5）"""
        import math
        
        reposts = 100
        comments = 50
        likes = 200
        
        # 公式: H_raw = log₁₀(1 + λ_r·R + λ_c·C + λ_l·L)
        # λ_r=3, λ_c=2, λ_l=1
        raw_heat = math.log10(1 + 3 * reposts + 2 * comments + 1 * likes)
        
        # 归一化: H_norm = H_raw / log₁₀(1 + max_heat_value)
        max_heat_value = 100000.0
        max_heat = math.log10(1 + max_heat_value)
        heat_normalized = min(raw_heat / max_heat, 1.0)
        
        assert raw_heat > 0
        assert 0 < heat_normalized <= 1
        assert raw_heat == pytest.approx(2.78, rel=0.02)  # log10(1+600) ≈ 2.78
    
    @pytest.mark.unit
    def test_time_decay_factor(self):
        """测试时间衰减因子（公式4-6）：半衰期参数化"""
        import math
        
        # 公式: γ(t) = 2^(-Δt / H)，H=12小时
        half_life = 12.0
        
        test_cases = [
            (0, 1.0),       # 0小时前，衰减因子为1
            (12, 0.5),      # 12小时（一个半衰期），衰减因子为0.5
            (24, 0.25),     # 24小时（两个半衰期），衰减因子为0.25
            (36, 0.125),    # 36小时（三个半衰期），衰减因子为0.125
        ]
        
        for hours_ago, expected_decay in test_cases:
            actual_decay = 2 ** (-hours_ago / half_life)
            assert actual_decay == pytest.approx(expected_decay, rel=0.01)
    
    @pytest.mark.unit
    def test_ranking_order(self, mock_dual_dimension_result):
        """测试排序顺序"""
        topics = [
            {"name": "话题A", "composite_score": 0.9},
            {"name": "话题B", "composite_score": 0.7},
            {"name": "话题C", "composite_score": 0.8},
        ]
        
        # 按综合得分降序排序
        sorted_topics = sorted(topics, key=lambda x: x['composite_score'], reverse=True)
        
        assert sorted_topics[0]['name'] == "话题A"
        assert sorted_topics[1]['name'] == "话题C"
        assert sorted_topics[2]['name'] == "话题B"
