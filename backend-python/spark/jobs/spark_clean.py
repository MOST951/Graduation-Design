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


# ==================== Python UDF: 表情 / 繁简 ====================
# 作为 PySpark UDF 在 Executor 进程里被调用; 各 partition 并行执行.

_EMOJI_RE = re.compile(
    "["                          # 表情 unicode 范围 (论文 6.3.2 "表情") 
    "\U0001F600-\U0001F64F"      # emoticons
    "\U0001F300-\U0001F5FF"      # symbols & pictographs
    "\U0001F680-\U0001F6FF"      # transport & map
    "\U0001F1E0-\U0001F1FF"      # flags
    "\U00002600-\U000027BF"      # misc symbols
    "\U0001F900-\U0001F9FF"      # supplemental symbols
    "]+",
    flags=re.UNICODE,
)
# 微博特色表情: [笑] [哈哈] [doge] 等方括号 emoji
_WEIBO_EMOJI_RE = re.compile(r"\[[^\[\]]{1,8}\]")


def _udf_clean_text(text):
    """Python UDF: 清洗微博正文中无法用 regexp_replace 一次搞定的复杂部分.

    论文 6.3.2 明确说: 较复杂的清洗如(表情、繁简)等用 Python UDF 实现.
    步骤:
      1) 去 unicode emoji
      2) 去微博方括号表情 [笑] [doge]
      3) 繁体 -> 简体 (OpenCC, 可选; 无 opencc 时跳过)
      4) 多余空白压缩
    """
    if text is None:
        return None
    t = _EMOJI_RE.sub("", text)
    t = _WEIBO_EMOJI_RE.sub("", t)
    # 繁简转换 (opencc 存在才做, Executor 首次调用会懒加载)
    try:
        global _OPENCC
        try:
            _OPENCC  # type: ignore
        except NameError:
            try:
                from opencc import OpenCC  # opencc-python-reimplemented
                _OPENCC = OpenCC("t2s")   # 繁 -> 简
            except Exception:
                _OPENCC = None
        if _OPENCC is not None:
            t = _OPENCC.convert(t)
    except Exception:
        pass
    # 压缩空白
    t = re.sub(r"\s+", " ", t).strip()
    return t


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

    # ---- Python UDF: 表情 / 繁简 ----
    # 论文核心代码: df = df.withColumn("clean", clean_udf(df.content))
    clean_udf = F.udf(_udf_clean_text, StringType())
    df = df.withColumn("clean", clean_udf(F.col("_topic_stripped"))).drop("_topic_stripped")

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
