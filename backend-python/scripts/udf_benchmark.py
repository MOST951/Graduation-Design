"""
UDF 性能对比基准测试
对比三种实现方式：
  A) 普通 Python UDF（原始方案）
  B) Pandas UDF（向量化 UDF，使用 Apache Arrow）
  C) Spark SQL 原生函数（仅数据清洗阶段）

测试阶段：数据清洗、分词、情感分析
数据量：10,000 条
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

# Java 17+ : 必须在 JVM 启动之前设置，否则 Arrow 的 DirectByteBuffer 不可用
os.environ['_JAVA_OPTIONS'] = ' '.join([
    '--add-opens=java.base/java.lang=ALL-UNNAMED',
    '--add-opens=java.base/java.lang.invoke=ALL-UNNAMED',
    '--add-opens=java.base/java.lang.reflect=ALL-UNNAMED',
    '--add-opens=java.base/java.io=ALL-UNNAMED',
    '--add-opens=java.base/java.net=ALL-UNNAMED',
    '--add-opens=java.base/java.nio=ALL-UNNAMED',
    '--add-opens=java.base/java.util=ALL-UNNAMED',
    '--add-opens=java.base/java.util.concurrent=ALL-UNNAMED',
    '--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED',
    '--add-opens=java.base/sun.nio.ch=ALL-UNNAMED',
    '--add-opens=java.base/sun.nio.cs=ALL-UNNAMED',
    '--add-opens=java.base/sun.security.action=ALL-UNNAMED',
    '--add-opens=java.base/sun.util.calendar=ALL-UNNAMED',
    '--add-opens=java.base/jdk.internal.misc=ALL-UNNAMED',
    '--add-opens=java.security.jgss/sun.security.krb5=ALL-UNNAMED',
    '--add-opens=jdk.unsupported/sun.misc=ALL-UNNAMED',
])

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, FloatType,
    ArrayType
)

# ── 常量 ──────────────────────────────────────────────────────
DATA_PATH = ROOT / 'data' / 'weibo_senti_100k.csv'
OUT_PATH = ROOT / 'scripts' / 'udf_benchmark_results.json'

EMOJI_MAP = {
    '[笑cry]': '笑哭', '[哈哈]': '大笑', '[嘻嘻]': '嘻嘻笑',
    '[偷笑]': '偷笑', '[太开心]': '非常开心', '[开心]': '开心',
    '[赞]': '点赞', '[good]': '点赞', '[鼓掌]': '鼓掌',
    '[心]': '喜爱', '[爱你]': '爱你', '[给力]': '给力',
    '[怒]': '愤怒', '[生气]': '生气', '[悲伤]': '悲伤',
    '[泪]': '流泪', '[失望]': '失望', '[委屈]': '委屈',
    '[可怜]': '可怜', '[黑线]': '无语', '[汗]': '尴尬',
    '[思考]': '思考', '[疑问]': '疑问', '[吃惊]': '吃惊',
    '[doge]': '滑稽', '[允悲]': '苦笑', '[微笑]': '微笑',
    '[摊手]': '无奈', '[加油]': '加油', '[吃瓜]': '吃瓜围观',
    '[裂开]': '裂开崩溃', '[酸]': '酸了羡慕',
}

T2S_MAP = {
    '國': '国', '東': '东', '車': '车', '學': '学', '開': '开',
    '長': '长', '門': '门', '時': '时', '萬': '万', '電': '电',
    '書': '书', '見': '见', '飛': '飞', '機': '机', '數': '数',
    '點': '点', '問': '问', '頭': '头', '風': '风', '動': '动',
    '對': '对', '說': '说', '話': '话', '買': '买', '賣': '卖',
    '寫': '写', '讓': '让', '認': '认', '識': '识', '義': '义',
    '經': '经', '過': '过', '從': '从', '進': '进', '遠': '远',
    '運': '运', '關': '关', '連': '连', '邊': '边', '還': '还',
    '這': '这', '裡': '里', '後': '后', '樂': '乐', '覺': '觉',
    '發': '发', '現': '现', '報': '报', '廣': '广', '熱': '热',
    '愛': '爱', '個': '个', '優': '优', '網': '网', '傳': '传',
    '體': '体', '統': '统', '雙': '双', '離': '离', '難': '难',
}

STOP_WORDS = set([
    '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
    '自己', '这', '那', '什么', '他', '她', '它', '们', '这个', '那个', '哪', '为',
    '吗', '呢', '吧', '啊', '哦', '嗯', '呀', '哈', '嘿', '喂', '哎', '唉',
])


# ═══════════════════════════════════════════════════════════════
# 核心清洗逻辑（单条文本，Python UDF 和 Pandas UDF 共用）
# ═══════════════════════════════════════════════════════════════

def _clean_one(text: str) -> str:
    """清洗单条文本（纯 Python 逻辑）"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'@[\w\u4e00-\u9fff]+', '', text)
    text = re.sub(r'#([^#]+)#', r'\1', text)

    def _replace_emoji(m):
        return EMOJI_MAP.get(m.group(0), m.group(0))
    text = re.sub(r'\[[\w\u4e00-\u9fff]+\]', _replace_emoji, text)
    text = ''.join(T2S_MAP.get(c, c) for c in text)

    chars = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:
            chars.append(' ')
        elif 0xFF01 <= code <= 0xFF5E:
            chars.append(chr(code - 0xFEE0))
        else:
            chars.append(ch)
    text = ''.join(chars)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ═══════════════════════════════════════════════════════════════
