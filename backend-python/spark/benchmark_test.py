"""
Spark性能基准测试脚本

测试内容：
1. 数据清洗性能
2. 特征提取性能
3. 情感分析性能
4. 不同配置对比
5. 内存使用监控

使用方法：
    python benchmark_test.py --records 10000 --iterations 3

作者：毕业设计
"""

import argparse
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from pyspark.sql import SparkSession
    from spark.spark_optimizer import (
        SparkOptimizationConfig,
        OptimizedSparkSession,
        OptimizedDataProcessor,
        PerformanceTester,
        PartitionOptimizer,
        CacheManager,
        get_spark_ui_metrics,
    )
    SPARK_AVAILABLE = True
except ImportError as e:
    print(f"导入失败: {e}")
    SPARK_AVAILABLE = False


class BenchmarkSuite:
    """
    性能基准测试套件
    """
    
    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.results: List[Dict] = []
    
    def run_test(self, name: str, func, *args, **kwargs) -> Dict:
        """运行单个测试"""
        print(f"\n{'='*50}")
        print(f"测试: {name}")
        print(f"{'='*50}")
        
        # 预热
        print("预热中...")
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"预热失败: {e}")
        
        # 正式测试
        times = []
        for i in range(3):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                times.append(elapsed)
                print(f"  迭代 {i+1}: {elapsed:.3f}秒")
            except Exception as e:
                print(f"  迭代 {i+1} 失败: {e}")
        
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
        else:
            avg_time = min_time = max_time = 0
        
        result = {
            "name": name,
            "avg_time": round(avg_time, 3),
            "min_time": round(min_time, 3),
            "max_time": round(max_time, 3),
            "iterations": len(times),
        }
        
        self.results.append(result)
        print(f"平均耗时: {avg_time:.3f}秒")
        
        return result
    
    def generate_test_data(self, num_records: int):
        """生成测试数据"""
        import random
        
        data = []
        for i in range(num_records):
            text = f"这是第{i}条测试微博，" + "测试内容" * random.randint(5, 20)
            if i % 3 == 0:
                text += "非常好！强烈推荐！"
            elif i % 3 == 1:
                text += "太差了！不推荐！"
            else:
                text += "一般般，还行吧。"
            
            data.append({
                "id": str(i),
                "text": text,
                "user_id": f"user_{i % 1000}",
                "reposts_count": random.randint(0, 10000),
                "comments_count": random.randint(0, 5000),
                "attitudes_count": random.randint(0, 20000),
                "followers_count": random.randint(100, 1000000),
                "created_at": datetime.now().isoformat(),
            })
        
        return self.spark.createDataFrame(data)
    
    def test_data_cleaning(self, df, processor):
        """测试数据清洗"""
        cleaned = processor.clean_data(df)
        return cleaned.count()
    
    def test_feature_extraction(self, df, processor):
        """测试特征提取"""
        featured = processor.extract_features(df)
        return featured.count()
    
    def test_sentiment_analysis(self, df, processor):
        """测试情感分析"""
        analyzed = processor.analyze_sentiment(df)
        return analyzed.count()
    
    def test_full_pipeline(self, df, processor):
        """测试完整流水线"""
        result = processor.process_pipeline(df, cache_intermediate=False)
        return result.count()
    
    def test_with_cache(self, df, processor):
        """测试带缓存的流水线"""
        result = processor.process_pipeline(df, cache_intermediate=True)
        count = result.count()
        processor.cache_manager.unpersist_all()
        return count
    
    def test_partition_optimization(self, df, num_partitions: int):
        """测试分区优化"""
        # 重分区
        repartitioned = df.repartition(num_partitions)
        return repartitioned.count()
    
    def run_all_tests(self, num_records: int = 10000) -> Dict:
        """运行所有测试"""
        print("\n" + "="*70)
        print("Spark性能基准测试")
        print(f"数据量: {num_records} 条")
        print("="*70)
        
        # 生成测试数据
        print("\n生成测试数据...")
        start = time.time()
        df = self.generate_test_data(num_records)
        df = df.cache()
        df.count()  # 触发缓存
        data_gen_time = time.time() - start
        print(f"数据生成耗时: {data_gen_time:.3f}秒")
        
        # 创建处理器
        processor = OptimizedDataProcessor(self.spark)
        processor.setup_broadcast_variables()
        
        # 先清洗数据用于后续测试
        cleaned_df = processor.clean_data(df)
        cleaned_df = cleaned_df.cache()
        cleaned_df.count()
        
        featured_df = processor.extract_features(cleaned_df)
        featured_df = featured_df.cache()
        featured_df.count()
        
        # 运行测试
        self.run_test("数据清洗", self.test_data_cleaning, df, processor)
        self.run_test("特征提取", self.test_feature_extraction, cleaned_df, processor)
        self.run_test("情感分析", self.test_sentiment_analysis, featured_df, processor)
        self.run_test("完整流水线(无缓存)", self.test_full_pipeline, df, processor)
        self.run_test("完整流水线(有缓存)", self.test_with_cache, df, processor)
        
        # 分区测试
        for partitions in [4, 8, 16, 32]:
            self.run_test(f"分区优化({partitions}分区)", 
                         self.test_partition_optimization, df, partitions)
        
        # 清理
        df.unpersist()
        cleaned_df.unpersist()
        featured_df.unpersist()
        processor.cleanup()
        
        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "num_records": num_records,
            "data_generation_time": round(data_gen_time, 3),
            "tests": self.results,
            "summary": self._generate_summary(),
        }
        
        return report
    
    def _generate_summary(self) -> Dict:
        """生成测试摘要"""
        if not self.results:
            return {}
        
        total_time = sum(r["avg_time"] for r in self.results)
        
        return {
            "total_tests": len(self.results),
            "total_time": round(total_time, 3),
            "fastest_test": min(self.results, key=lambda x: x["avg_time"])["name"],
            "slowest_test": max(self.results, key=lambda x: x["avg_time"])["name"],
        }


