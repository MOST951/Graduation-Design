"""
UDF 性能对比基准测试 v2
======================

对比方案：
  A) 普通 Python UDF（原始逐行方案）
  B) mapPartitions 批量处理（模拟向量化，无 Arrow 依赖）
  C1) Spark SQL 原生 regexp_replace（仅数据清洗，纯正则）
  C2) SQL 正则 + mapPartitions 后处理（完整清洗）

注：Pandas UDF 需要 Arrow Java 14+，当前环境 Spark 3.5.3 内置 Arrow 12.0.1，
与 Java 21 不兼容（sun.misc.Unsafe），故使用 mapPartitions 作为等效替代。

测试数据：10,000 条微博文本
每种方案运行 2 次取平均
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import List

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

from pyspark.sql import SparkSession, DataFrame, Row
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, FloatType, IntegerType,
    ArrayType
)

DATA_PATH = ROOT / 'data' / 'weibo_senti_100k.csv'
OUT_PATH = ROOT / 'scripts' / 'udf_benchmark_results.json'

# ── 共享常量 ─────────────────────────────────────────────────────
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


# ── 单条文本处理函数 ─────────────────────────────────────────────
def _clean_one(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'@[\w\u4e00-\u9fff]+', '', text)
    text = re.sub(r'#([^#]+)#', r'\1', text)
    def _rep(m):
        return EMOJI_MAP.get(m.group(0), m.group(0))
    text = re.sub(r'\[[\w\u4e00-\u9fff]+\]', _rep, text)
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


def _tokenize_one(text):
    import jieba
    if not text:
        return []
    words = jieba.lcut(text)
    return [w for w in words if len(w) > 1 and w not in STOP_WORDS]


def _sentiment_one(text):
    from spark.sentiment_analyzer import SentimentLexicon
    if not text:
        return ("neutral", 0.0)
    sentiment, score = SentimentLexicon.analyze(text)
    return (sentiment, float(score))


# ══════════════════════════════════════════════════════════════
# 方案 A：普通 Python UDF
# ══════════════════════════════════════════════════════════════

def make_clean_udf():
    return F.udf(_clean_one, StringType())


def make_tokenize_udf():
    import jieba
    stop = STOP_WORDS
    def tokenize(text):
        if not text:
            return []
        words = jieba.lcut(text)
        return [w for w in words if len(w) > 1 and w not in stop]
    return F.udf(tokenize, ArrayType(StringType()))


def make_sentiment_udf():
    from spark.sentiment_analyzer import SentimentLexicon
    def analyze(text):
        if not text:
            return ("neutral", 0.0)
        sentiment, score = SentimentLexicon.analyze(text)
        return (sentiment, float(score))
    schema = StructType([
        StructField("sentiment", StringType(), True),
        StructField("score", FloatType(), True)
    ])
    return F.udf(analyze, schema)


# ══════════════════════════════════════════════════════════════
# 方案 B：mapPartitions 批量处理
# ══════════════════════════════════════════════════════════════

def clean_map_partitions(df, text_column='text'):
    """用 mapPartitions 做批量数据清洗"""
    schema = df.schema.add(StructField("cleaned_text", StringType(), True))

    def process(iterator):
        for row in iterator:
            d = row.asDict()
            d['cleaned_text'] = _clean_one(d.get(text_column, ''))
            yield Row(**d)

    return df.rdd.mapPartitions(process).toDF(schema)


def tokenize_map_partitions(df, text_column='cleaned_text'):
    """用 mapPartitions 做批量分词"""
    schema = df.schema.add(StructField("tokens", ArrayType(StringType()), True))

    def process(iterator):
        import jieba
        stop = STOP_WORDS
        for row in iterator:
            d = row.asDict()
            text = d.get(text_column, '')
            if text:
                words = jieba.lcut(text)
                d['tokens'] = [w for w in words if len(w) > 1 and w not in stop]
            else:
                d['tokens'] = []
            yield Row(**d)

    return df.rdd.mapPartitions(process).toDF(schema)


def sentiment_map_partitions(df, text_column='cleaned_text'):
    """用 mapPartitions 做批量情感分析"""
    schema = (df.schema
              .add(StructField("sentiment", StringType(), True))
              .add(StructField("sentiment_score", FloatType(), True)))

    def process(iterator):
        from spark.sentiment_analyzer import SentimentLexicon
        for row in iterator:
            d = row.asDict()
            text = d.get(text_column, '')
            if text:
                sentiment, score = SentimentLexicon.analyze(text)
                d['sentiment'] = sentiment
                d['sentiment_score'] = float(score)
            else:
                d['sentiment'] = 'neutral'
                d['sentiment_score'] = 0.0
            yield Row(**d)

    return df.rdd.mapPartitions(process).toDF(schema)


# ══════════════════════════════════════════════════════════════
# 方案 C1：Spark SQL 原生（纯正则清洗）
# ══════════════════════════════════════════════════════════════

def clean_spark_sql_native(df, text_column='text'):
    col = F.col(text_column)
    col = F.regexp_replace(col, r'<[^>]+>', '')
    col = F.regexp_replace(col, r'http[s]?://\S+', '')
    col = F.regexp_replace(col, r'@[\w\u4e00-\u9fff]+', '')
    col = F.regexp_replace(col, r'#([^#]+)#', '$1')
    col = F.regexp_replace(col, r'\s+', ' ')
    col = F.trim(col)
    return df.withColumn("cleaned_text", col)


# ══════════════════════════════════════════════════════════════
# 方案 C2：SQL 正则 + mapPartitions 后处理
# ══════════════════════════════════════════════════════════════

def clean_sql_plus_mappartitions(df, text_column='text'):
    # 第一步：SQL 原生做正则清洗
    col = F.col(text_column)
    col = F.regexp_replace(col, r'<[^>]+>', '')
    col = F.regexp_replace(col, r'http[s]?://\S+', '')
    col = F.regexp_replace(col, r'@[\w\u4e00-\u9fff]+', '')
    col = F.regexp_replace(col, r'#([^#]+)#', '$1')
    col = F.regexp_replace(col, r'\s+', ' ')
    col = F.trim(col)
    df = df.withColumn("_pre_clean", col)

    # 第二步：mapPartitions 做表情/繁简/全角
    schema = df.schema
    # 需要把 _pre_clean 替换成 cleaned_text
    final_fields = [f for f in schema.fields if f.name != '_pre_clean']
    final_fields.append(StructField("cleaned_text", StringType(), True))
    final_schema = StructType(final_fields)

    def process(iterator):
        for row in iterator:
            d = row.asDict()
            text = d.pop('_pre_clean', '')
            if not text:
                d['cleaned_text'] = ''
                yield Row(**d)
                continue
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
            d['cleaned_text'] = ''.join(chars).strip()
            yield Row(**d)

    return df.rdd.mapPartitions(process).toDF(final_schema)


# ══════════════════════════════════════════════════════════════
# 辅助函数
# ══════════════════════════════════════════════════════════════

def timed(label, fn, df):
    start = time.perf_counter()
    out = fn(df)
    rows = out.count()
    elapsed = time.perf_counter() - start
    print(f'  {label}: {elapsed:.4f}s  rows={rows}', flush=True)
    return out, elapsed, rows


def dedup(df):
    return (
        df.filter(F.length(F.col("cleaned_text")) > 0)
        .withColumn("text_hash", F.md5(F.col("cleaned_text")))
        .dropDuplicates(["text_hash"])
    )


def build_spark(label):
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
        .config('spark.sql.adaptive.enabled', 'true')
        .config('spark.serializer', 'org.apache.spark.serializer.KryoSerializer')
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel('WARN')
    return spark


def load_data(spark, n=10000):
    pdf = pd.read_csv(DATA_PATH, usecols=['review', 'label']).head(n)
    pdf = pdf.rename(columns={'review': 'text'})
    pdf['text'] = pdf['text'].fillna('').astype(str)
    pdf['label'] = pdf['label'].astype(int)
    return spark.createDataFrame(pdf[['text', 'label']]).repartition(4)


# ══════════════════════════════════════════════════════════════
# 测试入口
# ══════════════════════════════════════════════════════════════

def run_A(spark, df_src):
    """方案 A：全部使用普通 Python UDF"""
    print('\n── 方案 A：普通 Python UDF ──', flush=True)
    r = {'approach': 'A_regular_udf'}

    cudf = make_clean_udf()
    df, t, _ = timed('清洗', lambda d: dedup(d.withColumn("cleaned_text", cudf(F.col("text")))), df_src)
    r['clean'] = t

    tudf = make_tokenize_udf()
    df, t, _ = timed('分词', lambda d: d.withColumn("tokens", tudf(F.col("cleaned_text"))), df)
    r['tokenize'] = t

    sudf = make_sentiment_udf()
    def _s(d):
        d2 = d.withColumn("sr", sudf(F.col("cleaned_text")))
        return d2.withColumn("sentiment", F.col("sr.sentiment")) \
                 .withColumn("sentiment_score", F.col("sr.score")).drop("sr")
    df, t, rows = timed('情感分析', _s, df)
    r['sentiment'] = t
    r['total'] = r['clean'] + r['tokenize'] + r['sentiment']
    r['rows'] = rows
    return r


def run_B(spark, df_src):
    """方案 B：mapPartitions 批量处理"""
    print('\n── 方案 B：mapPartitions 批量处理 ──', flush=True)
    r = {'approach': 'B_mapPartitions'}

    df, t, _ = timed('清洗', lambda d: dedup(clean_map_partitions(d)), df_src)
    r['clean'] = t

    df, t, _ = timed('分词', lambda d: tokenize_map_partitions(d), df)
    r['tokenize'] = t

    df, t, rows = timed('情感分析', lambda d: sentiment_map_partitions(d), df)
    r['sentiment'] = t
    r['total'] = r['clean'] + r['tokenize'] + r['sentiment']
    r['rows'] = rows
    return r


def run_C1(spark, df_src):
    """方案 C1：Spark SQL 原生正则清洗"""
    print('\n── 方案 C1：Spark SQL 原生清洗（纯正则） ──', flush=True)
    r = {'approach': 'C1_sql_native'}

    df, t, rows = timed('清洗', lambda d: dedup(clean_spark_sql_native(d)), df_src)
    r['clean'] = t
    r['rows'] = rows
    return r


def run_C2(spark, df_src):
    """方案 C2：SQL正则 + mapPartitions 后处理"""
    print('\n── 方案 C2：SQL正则 + mapPartitions 后处理 ──', flush=True)
    r = {'approach': 'C2_sql_hybrid'}

    df, t, rows = timed('清洗', lambda d: dedup(clean_sql_plus_mappartitions(d)), df_src)
    r['clean'] = t
    r['rows'] = rows
    return r


def main():
    results = []

    for run_id in [1, 2]:
        print(f'\n{"="*60}', flush=True)
        print(f'  第 {run_id} 轮测试', flush=True)
        print(f'{"="*60}', flush=True)

        for approach_fn, label in [(run_A, 'A'), (run_B, 'B'), (run_C1, 'C1'), (run_C2, 'C2')]:
            spark = build_spark(f'{label}-run{run_id}')
            df_src = load_data(spark)
            r = approach_fn(spark, df_src)
            r['run'] = run_id
            results.append(r)
            spark.stop()

    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')

    # ── 汇总 ──
    print(f'\n{"="*60}', flush=True)
    print('  汇总结果', flush=True)
    print(f'{"="*60}', flush=True)

    def avg(approach, key):
        vals = [r[key] for r in results if r['approach'] == approach and key in r]
        return sum(vals) / len(vals) if vals else None

    # 全流程对比
    a_stages = [('数据清洗', 'clean'), ('分词', 'tokenize'), ('情感分析', 'sentiment'), ('总耗时', 'total')]
    print('\n## 全流程对比（A 普通UDF vs B mapPartitions）')
    print('| 阶段 | 普通UDF | mapPartitions | 提升 |')
    print('|---|---:|---:|---:|')
    for name, key in a_stages:
        a = avg('A_regular_udf', key)
        b = avg('B_mapPartitions', key)
        if a and b:
            imp = (a - b) / a * 100
            print(f'| {name} | {a:.2f}s | {b:.2f}s | {imp:+.2f}% |')

    # 清洗阶段对比
    print('\n## 数据清洗阶段对比')
    print('| 方案 | 清洗耗时 | vs 普通UDF |')
    print('|---|---:|---:|')
    a_clean = avg('A_regular_udf', 'clean')
    for label, key in [('A 普通 Python UDF', 'A_regular_udf'),
                       ('B mapPartitions', 'B_mapPartitions'),
                       ('C1 Spark SQL 纯正则', 'C1_sql_native'),
                       ('C2 SQL+mapPartitions', 'C2_sql_hybrid')]:
        v = avg(key, 'clean')
        if v is not None and a_clean:
            imp = (a_clean - v) / a_clean * 100
            s = f'{imp:+.2f}%' if key != 'A_regular_udf' else '—'
            print(f'| {label} | {v:.2f}s | {s} |')

    print(f'\nResults saved to: {OUT_PATH}')


if __name__ == '__main__':
    main()
