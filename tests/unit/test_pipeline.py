"""
数据流水线端到端测试
==================
测试: 情感分析(级联策略) → 双维度排序 → 结果完整性

不依赖MySQL，直接测试 pipeline_service 的核心逻辑。
"""
import sys
import os
import math
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend-python'))

from services.pipeline_service import (
    PipelineConfig,
    SentimentStage,
    RankingStage,
)


class TestSentimentStage:
    """测试情感分析阶段(级联策略)"""

    def setup_method(self):
        self.config = PipelineConfig()
        self.stage = SentimentStage(self.config)

    def test_positive_text(self):
        """正面文本应返回 positive"""
        result = self.stage.analyze("这个产品太棒了，非常好用，强烈推荐！")
        assert result['sentiment_class'] == 'positive'
        assert result['score'] > 0
        assert result['dict_score'] is not None
        assert 'processing_time_ms' in result

    def test_negative_text(self):
        """负面文本应返回 negative"""
        result = self.stage.analyze("这也太差了，垃圾产品，非常失望")
        assert result['sentiment_class'] == 'negative'
        assert result['score'] < 0

    def test_neutral_text(self):
        """中性文本应返回 neutral"""
        result = self.stage.analyze("今天天气一般")
        assert result['sentiment_class'] == 'neutral'

    def test_cascade_method_field(self):
        """级联策略应返回 cascade-lexicon 或 cascade-bert"""
        result = self.stage.analyze("好棒好开心")
        assert result['method'].startswith('cascade-')

    def test_batch_analyze(self):
        """批量分析应正确标记 weibo_id"""
        weibos = [
            {'weibo_id': 1001, 'content': '太棒了'},
            {'weibo_id': 1002, 'content': '太差了'},
            {'weibo_id': 1003, 'content': '一般般'},
        ]
        results = self.stage.analyze_batch(weibos)
        assert len(results) == 3
        assert results[0]['weibo_id'] == 1001
        assert 'hybrid_score' in results[0]
        assert 'analysis_method' in results[0]  # 已从 method 重命名


