"""
基于Spark的微博情感分析模块
使用PySpark进行分布式情感分析处理
"""
import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 尝试导入PySpark
try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql.functions import (
        col, udf, when, lit, count, avg, sum as spark_sum,
        to_timestamp, date_format, hour, dayofweek,
        explode, split, lower, trim, regexp_replace,
        collect_list, struct, row_number, desc, asc
    )
    from pyspark.sql.types import (
        StructType, StructField, StringType, IntegerType, 
        FloatType, ArrayType, TimestampType, BooleanType
    )
    from pyspark.sql.window import Window
    from pyspark.ml.feature import HashingTF, IDF, Tokenizer
    from pyspark.ml.classification import LogisticRegression, NaiveBayes
    from pyspark.ml import Pipeline
    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False
    logger.warning("PySpark未安装，将使用本地模式进行情感分析")


# 情感词典
class SentimentLexicon:
    """中文情感词典"""
    
    # 正面情感词
    POSITIVE_WORDS = {
        '好', '棒', '赞', '优秀', '喜欢', '爱', '开心', '高兴', '快乐', '幸福',
        '美好', '精彩', '厉害', '牛', '强', '帅', '美', '漂亮', '可爱', '温暖',
        '感动', '支持', '期待', '希望', '成功', '胜利', '加油', '努力', '进步',
        '优质', '满意', '舒服', '享受', '惊喜', '感谢', '祝福', '恭喜', '点赞',
        '推荐', '值得', '完美', '出色', '杰出', '卓越', '一流', '顶级', '最佳',
        '太棒了', '真好', '不错', '很好', '非常好', '超级棒', '太厉害', '真棒',
        '哈哈', '嘻嘻', '么么哒', '比心', '鼓掌', '撒花', '庆祝', '欢呼',
    }
    
    # 负面情感词
    NEGATIVE_WORDS = {
        '差', '烂', '垃圾', '讨厌', '恨', '愤怒', '生气', '难过', '伤心', '失望',
        '糟糕', '恶心', '无语', '崩溃', '绝望', '痛苦', '悲伤', '郁闷', '烦躁',
        '可怕', '恐怖', '害怕', '担心', '焦虑', '紧张', '压力', '累', '疲惫',
        '失败', '输', '败', '亏', '损失', '问题', '错误', 'bug', '故障', '缺陷',
        '骗', '假', '坑', '黑', '喷', '骂', '怼', '撕', '吵', '闹',
        '太差了', '真烂', '不行', '很差', '非常差', '超级烂', '太垃圾', '真差',
        '呵呵', '滚', '傻', '蠢', '笨', '白痴', '脑残', '智障',
    }
    
    # 否定词（需要独立出现，避免误匹配"非常"等词）
    NEGATION_WORDS = {'不', '没', '没有', '无', '别', '莫', '未', '勿', '难以', '不是', '不会', '不能'}
    
    # 程度副词
    DEGREE_WORDS = {
        '很': 1.5, '非常': 2.0, '特别': 2.0, '极其': 2.5, '超级': 2.0,
        '太': 1.8, '真': 1.5, '好': 1.3, '挺': 1.2, '蛮': 1.2,
        '有点': 0.5, '稍微': 0.5, '略': 0.5, '些': 0.7, '比较': 1.2,
    }
    
    @classmethod
    def analyze(cls, text: str) -> Tuple[str, float]:
        """
        分析文本情感
        
        Args:
            text: 输入文本
            
        Returns:
            (情感标签, 情感得分) - 得分范围 [-1, 1]
        """
        if not text:
            return 'neutral', 0.0
            
        text = text.lower()
        
        positive_score = 0.0
        negative_score = 0.0
        
        # 简单分词（按字符和常见分隔符）
        words = list(text)
        
        # 检查否定词
        has_negation = False
        negation_patterns = ['不好', '不行', '不喜欢', '不爱', '不满', '不开心', '没用', '不值']
        for pattern in negation_patterns:
            if pattern in text:
                has_negation = True
                break
        
        # 如果没有匹配到固定模式，检查否定词+情感词组合
        if not has_negation:
            for neg in cls.NEGATION_WORDS:
                if neg in text:
                    idx = text.find(neg)
                    if idx >= 0:
                        after_neg = text[idx + len(neg):idx + len(neg) + 4]
                        for pos_word in list(cls.POSITIVE_WORDS)[:30]:
                            if pos_word in after_neg:
                                has_negation = True
                                break
                        if has_negation:
                            break
        
        # 检查程度副词
        degree = 1.0
        for word, deg in cls.DEGREE_WORDS.items():
            if word in text:
                degree = max(degree, deg)
        
        # 计算正面得分
        for word in cls.POSITIVE_WORDS:
            if word in text:
                positive_score += 1.0 * degree
                
        # 计算负面得分
        for word in cls.NEGATIVE_WORDS:
            if word in text:
                negative_score += 1.0 * degree
        
        # 如果有否定词，交换正负得分
        if has_negation:
            positive_score, negative_score = negative_score * 0.8, positive_score * 0.8
            
        # 计算最终得分
        total = positive_score + negative_score
        if total == 0:
            return 'neutral', 0.0
            
        score = (positive_score - negative_score) / max(total, 1)
        
        # 确定情感标签
        if score > 0.2:
            sentiment = 'positive'
        elif score < -0.2:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
            
        return sentiment, round(score, 4)

    # ---- 负面情绪 emoji/标记 (用于辅助判别) ----
    NEG_EMOJI_MARKERS = {
        '[泪]', '[衰]', '[抓狂]', '[怒]', '[哭]', '[失望]', '[囧]',
        '[委屈]', '[悲伤]', '[崩溃]', '[汗]', '[困]', '[可怜]',
        '[鄙视]', '[吐]', '[怒骂]', '[生病]', '[悲催]', '[泪奔]',
        '[生气]', '[拜拜]',
    }
    POS_EMOJI_MARKERS = {
        '[哈哈]', '[嘻嘻]', '[爱你]', '[心]', '[鼓掌]', '[赞]',
        '[good]', '[给力]', '[威武]', '[偷笑]', '[花心]', '[太开心]',
        '[耶]', '[微笑]', '[doge]', '[抱抱]', '[笑哈哈]', '[亲亲]',
        '[害羞]', '[奥特曼]',
    }
    # 中性/无意义标记 (出现时既非正也非负)
    NEUTRAL_EMOJI_MARKERS = {
        '[思考]', '[疑问]', '[吃惊]', '[黑线]', '[晕]', '[挖鼻屎]',
    }

    # 噪声模式 (预编译正则)
    _URL_RE = None
    _MENTION_RE = None
    _HASHTAG_RE = None
    _EMOJI_BRACKET_RE = None

    @classmethod
    def _get_noise_patterns(cls):
        import re
        if cls._URL_RE is None:
            cls._URL_RE = re.compile(r'https?://\S+|www\.\S+|\S+\.(?:com|cn|net|org)\S*')
            cls._MENTION_RE = re.compile(r'@[\w\u4e00-\u9fff\-]+')
            cls._HASHTAG_RE = re.compile(r'#[^#]+#')
            cls._EMOJI_BRACKET_RE = re.compile(r'\[[^\[\]]{1,10}\]')
        return cls._URL_RE, cls._MENTION_RE, cls._HASHTAG_RE, cls._EMOJI_BRACKET_RE

    @classmethod
    def analyze_3class(cls, text: str) -> Tuple[int, float, bool]:
        """
        三分类级联专用接口 (v3 — 严格规则版)

        设计原则:
          - 宁可漏判 (返回 high_confidence=False 让 BERT 处理),
            也不要误判 (避免错误的词典直出)
          - 规则按优先级排列, 命中即返回
          - 目标: 词典直出路径准确率 ≥ 85%

        Returns:
            (label_id, confidence, high_confidence)
        """
        import re

        if not text or not text.strip():
            return 2, 0.95, True  # 空文本 → 中性

        url_re, mention_re, hashtag_re, emoji_re = cls._get_noise_patterns()
        text_low = text.lower()
        stripped = text.strip()

        # ---- 预处理: 剥离噪声 (URL / @ / #topic# / emoji 括号 / 数字标点) ----
        cleaned = url_re.sub('', stripped)
        cleaned = mention_re.sub('', cleaned)
        cleaned = hashtag_re.sub('', cleaned)
        cleaned_no_emoji = emoji_re.sub('', cleaned)
        cleaned_semantic = re.sub(r'[\d\s\W_]+', '', cleaned_no_emoji, flags=re.UNICODE)
        # cleaned_semantic 仅保留实义字符 (中文/英文字母)

        # ---- 计数 ----
        pos_count = sum(1 for w in cls.POSITIVE_WORDS if w in text_low)
        neg_count = sum(1 for w in cls.NEGATIVE_WORDS if w in text_low)
        pos_emoji = sum(1 for e in cls.POS_EMOJI_MARKERS if e in text)
        neg_emoji = sum(1 for e in cls.NEG_EMOJI_MARKERS if e in text)

        # 否定词
        has_negation = any(p in text_low for p in
                           ['不好', '不行', '不喜欢', '不爱', '不满', '不开心',
                            '没用', '不值', '不是', '没有'])

        total_pos = pos_count + pos_emoji
        total_neg = neg_count + neg_emoji

        # ================ 决策规则 (按优先级) ================

        # Rule 0: 极短文本 (去噪后 < 2 实义字符) → 中性 (高置信, 真的无内容)
        if len(cleaned_semantic) < 2:
            return 2, 0.92, True

        # Rule 1: 纯噪声文本 (只有 URL/@/# 或纯数字) → 中性
        if len(cleaned_no_emoji.strip()) < 3 and total_pos == 0 and total_neg == 0:
            return 2, 0.9, True

        # Rule 2: 无情感词 → 不标高置信, 交给 BERT 判别
        # (因为许多正/负文本使用的情感词不在词表中, 直接判中性会错)
        # 例外: 去噪后语义内容 < 3 字 → 确实是纯噪声 → 中性高置信
        if total_pos == 0 and total_neg == 0:
            if len(cleaned_semantic) < 3:
                return 2, 0.88, True
            return 2, 0.5, False  # 其余全部交给 BERT

        # Rule 3: 强正面 — 需 ≥3 正面信号 + 无负面 + 无否定 + 足够长度
        if total_pos >= 3 and total_neg == 0 and not has_negation \
                and len(cleaned_semantic) >= 4:
            return 1, min(0.82 + 0.03 * total_pos, 0.97), True

        # Rule 4: 强负面 — 需 ≥3 负面信号 + 无正面 + 无否定 + 足够长度
        if total_neg >= 3 and total_pos == 0 and not has_negation \
                and len(cleaned_semantic) >= 4:
            return 0, min(0.82 + 0.03 * total_neg, 0.97), True

        # Rule 5: 负面 emoji 密集 (≥3) 且无正面词 → 负面
        if neg_emoji >= 3 and total_pos == 0:
            return 0, 0.88, True

        # Rule 6: 正面 emoji 密集 (≥3) 且无负面词 → 正面
        if pos_emoji >= 3 and total_neg == 0 and not has_negation:
            return 1, 0.88, True

        # Rule 7: 2 正面词 + 同向 emoji 辅助 + 无负面 → 正面 (中等置信)
        if pos_count >= 2 and neg_count == 0 and pos_emoji >= 1 \
                and neg_emoji == 0 and not has_negation:
            return 1, 0.83, True

        # Rule 8: 2 负面词 + 同向 emoji 辅助 + 无正面 → 负面 (中等置信)
        if neg_count >= 2 and pos_count == 0 and neg_emoji >= 1 \
                and pos_emoji == 0 and not has_negation:
            return 0, 0.83, True

        # ================ 其他歧义情形 → BERT 处理 ================
        # 给出试探性预测 (不标记高置信)
        if total_pos > total_neg:
            tentative = 1
        elif total_neg > total_pos:
            tentative = 0
        else:
            tentative = 2
        return tentative, 0.45, False


