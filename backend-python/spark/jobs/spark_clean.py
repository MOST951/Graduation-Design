"""
论文 6.3.2 分布式数据预处理
============================

Spark 作业: 从 HDFS 读取原始 JSON -> URL/@提及 regexp_replace ->
    Python UDF 处理表情/繁简 -> 写 Parquet 到 HDFS /cleaned/dt=YYYY-MM-DD/

提交方式 (spark-submit):
    spark-submit \
        --master spark://spark-master:7077 \
        --deploy-mode client \
        --name WeiboClean \
        --conf spark.sql.shuffle.partitions=4 \
        spark_clean.py \
        --input  "hdfs://namenode:9000/raw/dt=2026-05-14/*.json" \
        --output "hdfs://namenode:9000/cleaned/dt=2026-05-14"

对应论文核心代码:
    df = spark.read.json("hdfs:///raw/*.json")
    df = df.withColumn("clean", clean_udf(df.content))
    df.write.parquet("hdfs:///cleaned")
"""
import argparse
import re
import sys
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType


# ==================== 表情 / 繁简: Spark SQL + Python UDF 混合策略 ====================
# 论文 6.3.2: 较复杂的清洗如(表情、繁简)等用 Python UDF 实现.
# 实现策略:
#   - Unicode 表情 / 微博方括号表情: 使用 regexp_replace (Catalyst 优化, 无需 Python 参与)
#   - 繁简转换: 在 Driver 端通过 mapInPandas / collect 方式处理, 或使用 pandas_udf
#   - 多余空白压缩: regexp_replace

# Spark SQL regexp 可匹配的 emoji 范围 (Java regex 语法)
_EMOJI_JAVA_REGEX = (
    "[\\x{1F600}-\\x{1F64F}"
    "\\x{1F300}-\\x{1F5FF}"
    "\\x{1F680}-\\x{1F6FF}"
    "\\x{1F1E0}-\\x{1F1FF}"
    "\\x{2600}-\\x{27BF}"
    "\\x{1F900}-\\x{1F9FF}"
    "\\x{FE00}-\\x{FE0F}"
    "\\x{200D}]+"
)
# 微博方括号表情: [笑] [哈哈] [doge]
_WEIBO_EMOJI_REGEX = r"\[[^\[\]]{1,8}\]"


def _apply_t2s_udf(spark, df, col_name):
    """繁体转简体: 在 Driver 端用 pandas_udf (Arrow) 或 Python UDF 实现.
    
    论文 6.3.2: 繁简转换用 Python UDF 实现.
    这里使用 pandas_udf(Arrow 序列化) 避免 Python 版本不匹配问题.
    如果 OpenCC 不可用则跳过.
    """
    try:
        from opencc import OpenCC
        converter = OpenCC("t2s")
        
        # 使用 pandas_udf (基于 Arrow, 不受 Python 版本差异影响)
        from pyspark.sql.functions import pandas_udf
        import pandas as pd
        
        @pandas_udf(StringType())
        def t2s_pandas_udf(texts: pd.Series) -> pd.Series:
            return texts.apply(lambda t: converter.convert(t) if t else t)
        
        df = df.withColumn(col_name, t2s_pandas_udf(F.col(col_name)))
        print("[spark_clean] 繁简转换: 已启用 (OpenCC + pandas_udf)")
    except ImportError:
        print("[spark_clean] 繁简转换: OpenCC 未安装, 跳过")
    except Exception as e:
        print(f"[spark_clean] 繁简转换: 回退跳过 ({e})")
    return df


# ==================== 主流程 ====================

def build_spark(app_name: str, shuffle_partitions: int) -> SparkSession:
    """构建 SparkSession. 不指定 master (由 spark-submit 提供)."""
    return (
        SparkSession.builder
        .appName(app_name)
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
        .config("spark.sql.parquet.compression.codec", "snappy")
        # HDFS 客户端连接, 默认从 HADOOP_CONF_DIR 读 core-site.xml / hdfs-site.xml
        .getOrCreate()
    )