def compare_configurations(spark: SparkSession, num_records: int = 5000):
    """
    对比不同配置的性能
    """
    print("\n" + "="*70)
    print("配置对比测试")
    print("="*70)
    
    configs = [
        ("默认配置", SparkOptimizationConfig()),
        ("高内存配置", SparkOptimizationConfig(
            driver_memory="4g",
            memory_fraction=0.8,
        )),
        ("多分区配置", SparkOptimizationConfig(
            shuffle_partitions=50,
            default_parallelism=16,
        )),
        ("AQE关闭", SparkOptimizationConfig(
            adaptive_enabled=False,
        )),
    ]
    
    results = []
    
    for name, config in configs:
        print(f"\n测试配置: {name}")
        print("-" * 40)
        
        # 应用配置
        for key, value in config.to_spark_conf().items():
            try:
                spark.conf.set(key, value)
            except:
                pass
        
        # 运行测试
        tester = PerformanceTester(spark)
        result = tester.run_benchmark(num_records)
        result["config_name"] = name
        results.append(result)
        
        print(f"总耗时: {result['total_time_seconds']}秒")
        print(f"吞吐量: {result['total_throughput']} 条/秒")
    
    return results


def print_report(report: Dict):
    """打印测试报告"""
    print("\n" + "="*70)
    print("性能测试报告")
    print("="*70)
    print(f"测试时间: {report['timestamp']}")
    print(f"数据量: {report['num_records']} 条")
    print(f"数据生成耗时: {report['data_generation_time']}秒")
    
    print("\n测试结果:")
    print("-" * 70)
    print(f"{'测试名称':<30} {'平均耗时':<12} {'最小耗时':<12} {'最大耗时':<12}")
    print("-" * 70)
    
    for test in report['tests']:
        print(f"{test['name']:<30} {test['avg_time']:<12.3f} "
              f"{test['min_time']:<12.3f} {test['max_time']:<12.3f}")
    
    print("-" * 70)
    
    if 'summary' in report:
        summary = report['summary']
        print(f"\n摘要:")
        print(f"  总测试数: {summary.get('total_tests', 0)}")
        print(f"  总耗时: {summary.get('total_time', 0)}秒")
        print(f"  最快测试: {summary.get('fastest_test', 'N/A')}")
        print(f"  最慢测试: {summary.get('slowest_test', 'N/A')}")


def main():
    parser = argparse.ArgumentParser(description='Spark性能基准测试')
    parser.add_argument('--records', type=int, default=10000, help='测试数据量')
    parser.add_argument('--iterations', type=int, default=3, help='测试迭代次数')
    parser.add_argument('--compare', action='store_true', help='运行配置对比测试')
    parser.add_argument('--output', type=str, default='benchmark_results.json', help='输出文件')
    
    args = parser.parse_args()
    
    if not SPARK_AVAILABLE:
        print("错误: PySpark未安装")
        sys.exit(1)
    
    # 创建SparkSession
    config = SparkOptimizationConfig(
        app_name="BenchmarkTest",
        driver_memory="4g",
        shuffle_partitions=50,
    )
    
    session_manager = OptimizedSparkSession()
    spark = session_manager.get_or_create(config)
    
    try:
        # 运行基准测试
        suite = BenchmarkSuite(spark)
        report = suite.run_all_tests(args.records)
        
        # 打印报告
        print_report(report)
        
        # 配置对比测试
        if args.compare:
            compare_results = compare_configurations(spark, args.records // 2)
            report["config_comparison"] = compare_results
        
        # 获取Spark UI指标
        ui_metrics = get_spark_ui_metrics(spark)
        report["spark_ui_metrics"] = ui_metrics
        
        # 保存结果
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存到: {args.output}")
        
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