# 方案 A：普通 Python UDF
# ═══════════════════════════════════════════════════════════════

def make_clean_udf_regular():
    return F.udf(_clean_one, StringType())


def make_tokenize_udf_regular():
    import jieba
    stop = STOP_WORDS

    def tokenize(text: str) -> List[str]:
        if not text:
            return []
        words = jieba.lcut(text)
        return [w for w in words if len(w) > 1 and w not in stop]

    return F.udf(tokenize, ArrayType(StringType()))


def make_sentiment_udf_regular():
    from spark.sentiment_analyzer import SentimentLexicon

    def analyze(text: str):
        if not text:
            return {"sentiment": "neutral", "score": 0.0}
        sentiment, score = SentimentLexicon.analyze(text)
        return {"sentiment": sentiment, "score": float(score)}

    schema = StructType([
        StructField("sentiment", StringType(), True),
        StructField("score", FloatType(), True)
    ])
    return F.udf(analyze, schema)


# ═══════════════════════════════════════════════════════════════
# 方案 B：Pandas UDF（向量化 UDF）
# ═══════════════════════════════════════════════════════════════

def make_clean_pandas_udf():
    from pyspark.sql.functions import pandas_udf

    @pandas_udf(StringType())
    def clean_pandas(series: pd.Series) -> pd.Series:
        return series.fillna('').apply(_clean_one)

    return clean_pandas


def make_tokenize_pandas_udf():
    from pyspark.sql.functions import pandas_udf

    @pandas_udf(ArrayType(StringType()))
    def tokenize_pandas(series: pd.Series) -> pd.Series:
        import jieba
        stop = STOP_WORDS

        def _tok(text):
            if not text:
                return []
            words = jieba.lcut(text)
            return [w for w in words if len(w) > 1 and w not in stop]

        return series.apply(_tok)

    return tokenize_pandas


def make_sentiment_pandas_udf():
    from pyspark.sql.functions import pandas_udf

    @pandas_udf(StringType())
    def sentiment_label_pandas(series: pd.Series) -> pd.Series:
        from spark.sentiment_analyzer import SentimentLexicon

        def _analyze(text):
            if not text:
                return "neutral"
            sentiment, _ = SentimentLexicon.analyze(text)
            return sentiment

        return series.fillna('').apply(_analyze)

    @pandas_udf(FloatType())
    def sentiment_score_pandas(series: pd.Series) -> pd.Series:
        from spark.sentiment_analyzer import SentimentLexicon

        def _score(text):
            if not text:
                return 0.0
            _, score = SentimentLexicon.analyze(text)
            return float(score)

        return series.fillna('').apply(_score)

    return sentiment_label_pandas, sentiment_score_pandas