def main():
    parser = argparse.ArgumentParser(description="论文 6.3.2 Spark 数据清洗作业")
    parser.add_argument("--input",  required=True,
                        help="HDFS 原始 JSON 路径, 如 hdfs://namenode:9000/raw/dt=2026-05-14/*.json")
    parser.add_argument("--output", required=True,
                        help="Parquet 输出路径, 如 hdfs://namenode:9000/cleaned/dt=2026-05-14")
    parser.add_argument("--text-field", default="text",
                        help="原 JSON 中微博正文字段名 (默认 text)")
    parser.add_argument("--shuffle-partitions", type=int, default=4)
    parser.add_argument("--app-name", default=f"WeiboClean-{datetime.now().strftime('%H%M%S')}")
    args = parser.parse_args()

    spark = build_spark(args.app_name, args.shuffle_partitions)
    spark.sparkContext.setLogLevel("WARN")
    print(f"[spark_clean] Spark {spark.version} appId={spark.sparkContext.applicationId}")
    print(f"[spark_clean] input={args.input}")
    print(f"[spark_clean] output={args.output}")

    # ---- 读取 ----
    # 论文核心代码: df = spark.read.json("hdfs:///raw/*.json")
    # multiLine=true: 项目里 crawl_result_*.json 是 JSON 数组格式 (非 JSON Lines),
    # 必须打开 multiLine 才能把每条微博解析为一行; 否则每个字符被当 corrupt_record.
    df_raw = spark.read.option("multiLine", "true").json(args.input)
    total_in = df_raw.count()
    print(f"[spark_clean] 读取原始记录数: {total_in}")
    if total_in == 0:
        print("[spark_clean] 输入为空, 直接退出")
        spark.stop()
        sys.exit(0)

    text_col = args.text_field
    if text_col not in df_raw.columns:
        # 兼容常见字段名
        for alt in ("text_raw", "content", "body"):
            if alt in df_raw.columns:
                text_col = alt
                break
        else:
            print(f"[spark_clean] ERROR: 找不到文本字段 (尝试 {args.text_field}/text_raw/content/body)")
            spark.stop()
            sys.exit(2)

    # ---- 内置函数: URL / @提及 / 话题# / 空行 ----
    # 论文 6.3.2: 用内置函数 regexp_replace 处理 URL 和 @提及 (性能好, 走 Catalyst 优化)
    df = (
        df_raw
        .withColumn("_url_stripped",     F.regexp_replace(F.col(text_col), r"https?://\S+",    ""))
        .withColumn("_mention_stripped", F.regexp_replace(F.col("_url_stripped"), r"@[\w\-]+", ""))
        .withColumn("_topic_stripped",   F.regexp_replace(F.col("_mention_stripped"), r"#([^#]{1,30})#", r"$1"))
        .drop("_url_stripped", "_mention_stripped")
    )

    # ---- 表情清洗 (Spark SQL 内置函数, 论文 6.3.2) ----
    # 去 Unicode 表情 (regexp_replace, Catalyst 优化)
    df = df.withColumn("_emoji_stripped",
        F.regexp_replace(F.col("_topic_stripped"), _EMOJI_JAVA_REGEX, ""))
    # 去微博方括号表情 [笑] [doge] (regexp_replace)
    df = df.withColumn("_weibo_emoji_stripped",
        F.regexp_replace(F.col("_emoji_stripped"), _WEIBO_EMOJI_REGEX, ""))
    # 压缩多余空白
    df = df.withColumn("clean",
        F.trim(F.regexp_replace(F.col("_weibo_emoji_stripped"), r"\s+", " ")))
    df = df.drop("_topic_stripped", "_emoji_stripped", "_weibo_emoji_stripped")

    # ---- 繁简转换 (Python UDF, 论文 6.3.2) ----
    # 论文核心代码: df = df.withColumn("clean", clean_udf(df.content))
    df = _apply_t2s_udf(spark, df, "clean")

    # ---- 去空 & 去重 ----
    df = df.filter(F.length(F.col("clean")) >= 2)
    if "id" in df.columns:
        df = df.dropDuplicates(["id"])
    else:
        df = df.dropDuplicates(["clean"])

    # ---- 分区写 Parquet ----
    # 论文核心代码: df.write.parquet("hdfs:///cleaned")
    # 自动并行分片: Spark 会按当前分区数 (shuffle-partitions) 并行写多个 part 文件.
    df.write.mode("overwrite").parquet(args.output)

    # ---- 质量报告 ----
    total_out = df.count()
    print(f"[spark_clean] 清洗后记录数: {total_out} (dropped={total_in - total_out})")
    print(f"[spark_clean] 输出路径: {args.output}")
    print(f"[spark_clean] 分区数: {df.rdd.getNumPartitions()}")

    spark.stop()


if __name__ == "__main__":
    main()