class TestRankingStage:
    """测试双维度排序阶段"""

    def setup_method(self):
        self.config = PipelineConfig()
        self.stage = RankingStage(self.config)

    def test_sentiment_normalized(self):
        """公式4-4: N(S) = (|S| + 1) / 2"""
        assert self.stage._sentiment_normalized(0.8) == (0.8 + 1) / 2  # 0.9
        assert self.stage._sentiment_normalized(-0.6) == (0.6 + 1) / 2  # 0.8
        assert self.stage._sentiment_normalized(0.0) == 0.5

    def test_heat_raw(self):
        """公式4-5: H_raw = log₁₀(1 + λ_r·R + λ_c·C + λ_l·L), λ_r=1,λ_c=2,λ_l=1"""
        h = self.stage._heat_raw(reposts=100, comments=50, likes=200)
        expected = math.log10(1 + 1*100 + 2*50 + 1*200)  # log10(401)
        assert abs(h - expected) < 0.001

    def test_heat_normalized(self):
        """归一化后应在 [0, 1]"""
        h_raw = self.stage._heat_raw(100, 50, 200)
        h_norm = self.stage._heat_normalized(h_raw)
        assert 0 <= h_norm <= 1

    def test_time_decay(self):
        """公式4-6: γ(t) = 2^(-Δt/H), H=12"""
        now = datetime.now()

        # Δt = 0 → γ = 1.0
        assert abs(self.stage._time_decay(now, now) - 1.0) < 0.001

        # Δt = 12h → γ = 0.5
        t12 = now - timedelta(hours=12)
        assert abs(self.stage._time_decay(t12, now) - 0.5) < 0.001

        # Δt = 24h → γ = 0.25
        t24 = now - timedelta(hours=24)
        assert abs(self.stage._time_decay(t24, now) - 0.25) < 0.001

    def test_composite_score(self):
        """公式4-7: Score = ω₁·N(S) + ω₂·H_norm + ω₃·γ(t)"""
        now = datetime.now()
        weibos = [{
            'weibo_id': 2001,
            'hybrid_score': 0.8,
            'reposts_count': 100,
            'comments_count': 50,
            'attitudes_count': 200,
            'created_at': now,
        }]
        ranked = self.stage.rank(weibos)
        assert len(ranked) == 1

        r = ranked[0]
        # 手动计算验证
        n_s = (0.8 + 1) / 2  # 0.9
        h_raw = math.log10(1 + 1*100 + 2*50 + 1*200)
        max_h = math.log10(1 + self.config.max_heat_reference)
        h_norm = min(h_raw / max_h, 1.0)
        gamma = 1.0  # Δt ≈ 0
        expected = 0.4 * n_s + 0.4 * h_norm + 0.2 * gamma
        assert abs(r['composite_score'] - round(expected, 4)) < 0.01

    def test_ranking_order(self):
        """排序结果应按综合得分降序"""
        now = datetime.now()
        weibos = [
            {'weibo_id': 3001, 'hybrid_score': 0.3, 'reposts_count': 1,
             'comments_count': 0, 'attitudes_count': 0, 'created_at': now - timedelta(hours=48)},
            {'weibo_id': 3002, 'hybrid_score': 0.9, 'reposts_count': 1000,
             'comments_count': 500, 'attitudes_count': 2000, 'created_at': now},
            {'weibo_id': 3003, 'hybrid_score': 0.5, 'reposts_count': 50,
             'comments_count': 20, 'attitudes_count': 100, 'created_at': now - timedelta(hours=6)},
        ]
        ranked = self.stage.rank(weibos)

        # 第一名应该是高情感+高热度+刚发布的 3002
        assert ranked[0]['weibo_id'] == 3002
        assert ranked[0]['ranking_position'] == 1

        # 所有都有排名
        positions = [r['ranking_position'] for r in ranked]
        assert positions == [1, 2, 3]

        # 综合得分递减
        scores = [r['composite_score'] for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_popularity_class(self):
        """热度分级: high/medium/low"""
        now = datetime.now()
        weibos = [
            {'weibo_id': 4001, 'hybrid_score': 0.5, 'reposts_count': 100000,
             'comments_count': 50000, 'attitudes_count': 200000, 'created_at': now},
            {'weibo_id': 4002, 'hybrid_score': 0.5, 'reposts_count': 0,
             'comments_count': 0, 'attitudes_count': 1, 'created_at': now},
        ]
        ranked = self.stage.rank(weibos)

        high_item = next(r for r in ranked if r['weibo_id'] == 4001)
        low_item = next(r for r in ranked if r['weibo_id'] == 4002)
        assert high_item['popularity_class'] == 'high'
        assert low_item['popularity_class'] == 'low'


class TestEndToEnd:
    """端到端流程测试（不依赖MySQL）"""

    def test_full_flow(self):
        """模拟完整流程: 情感分析 → 双维度排序"""
        config = PipelineConfig()
        sentiment_stage = SentimentStage(config)
        ranking_stage = RankingStage(config)

        # 模拟从MySQL读取的未处理微博
        now = datetime.now()
        weibos = [
            {'weibo_id': 5001, 'content': '太开心了，今天收到好消息！加油！',
             'reposts_count': 200, 'comments_count': 100, 'attitudes_count': 500,
             'created_at': now},
            {'weibo_id': 5002, 'content': '真的太差了，失望透顶，垃圾服务',
             'reposts_count': 50, 'comments_count': 30, 'attitudes_count': 10,
             'created_at': now - timedelta(hours=6)},
            {'weibo_id': 5003, 'content': '今天去了一下超市',
             'reposts_count': 1, 'comments_count': 0, 'attitudes_count': 2,
             'created_at': now - timedelta(hours=24)},
        ]

        # Stage 1: 情感分析
        sentiment_results = sentiment_stage.analyze_batch(weibos)
        assert len(sentiment_results) == 3
        for r in sentiment_results:
            assert 'weibo_id' in r
            assert 'hybrid_score' in r
            assert 'analysis_method' in r

        # 合并情感结果到微博数据（模拟 get_unranked_weibos 的 JOIN 查询）
        weibo_map = {w['weibo_id']: w for w in weibos}
        combined = []
        for sr in sentiment_results:
            wid = sr['weibo_id']
            w = weibo_map[wid].copy()
            w['hybrid_score'] = sr['hybrid_score']
            w['sentiment_class'] = sr['sentiment_class']
            combined.append(w)

        # Stage 2: 双维度排序
        ranked = ranking_stage.rank(combined)
        assert len(ranked) == 3

        # 验证排序结果完整性
        for r in ranked:
            assert 'weibo_id' in r
            assert 'sentiment_score' in r
            assert 'popularity_score' in r
            assert 'time_decay' in r
            assert 'composite_score' in r
            assert 'ranking_position' in r
            assert r['algorithm_version'] == 'v2.0.0'

        # 第一条（高热度+正面情感+刚发布）应排名最高
        assert ranked[0]['weibo_id'] == 5001

        print("\n=== 端到端测试结果 ===")
        for r in ranked:
            print(f"  #{r['ranking_position']} weibo_id={r['weibo_id']} "
                  f"score={r['composite_score']:.4f} "
                  f"sentiment={r['sentiment_score']:.4f} "
                  f"heat={r['popularity_score']:.4f} "
                  f"decay={r['time_decay']:.4f} "
                  f"class={r['popularity_class']}")


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '--tb=short'])