# ═══════════════════════════════════════════════════════════════
# 方案 C：Spark SQL 原生（仅数据清洗阶段）
# ═══════════════════════════════════════════════════════════════

def clean_spark_sql_native(df: DataFrame, text_column: str = "text") -> DataFrame:
    """
    用 Spark SQL regexp_replace 链替代 Python UDF 完成数据清洗。

    可覆盖的操作：去 HTML、去 URL、去 @、去 # 话题标签、去多余空白。
    无法覆盖的操作：表情映射、繁简转换、全角→半角（仍需 Python UDF 辅助）。
    """
    col = F.col(text_column)

    # 1) 去除 HTML 标签
    col = F.regexp_replace(col, r'<[^>]+>', '')
    # 2) 去除 URL
    col = F.regexp_replace(col, r'http[s]?://\S+', '')
    # 3) 去除 @用户
    col = F.regexp_replace(col, r'@[\w\u4e00-\u9fff]+', '')
    # 4) 去除 #话题# → 保留内容
    col = F.regexp_replace(col, r'#([^#]+)#', '$1')
    # 5) 去除多余空白
    col = F.regexp_replace(col, r'\s+', ' ')
    col = F.trim(col)

    df = df.withColumn("cleaned_text", col)
    return df


def clean_spark_sql_hybrid(df: DataFrame, text_column: str = "text") -> DataFrame:
    """
    混合方案：用 SQL 原生做正则清洗，用轻量级 Pandas UDF 做表情/繁简/全角。
    """
    # 先用 SQL 原生完成正则操作
    col = F.col(text_column)
    col = F.regexp_replace(col, r'<[^>]+>', '')
    col = F.regexp_replace(col, r'http[s]?://\S+', '')
    col = F.regexp_replace(col, r'@[\w\u4e00-\u9fff]+', '')
    col = F.regexp_replace(col, r'#([^#]+)#', '$1')
    col = F.regexp_replace(col, r'\s+', ' ')
    col = F.trim(col)
    df = df.withColumn("_pre_clean", col)

    # 再用 Pandas UDF 完成表情映射 + 繁简 + 全角
    from pyspark.sql.functions import pandas_udf

    @pandas_udf(StringType())
    def _post_clean(series: pd.Series) -> pd.Series:
        def _fix(text):
            if not text:
                return ""
            # 表情替换
            def _rep(m):
                return EMOJI_MAP.get(m.group(0), m.group(0))
            text = re.sub(r'\[[\w\u4e00-\u9fff]+\]', _rep, text)
            # 繁简
            text = ''.join(T2S_MAP.get(c, c) for c in text)
            # 全角→半角
            chars = []
            for ch in text:
                code = ord(ch)
                if code == 0x3000:
                    chars.append(' ')
                elif 0xFF01 <= code <= 0xFF5E:
                    chars.append(chr(code - 0xFEE0))
                else:
                    chars.append(ch)
            return ''.join(chars).strip()
        return series.fillna('').apply(_fix)

    df = df.withColumn("cleaned_text", _post_clean(F.col("_pre_clean")))
    df = df.drop("_pre_clean")
    return df


# ═══════════════════════════════════════════════════════════════
# 计时辅助
# ═══════════════════════════════════════════════════════════════

def timed(label, fn, df):
    start = time.perf_counter()
    out = fn(df)
    rows = out.count()  # force action
    elapsed = time.perf_counter() - start
    print(f'  {label}: {elapsed:.4f}s  rows={rows}', flush=True)
    return out, elapsed, rows


# ═══════════════════════════════════════════════════════════════
# 测试运行
# ═══════════════════════════════════════════════════════════════