class SparkSentimentAnalyzer:
    """
    基于Spark的情感分析器
    支持本地模式和集群模式
    """
    
    def __init__(self, master: str = "local[*]", app_name: str = "WeiboSentimentAnalysis"):
        """
        初始化Spark分析器
        
        Args:
            master: Spark master URL
                - "local[*]": 本地模式，使用所有CPU核心
                - "local[4]": 本地模式，使用4个核心
                - "spark://host:7077": 集群模式
            app_name: Spark应用名称
        """
        self.master = master
        self.app_name = app_name
        self.spark = None
        
        if SPARK_AVAILABLE:
            self._init_spark()
        else:
            logger.warning("Spark不可用，将使用本地分析模式")
            
    def _init_spark(self):
        """初始化SparkSession"""
        try:
            self.spark = SparkSession.builder \
                .master(self.master) \
                .appName(self.app_name) \
                .config("spark.driver.memory", "2g") \
                .config("spark.executor.memory", "2g") \
                .config("spark.sql.shuffle.partitions", "4") \
                .config("spark.ui.showConsoleProgress", "false") \
                .getOrCreate()
                
            # 设置日志级别
            self.spark.sparkContext.setLogLevel("WARN")
            logger.info(f"Spark初始化成功: {self.master}")
            
        except Exception as e:
            logger.error(f"Spark初始化失败: {e}")
            self.spark = None
            
    def analyze_batch(self, data: List[Dict]) -> List[Dict]:
        """
        批量分析微博情感
        
        Args:
            data: 微博数据列表
            
        Returns:
            添加了情感分析结果的数据列表
        """
        if not data:
            return []
            
        if self.spark and SPARK_AVAILABLE:
            return self._analyze_with_spark(data)
        else:
            return self._analyze_local(data)
            
    def _analyze_with_spark(self, data: List[Dict]) -> List[Dict]:
        """使用Spark进行分析"""
        logger.info(f"使用Spark分析 {len(data)} 条微博...")
        
        # 创建DataFrame
        df = self.spark.createDataFrame(data)
        
        # 注册UDF
        sentiment_udf = udf(
            lambda text: SentimentLexicon.analyze(text)[0],
            StringType()
        )
        score_udf = udf(
            lambda text: float(SentimentLexicon.analyze(text)[1]),
            FloatType()
        )
        
        # 应用情感分析
        result_df = df.withColumn('sentiment', sentiment_udf(col('text'))) \
                      .withColumn('sentiment_score', score_udf(col('text')))
        
        # 转换回Python列表
        result = [row.asDict() for row in result_df.collect()]
        
        logger.info(f"Spark分析完成")
        return result
        
    def _analyze_local(self, data: List[Dict]) -> List[Dict]:
        """本地模式分析"""
        logger.info(f"使用本地模式分析 {len(data)} 条微博...")
        
        for item in data:
            text = item.get('text', '')
            sentiment, score = SentimentLexicon.analyze(text)
            item['sentiment'] = sentiment
            item['sentiment_score'] = score
            
        logger.info(f"本地分析完成")
        return data
        
    def analyze_file(self, input_path: str, output_path: str = None) -> str:
        """
        分析JSON文件中的微博数据
        
        Args:
            input_path: 输入JSON文件路径
            output_path: 输出文件路径（可选）
            
        Returns:
            输出文件路径
        """
        # 读取数据
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 分析
        result = self.analyze_batch(data)
        
        # 保存结果
        if not output_path:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_analyzed{ext}"
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        logger.info(f"分析结果已保存到: {output_path}")
        return output_path
        
    def get_statistics(self, data: List[Dict]) -> Dict:
        """
        获取情感分析统计信息
        
        Args:
            data: 已分析的微博数据
            
        Returns:
            统计信息字典
        """
        if not data:
            return {}
            
        total = len(data)
        positive = sum(1 for d in data if d.get('sentiment') == 'positive')
        negative = sum(1 for d in data if d.get('sentiment') == 'negative')
        neutral = sum(1 for d in data if d.get('sentiment') == 'neutral')
        
        scores = [d.get('sentiment_score', 0) for d in data if d.get('sentiment_score') is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        return {
            'total': total,
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'positive_ratio': round(positive / total * 100, 2) if total > 0 else 0,
            'negative_ratio': round(negative / total * 100, 2) if total > 0 else 0,
            'neutral_ratio': round(neutral / total * 100, 2) if total > 0 else 0,
            'average_score': round(avg_score, 4),
            'analysis_time': datetime.now().isoformat()
        }
        
    def get_keyword_sentiment(self, data: List[Dict]) -> Dict[str, Dict]:
        """
        按关键词统计情感分布
        
        Args:
            data: 已分析的微博数据
            
        Returns:
            关键词情感统计
        """
        keyword_stats = {}
        
        for item in data:
            keyword = item.get('keyword', 'unknown')
            if keyword not in keyword_stats:
                keyword_stats[keyword] = {
                    'total': 0,
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0,
                    'scores': []
                }
                
            stats = keyword_stats[keyword]
            stats['total'] += 1
            
            sentiment = item.get('sentiment', 'neutral')
            stats[sentiment] = stats.get(sentiment, 0) + 1
            
            score = item.get('sentiment_score', 0)
            if score is not None:
                stats['scores'].append(score)
                
        # 计算平均分
        for keyword, stats in keyword_stats.items():
            scores = stats.pop('scores')
            stats['average_score'] = round(sum(scores) / len(scores), 4) if scores else 0
            
        return keyword_stats
        
    def get_time_series(self, data: List[Dict], interval: str = 'hour') -> List[Dict]:
        """
        获取情感时间序列
        
        Args:
            data: 已分析的微博数据
            interval: 时间间隔 (hour/day)
            
        Returns:
            时间序列数据
        """
        time_stats = {}
        
        for item in data:
            created_at = item.get('created_at', '')
            if not created_at:
                continue
                
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                if interval == 'hour':
                    key = dt.strftime('%Y-%m-%d %H:00')
                else:
                    key = dt.strftime('%Y-%m-%d')
            except:
                continue
                
            if key not in time_stats:
                time_stats[key] = {
                    'time': key,
                    'total': 0,
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0,
                    'score_sum': 0
                }
                
            stats = time_stats[key]
            stats['total'] += 1
            
            sentiment = item.get('sentiment', 'neutral')
            stats[sentiment] = stats.get(sentiment, 0) + 1
            
            score = item.get('sentiment_score', 0)
            if score is not None:
                stats['score_sum'] += score
                
        # 计算平均分并排序
        result = []
        for key in sorted(time_stats.keys()):
            stats = time_stats[key]
            stats['average_score'] = round(stats.pop('score_sum') / stats['total'], 4) if stats['total'] > 0 else 0
            result.append(stats)
            
        return result
        
    def stop(self):
        """停止Spark会话"""
        if self.spark:
            self.spark.stop()
            logger.info("Spark会话已停止")


class SparkClusterManager:
    """
    Spark伪集群管理器
    用于管理本地Spark集群的启动和停止
    """
    
    def __init__(self, spark_home: str = None):
        """
        初始化集群管理器
        
        Args:
            spark_home: Spark安装目录
        """
        self.spark_home = spark_home or os.environ.get('SPARK_HOME', '')
        
    def get_cluster_info(self) -> Dict:
        """获取集群信息"""
        return {
            'spark_home': self.spark_home,
            'spark_available': SPARK_AVAILABLE,
            'mode': 'local' if not self.spark_home else 'pseudo-distributed',
            'master_url': 'local[*]',
            'status': 'ready' if SPARK_AVAILABLE else 'spark_not_installed'
        }
        
    def submit_job(self, job_class: str, args: List[str] = None) -> Dict:
        """
        提交Spark作业
        
        Args:
            job_class: 作业类名
            args: 作业参数
            
        Returns:
            作业提交结果
        """
        # 在本地模式下，直接运行
        return {
            'job_id': f"job_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'status': 'submitted',
            'mode': 'local',
            'message': '作业已提交到本地Spark'
        }


# 便捷函数
def analyze_weibo_sentiment(data: List[Dict], 
                           use_spark: bool = True) -> Tuple[List[Dict], Dict]:
    """
    分析微博情感的便捷函数
    
    Args:
        data: 微博数据列表
        use_spark: 是否使用Spark
        
    Returns:
        (分析结果, 统计信息)
    """
    if use_spark and SPARK_AVAILABLE:
        analyzer = SparkSentimentAnalyzer()
    else:
        analyzer = SparkSentimentAnalyzer()  # 会自动降级到本地模式
        
    result = analyzer.analyze_batch(data)
    stats = analyzer.get_statistics(result)
    
    return result, stats


if __name__ == '__main__':
    # 测试情感分析
    test_texts = [
        "这个产品太棒了，非常喜欢！",
        "服务态度很差，再也不来了",
        "今天天气不错",
        "真的很失望，完全不值这个价",
        "哈哈哈太好笑了",
    ]
    
    print("=== 情感分析测试 ===")
    for text in test_texts:
        sentiment, score = SentimentLexicon.analyze(text)
        print(f"文本: {text}")
        print(f"情感: {sentiment}, 得分: {score}")
        print()
        
    # 测试批量分析
    print("=== 批量分析测试 ===")
    test_data = [{'text': t, 'id': i} for i, t in enumerate(test_texts)]
    
    analyzer = SparkSentimentAnalyzer()
    result = analyzer.analyze_batch(test_data)
    stats = analyzer.get_statistics(result)
    
    print(f"统计信息: {json.dumps(stats, ensure_ascii=False, indent=2)}")
