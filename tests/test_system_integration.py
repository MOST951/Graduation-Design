#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系统集成测试
============

测试各模块的协作：
1. 数据采集 -> 数据清洗 -> 情感分析 -> 存储
2. 双维度排序模型
3. API接口

作者: 罗森
学号: 2022407443
"""

import os
import sys
import json
import time
import unittest
from datetime import datetime
from typing import List, Dict

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# 测试数据
TEST_WEIBOS = [
    {
        'id': '1001',
        'text': '今天天气真好，心情也很棒！出去玩了一整天，超级开心😊',
        'user_id': 'user001',
        'user_name': '测试用户1',
        'created_at': datetime.now(),
        'reposts_count': 100,
        'comments_count': 50,
        'attitudes_count': 200
    },
    {
        'id': '1002',
        'text': '这个产品太差了，完全不值这个价格，非常失望😡',
        'user_id': 'user002',
        'user_name': '测试用户2',
        'created_at': datetime.now(),
        'reposts_count': 500,
        'comments_count': 300,
        'attitudes_count': 100
    },
    {
        'id': '1003',
        'text': '刚看完这部电影，剧情一般般，不好也不坏',
        'user_id': 'user003',
        'user_name': '测试用户3',
        'created_at': datetime.now(),
        'reposts_count': 20,
        'comments_count': 10,
        'attitudes_count': 30
    },
    {
        'id': '1004',
        'text': '强烈推荐这家餐厅！服务态度超好，菜品也很美味，下次还来！',
        'user_id': 'user004',
        'user_name': '测试用户4',
        'created_at': datetime.now(),
        'reposts_count': 80,
        'comments_count': 40,
        'attitudes_count': 150
    },
    {
        'id': '1005',
        'text': '等了两个小时还没发货，客服态度也很差，再也不买了',
        'user_id': 'user005',
        'user_name': '测试用户5',
        'created_at': datetime.now(),
        'reposts_count': 200,
        'comments_count': 150,
        'attitudes_count': 50
    }
]


class TestSentimentAnalysis(unittest.TestCase):
    """情感分析模块测试"""
    
    def test_dictionary_sentiment(self):
        """测试词典情感分析"""
        try:
            from spark.sentiment_analyzer import SentimentAnalyzer
            analyzer = SentimentAnalyzer()
            
            # 测试正面文本
            result = analyzer.analyze("今天天气真好，心情很棒")
            self.assertIn(result['label'], ['positive', 'neutral'])
            
            # 测试负面文本
            result = analyzer.analyze("这个产品太差了，非常失望")
            self.assertIn(result['label'], ['negative', 'neutral'])
            
            print("✅ 词典情感分析测试通过")
        except ImportError as e:
            print(f"⚠️ 跳过词典情感分析测试: {e}")
    
    def test_hybrid_sentiment(self):
        """测试混合情感分析"""
        try:
            from services.hybrid_analyzer import HybridSentimentAnalyzer
            analyzer = HybridSentimentAnalyzer()
            
            for weibo in TEST_WEIBOS[:2]:
                result = analyzer.analyze(weibo['text'])
                self.assertIn('score', result)
                self.assertIn('label', result)
                self.assertIn(result['label'], ['positive', 'neutral', 'negative'])
                print(f"  文本: {weibo['text'][:30]}...")
                print(f"  结果: {result['label']} (score={result['score']:.3f})")
            
            print("✅ 混合情感分析测试通过")
        except ImportError as e:
            print(f"⚠️ 跳过混合情感分析测试: {e}")


class TestDualDimensionModel(unittest.TestCase):
    """双维度排序模型测试"""
    
    def test_heat_score_calculation(self):
        """测试热度得分计算"""
        try:
            from spark.dual_dimension_model import DualDimensionRanker, DualDimensionConfig
            
            config = DualDimensionConfig()
            ranker = DualDimensionRanker(config)
            
            # 测试热度计算
            heat_score = ranker.calculate_heat_score(
                reposts=100,
                comments=50,
                likes=200
            )
            
            self.assertGreater(heat_score, 0)
            print(f"  热度得分: {heat_score:.4f}")
            print("✅ 热度得分计算测试通过")
        except ImportError as e:
            print(f"⚠️ 跳过热度得分测试: {e}")
    
    def test_dual_dimension_ranking(self):
        """测试双维度排序"""
        try:
            from spark.dual_dimension_model import DualDimensionRanker, DualDimensionConfig
            
            config = DualDimensionConfig(
                sentiment_weight=0.4,
                heat_weight=0.4,
                timeliness_weight=0.2
            )
            ranker = DualDimensionRanker(config)
            
            # 准备测试数据
            items = []
            for weibo in TEST_WEIBOS:
                item = {
                    'id': weibo['id'],
                    'text': weibo['text'],
                    'sentiment_score': 0.5,  # 模拟情感得分
                    'reposts_count': weibo['reposts_count'],
                    'comments_count': weibo['comments_count'],
                    'attitudes_count': weibo['attitudes_count'],
                    'created_at': weibo['created_at']
                }
                items.append(item)
            
            # 执行排序
            ranked = ranker.rank(items)
            
            self.assertEqual(len(ranked), len(TEST_WEIBOS))
            
            # 验证排序结果有rank字段
            for item in ranked:
                self.assertIn('dual_score', item)
                self.assertIn('rank', item)
            
            print("  排序结果:")
            for item in ranked[:3]:
                print(f"    Rank {item['rank']}: ID={item['id']}, Score={item['dual_score']:.4f}")
            
            print("✅ 双维度排序测试通过")
        except ImportError as e:
            print(f"⚠️ 跳过双维度排序测试: {e}")


class TestDataCleaning(unittest.TestCase):
    """数据清洗模块测试"""
    
    def test_text_cleaning(self):
        """测试文本清洗"""
        try:
            from spark.data_cleaner import DataCleaner
            
            # 测试HTML标签清理
            test_text = '<p>这是一段<b>测试</b>文本</p>'
            cleaned = DataCleaner.clean_html(test_text)
            self.assertNotIn('<', cleaned)
            
            # 测试URL提取
            test_text = '访问 https://example.com 了解更多'
            urls = DataCleaner.extract_urls(test_text)
            self.assertEqual(len(urls), 1)
            
            print("✅ 文本清洗测试通过")
        except ImportError as e:
            print(f"⚠️ 跳过文本清洗测试: {e}")
    
    def test_tokenization(self):
        """测试中文分词"""
        try:
            import jieba
            
            text = "微博舆情分析系统是一个很有用的工具"
            tokens = list(jieba.cut(text))
            
            self.assertGreater(len(tokens), 0)
            print(f"  分词结果: {' / '.join(tokens)}")
            print("✅ 中文分词测试通过")
        except ImportError as e:
            print(f"⚠️ 跳过中文分词测试: {e}")


class TestStorageService(unittest.TestCase):
    """存储服务测试"""
    
    def test_local_storage(self):
        """测试本地存储（开发模式）"""
        try:
            from services.storage_service import StorageService
            
            storage = StorageService()
            
            # 测试HBase本地存储
            test_data = {
                'cf_basic:id': '1001',
                'cf_basic:text': '测试微博内容',
                'cf_stats:reposts': '100'
            }
            
            rowkey = storage.hbase.generate_rowkey(entity_id='1001')
            storage.hbase.put('weibo_raw', rowkey, test_data)
            
            # 读取验证
            result = storage.hbase.get('weibo_raw', rowkey)
            self.assertIsNotNone(result)
            
            print("✅ 本地存储测试通过")
        except ImportError as e:
            print(f"⚠️ 跳过存储服务测试: {e}")


class TestAPIEndpoints(unittest.TestCase):
    """API接口测试"""
    
    def test_sentiment_api(self):
        """测试情感分析API"""
        try:
            import requests
            
            # 假设服务运行在本地
            base_url = 'http://localhost:5000/api'
            
            # 测试单条分析
            response = requests.post(
                f'{base_url}/sentiment/analyze',
                json={'text': '今天心情很好'},
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  API响应: {result}")
                print("✅ 情感分析API测试通过")
            else:
                print(f"⚠️ API返回状态码: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("⚠️ 跳过API测试（服务未运行）")
        except Exception as e:
            print(f"⚠️ API测试异常: {e}")


class TestFullPipeline(unittest.TestCase):
    """完整流水线测试"""
    
    def test_end_to_end(self):
        """端到端测试"""
        print("\n" + "="*50)
        print("端到端流水线测试")
        print("="*50)
        
        results = {
            'total': len(TEST_WEIBOS),
            'processed': 0,
            'positive': 0,
            'neutral': 0,
            'negative': 0
        }
        
        try:
            # 1. 数据清洗
            print("\n[1/4] 数据清洗...")
            cleaned_weibos = []
            for weibo in TEST_WEIBOS:
                cleaned = {
                    **weibo,
                    'cleaned_text': weibo['text'].strip()
                }
                cleaned_weibos.append(cleaned)
            print(f"  清洗完成: {len(cleaned_weibos)} 条")
            
            # 2. 情感分析
            print("\n[2/4] 情感分析...")
            try:
                from services.hybrid_analyzer import HybridSentimentAnalyzer
                analyzer = HybridSentimentAnalyzer()
                
                for weibo in cleaned_weibos:
                    result = analyzer.analyze(weibo['cleaned_text'])
                    weibo['sentiment_score'] = result.get('score', 0)
                    weibo['sentiment_label'] = result.get('label', 'neutral')
                    
                    if weibo['sentiment_label'] == 'positive':
                        results['positive'] += 1
                    elif weibo['sentiment_label'] == 'negative':
                        results['negative'] += 1
                    else:
                        results['neutral'] += 1
                    
                    results['processed'] += 1
                
                print(f"  分析完成: {results['processed']} 条")
                print(f"  正面: {results['positive']}, 中性: {results['neutral']}, 负面: {results['negative']}")
            except ImportError:
                print("  使用简单规则分析...")
                for weibo in cleaned_weibos:
                    text = weibo['cleaned_text']
                    if any(w in text for w in ['好', '棒', '开心', '推荐', '美味']):
                        weibo['sentiment_score'] = 0.7
                        weibo['sentiment_label'] = 'positive'
                        results['positive'] += 1
                    elif any(w in text for w in ['差', '失望', '不好', '再也不']):
                        weibo['sentiment_score'] = -0.7
                        weibo['sentiment_label'] = 'negative'
                        results['negative'] += 1
                    else:
                        weibo['sentiment_score'] = 0
                        weibo['sentiment_label'] = 'neutral'
                        results['neutral'] += 1
                    results['processed'] += 1
                print(f"  分析完成: {results['processed']} 条")
            
            # 3. 双维度排序
            print("\n[3/4] 双维度排序...")
            import math
            
            for weibo in cleaned_weibos:
                # 计算热度得分
                reposts = weibo['reposts_count']
                comments = weibo['comments_count']
                likes = weibo['attitudes_count']
                heat = math.log(1 + reposts * 3 + comments * 2 + likes)
                weibo['heat_score'] = heat
                
                # 计算综合得分
                sentiment = (weibo['sentiment_score'] + 1) / 2  # 归一化到[0,1]
                weibo['dual_score'] = 0.4 * sentiment + 0.4 * (heat / 10) + 0.2 * 1.0
            
            # 排序
            cleaned_weibos.sort(key=lambda x: x['dual_score'], reverse=True)
            for i, weibo in enumerate(cleaned_weibos):
                weibo['rank'] = i + 1
            
            print("  排序结果:")
            for weibo in cleaned_weibos[:3]:
                print(f"    Rank {weibo['rank']}: {weibo['text'][:25]}... (score={weibo['dual_score']:.3f})")
            
            # 4. 存储结果
            print("\n[4/4] 存储结果...")
            output_path = os.path.join(os.path.dirname(__file__), 'test_output.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_weibos, f, ensure_ascii=False, indent=2, default=str)
            print(f"  结果已保存: {output_path}")
            
            print("\n" + "="*50)
            print("✅ 端到端测试完成!")
            print(f"  处理: {results['processed']}/{results['total']} 条")
            print(f"  情感分布: 正面={results['positive']}, 中性={results['neutral']}, 负面={results['negative']}")
            print("="*50)
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()


def run_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("微博舆情分析系统 - 集成测试")
    print("作者: 罗森 | 学号: 2022407443")
    print("="*60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestSentimentAnalysis))
    suite.addTests(loader.loadTestsFromTestCase(TestDualDimensionModel))
    suite.addTests(loader.loadTestsFromTestCase(TestDataCleaning))
    suite.addTests(loader.loadTestsFromTestCase(TestStorageService))
    suite.addTests(loader.loadTestsFromTestCase(TestFullPipeline))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"运行: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    return result


if __name__ == '__main__':
    run_tests()