def build_spark(label: str) -> SparkSession:
    spark = (
        SparkSession.builder
        .master('local[2]')
        .appName(f'UDF-Benchmark-{label}')
        .config('spark.driver.memory', '2g')
        .config('spark.executor.memory', '2g')
        .config('spark.sql.shuffle.partitions', '4')
        .config('spark.ui.showConsoleProgress', 'false')
        .config('spark.python.worker.reuse', 'false')
        .config('spark.network.timeout', '300s')
        .config('spark.executor.heartbeatInterval', '30s')
        .config('spark.sql.execution.arrow.pyspark.enabled', 'true')
        .config('spark.sql.adaptive.enabled', 'true')
        .config('spark.serializer', 'org.apache.spark.serializer.KryoSerializer')
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel('WARN')
    return spark


def load_data(spark: SparkSession, n: int = 10000) -> DataFrame:
    pdf = pd.read_csv(DATA_PATH, usecols=['review', 'label']).head(n)
    pdf = pdf.rename(columns={'review': 'text'})
    pdf['text'] = pdf['text'].fillna('').astype(str)
    pdf['label'] = pdf['label'].astype(int)
    return spark.createDataFrame(pdf[['text', 'label']]).repartition(4)


def dedup(df: DataFrame) -> DataFrame:
    return (
        df.filter(F.length(F.col("cleaned_text")) > 0)
        .withColumn("text_hash", F.md5(F.col("cleaned_text")))
        .dropDuplicates(["text_hash"])
    )


def run_approach_a(spark, df_src):
    """方案 A：全部使用普通 Python UDF"""
    print('\n── 方案 A：普通 Python UDF ──', flush=True)
    result = {'approach': 'A_regular_udf'}

    clean_udf = make_clean_udf_regular()
    df, t, _ = timed('清洗', lambda d: dedup(d.withColumn("cleaned_text", clean_udf(F.col("text")))), df_src)
    result['clean'] = t

    tok_udf = make_tokenize_udf_regular()
    df, t, _ = timed('分词', lambda d: d.withColumn("tokens", tok_udf(F.col("cleaned_text"))), df)
    result['tokenize'] = t

    sent_udf = make_sentiment_udf_regular()
    def _sent(d):
        d2 = d.withColumn("sentiment_result", sent_udf(F.col("cleaned_text")))
        return d2.withColumn("sentiment", F.col("sentiment_result.sentiment")) \
                 .withColumn("sentiment_score", F.col("sentiment_result.score")) \
                 .drop("sentiment_result")
    df, t, rows = timed('情感分析', _sent, df)
    result['sentiment'] = t
    result['total'] = result['clean'] + result['tokenize'] + result['sentiment']
    result['rows'] = rows
    return result


def run_approach_b(spark, df_src):
    """方案 B：全部使用 Pandas UDF"""
    print('\n── 方案 B：Pandas UDF ──', flush=True)
    result = {'approach': 'B_pandas_udf'}

    clean_pudf = make_clean_pandas_udf()
    df, t, _ = timed('清洗', lambda d: dedup(d.withColumn("cleaned_text", clean_pudf(F.col("text")))), df_src)
    result['clean'] = t

    tok_pudf = make_tokenize_pandas_udf()
    df, t, _ = timed('分词', lambda d: d.withColumn("tokens", tok_pudf(F.col("cleaned_text"))), df)
    result['tokenize'] = t

    sent_label, sent_score = make_sentiment_pandas_udf()
    def _sent(d):
        return d.withColumn("sentiment", sent_label(F.col("cleaned_text"))) \
                .withColumn("sentiment_score", sent_score(F.col("cleaned_text")))
    df, t, rows = timed('情感分析', _sent, df)
    result['sentiment'] = t
    result['total'] = result['clean'] + result['tokenize'] + result['sentiment']
    result['rows'] = rows
    return result


def run_approach_c_sql(spark, df_src):
    """方案 C-1：数据清洗用纯 SQL 原生（不含表情/繁简/全角）"""
    print('\n── 方案 C-1：Spark SQL 原生清洗（纯正则） ──', flush=True)
    result = {'approach': 'C1_sql_native_regex_only'}

    df, t, _ = timed('清洗', lambda d: dedup(clean_spark_sql_native(d)), df_src)
    result['clean'] = t
    result['rows'] = _
    return result


def run_approach_c_hybrid(spark, df_src):
    """方案 C-2：数据清洗用 SQL+Pandas UDF 混合"""
    print('\n── 方案 C-2：SQL 正则 + Pandas UDF 后处理 ──', flush=True)
    result = {'approach': 'C2_sql_hybrid'}

    df, t, _ = timed('清洗', lambda d: dedup(clean_spark_sql_hybrid(d)), df_src)
    result['clean'] = t
    result['rows'] = _
    return result


def main():
    results = []

    for run_id in [1, 2]:
        print(f'\n{"="*60}', flush=True)
        print(f'  第 {run_id} 轮测试', flush=True)
        print(f'{"="*60}', flush=True)

        # 方案 A
        spark = build_spark(f'A-run{run_id}')
        df_src = load_data(spark)
        ra = run_approach_a(spark, df_src)
        ra['run'] = run_id
        results.append(ra)
        spark.stop()

        # 方案 B
        spark = build_spark(f'B-run{run_id}')
        df_src = load_data(spark)
        rb = run_approach_b(spark, df_src)
        rb['run'] = run_id
        results.append(rb)
        spark.stop()

        # 方案 C-1
        spark = build_spark(f'C1-run{run_id}')
        df_src = load_data(spark)
        rc1 = run_approach_c_sql(spark, df_src)
        rc1['run'] = run_id
        results.append(rc1)
        spark.stop()

        # 方案 C-2
        spark = build_spark(f'C2-run{run_id}')
        df_src = load_data(spark)
        rc2 = run_approach_c_hybrid(spark, df_src)
        rc2['run'] = run_id
        results.append(rc2)
        spark.stop()

    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')

    # ── 汇总输出 ──
    print(f'\n{"="*60}', flush=True)
    print('  汇总结果', flush=True)
    print(f'{"="*60}', flush=True)

    def avg(approach, key):
        vals = [r[key] for r in results if r['approach'] == approach and key in r]
        return sum(vals) / len(vals) if vals else None

    # 全阶段对比
    print('\n## 全流程对比（清洗+分词+情感分析）')
    print('| 阶段 | 普通UDF | Pandas UDF | 提升 |')
    print('|---|---:|---:|---:|')
    for stage_cn, key in [('数据清洗', 'clean'), ('分词', 'tokenize'), ('情感分析', 'sentiment'), ('总耗时', 'total')]:
        a = avg('A_regular_udf', key)
        b = avg('B_pandas_udf', key)
        if a and b:
            imp = (a - b) / a * 100
            print(f'| {stage_cn} | {a:.2f}s | {b:.2f}s | {imp:+.2f}% |')

    # 清洗阶段对比
    print('\n## 数据清洗阶段对比')
    print('| 方案 | 清洗耗时 | 提升 |')
    print('|---|---:|---:|')
    a_clean = avg('A_regular_udf', 'clean')
    approaches = [
        ('A 普通 Python UDF', 'A_regular_udf'),
        ('B Pandas UDF', 'B_pandas_udf'),
        ('C1 Spark SQL 纯正则', 'C1_sql_native_regex_only'),
        ('C2 SQL+Pandas UDF 混合', 'C2_sql_hybrid'),
    ]
    for label, key in approaches:
        v = avg(key, 'clean')
        if v and a_clean:
            imp = (a_clean - v) / a_clean * 100
            imp_str = f'{imp:+.2f}%' if key != 'A_regular_udf' else '—'
            print(f'| {label} | {v:.2f}s | {imp_str} |')

    print(f'\nResults saved to: {OUT_PATH}')


if __name__ == '__main__':
    main()
