"""
论文 6.3.3 分布式情感分析 (Spark 组织数据 + Flask 推理)
==================================================

Spark 作业: 读 HDFS 清洗后的 Parquet -> foreachPartition 在每个分区内把文本
聚成一批调用 Flask /api/sentiment/batch -> 结果 JDBC 写入 MySQL.

提交方式:
    spark-submit \
        --master spark://spark-master:7077 \
        --jars /opt/bitnami/spark/jars/mysql-connector-j-8.0.33.jar \
        spark_sentiment.py \
        --input  "hdfs://namenode:9000/cleaned/dt=2026-05-14" \
        --flask-url "http://web:5000/api/sentiment/batch" \
        --jdbc-url  "jdbc:mysql://mysql:3306/weibo_sentiment?useSSL=false&characterEncoding=utf8" \
        --jdbc-user root --jdbc-password <pw> \
        --jdbc-table sentiment_results

对应论文核心代码:
    def analyze_partition(rows):
        texts = [row.text for row in rows]
        resp = requests.post("http://flask:5000/batch", json={"texts": texts})
        return [(row.id, r['label']) for row, r in zip(rows, resp.json())]
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, FloatType, TimestampType
)


# ==================== foreachPartition 回调 ====================

def make_analyze_partition(flask_url: str, batch_size: int, timeout: int,
                            text_col: str, id_col: str):
    """工厂函数: 返回一个可被 executor 序列化的 partition 处理闭包.

    闭包捕获 flask_url/batch_size 等标量参数 (str/int), 无需把整个 SparkContext
    传过去. Executor 进程里会 import requests 发 HTTP.
    """
    def analyze_partition(rows):
        # 在 Executor 进程内部延迟 import, 避免 driver 端强依赖
        import requests

        batch_texts = []
        batch_ids = []
        out = []
        session = requests.Session()
        stats = {'ok': 0, 'fail': 0}

        def _flush():
            if not batch_texts:
                return
            try:
                t0 = time.time()
                resp = session.post(
                    flask_url,
                    json={'texts': batch_texts},
                    timeout=timeout,
                )
                elapsed_ms = int((time.time() - t0) * 1000)
                data = resp.json()
                # 兼容多种响应结构:
                #   Flask 当前: {'code':200, 'data': {'results': [...]}}
                #   简化:        {'results': [...]}
                #   直接列表:    {'data': [...]}
                results = data.get('results')
                if results is None:
                    inner = data.get('data')
                    if isinstance(inner, dict):
                        results = inner.get('results') or []
                    elif isinstance(inner, list):
                        results = inner
                    else:
                        results = []
                if len(results) != len(batch_texts):
                    # 长度不一致 — 回退: 全部标记 failed
                    stats['fail'] += len(batch_texts)
                    for _id in batch_ids:
                        out.append((_id, 'unknown', 0.0, 'length_mismatch', elapsed_ms))
                else:
                    stats['ok'] += len(batch_texts)
                    for _id, r in zip(batch_ids, results):
                        label = str(r.get('label', r.get('sentiment', 'unknown')))
                        score = float(r.get('score', r.get('confidence', 0.0)))
                        out.append((_id, label, score, None, elapsed_ms))
            except Exception as e:
                stats['fail'] += len(batch_texts)
                err = str(e)[:200]
                for _id in batch_ids:
                    out.append((_id, 'unknown', 0.0, err, 0))
            finally:
                batch_texts.clear()
                batch_ids.clear()

        for row in rows:
            text = getattr(row, text_col, None) or ''
            rid = getattr(row, id_col, None)
            if rid is None:
                continue
            batch_texts.append(str(text)[:512])   # 限长防 BERT 超长
            batch_ids.append(str(rid))
            if len(batch_texts) >= batch_size:
                _flush()
        _flush()

        print(f"[spark_sentiment] partition done: ok={stats['ok']} fail={stats['fail']}")
        return iter(out)

    return analyze_partition


# ==================== 主流程 ====================

def main():
    p = argparse.ArgumentParser(description="论文 6.3.3 Spark 分布式情感分析")
    p.add_argument("--input",       required=True, help="Parquet 输入路径 (HDFS)")
    p.add_argument("--flask-url",   default=os.getenv("FLASK_BATCH_URL",
                                                     "http://web:5000/api/sentiment/batch"))
    p.add_argument("--text-col",    default="clean")
    p.add_argument("--id-col",      default="id")
    p.add_argument("--batch-size",  type=int, default=32)
    p.add_argument("--http-timeout", type=int, default=30)
    # JDBC 写 MySQL
    p.add_argument("--jdbc-url",      default=os.getenv("MYSQL_JDBC_URL", ""))
    p.add_argument("--jdbc-user",     default=os.getenv("DB_USER", "root"))
    p.add_argument("--jdbc-password", default=os.getenv("DB_PASSWORD", ""))
    p.add_argument("--jdbc-table",    default="sentiment_results")
    p.add_argument("--output-json",   default="",
                   help="同时保存 JSON 汇总到此路径 (HDFS 或本地); 为空则不写")
    # HBase 写入 (论文 4.3.3 HBase 宽表存储)
    p.add_argument("--hbase-host",    default=os.getenv("HBASE_HOST", ""),
                   help="HBase Thrift host (如 hbase-master); 为空则不写 HBase")
    p.add_argument("--hbase-port",    type=int, default=int(os.getenv("HBASE_PORT", "9090")))
    p.add_argument("--hbase-table",   default="sentiment_result")
    args = p.parse_args()

    spark = (
        SparkSession.builder
        .appName(f"WeiboSentiment-{datetime.now().strftime('%H%M%S')}")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    print(f"[spark_sentiment] Spark {spark.version} appId={spark.sparkContext.applicationId}")
    print(f"[spark_sentiment] input={args.input} flask={args.flask_url}")

    # ---- 读 Parquet ----
    df = spark.read.parquet(args.input)
    total = df.count()
    print(f"[spark_sentiment] 待分析记录数: {total}")
    if total == 0:
        print("[spark_sentiment] 无数据, 退出")
        spark.stop()
        sys.exit(0)

    # 只保留必要字段, 减少网络传输
    for col in (args.text_col, args.id_col):
        if col not in df.columns:
            print(f"[spark_sentiment] ERROR: 列不存在 {col} (cols={df.columns})")
            spark.stop()
            sys.exit(2)

    # HBase RowKey 与宽表所需的辅助字段一并保留 (论文 4.3.1 / 4.3.4)
    # RowKey = "{keyword}|{reverse_ts}|{weibo_id}"
    # 同主题/话题在物理上连续, scan前缀即可拉同关键词全部数据
    keep_cols = [args.id_col, args.text_col]
    for c in ("keyword", "user_name", "publish_time", "created_at",
              "reposts_count", "comments_count", "attitudes_count"):
        if c in df.columns and c not in keep_cols:
            keep_cols.append(c)
    working = df.select(*keep_cols)

    # ---- foreachPartition (实际用 mapPartitions 拿回结果) ----
    # 论文核心代码: rdd.mapPartitions(analyze_partition) 等效写法
    analyze = make_analyze_partition(
        args.flask_url, args.batch_size, args.http_timeout,
        args.text_col, args.id_col,
    )
    result_rdd = working.rdd.mapPartitions(analyze)

    # 结果 schema
    out_schema = StructType([
        StructField("weibo_id",    StringType(), False),
        StructField("label",       StringType(), True),
        StructField("score",       FloatType(),  True),
        StructField("error",       StringType(), True),
        StructField("latency_ms",  FloatType(),  True),
    ])
    result_df = spark.createDataFrame(
        result_rdd.map(lambda t: (t[0], t[1], float(t[2]), t[3], float(t[4]))),
        schema=out_schema,
    ).withColumn("analyzed_at", F.current_timestamp())

    result_df.cache()
    ok_cnt = result_df.filter(F.col("error").isNull()).count()
    fail_cnt = result_df.count() - ok_cnt
    avg_latency = (result_df.filter(F.col("error").isNull())
                   .agg(F.avg("latency_ms")).collect()[0][0]) or 0.0
    print(f"[spark_sentiment] 成功={ok_cnt} 失败={fail_cnt} 平均延迟={avg_latency:.1f}ms")

    # ---- 写 MySQL (可选) ----
    if args.jdbc_url:
        try:
            (result_df.write
             .mode("append")
             .format("jdbc")
             .option("url", args.jdbc_url)
             .option("dbtable", args.jdbc_table)
             .option("user", args.jdbc_user)
             .option("password", args.jdbc_password)
             .option("driver", "com.mysql.cj.jdbc.Driver")
             .save())
            print(f"[spark_sentiment] ✅ 已写入 MySQL: {args.jdbc_table}")
        except Exception as e:
            print(f"[spark_sentiment] ⚠️ MySQL 写入失败: {e}")
    else:
        print("[spark_sentiment] 未配置 JDBC, 跳过 MySQL 写入")

    # ---- 写 HBase 宽表 (论文 4.3.1 / 4.3.4 表 4-8) ----
    # RowKey = "{keyword}|{reverse_ts}|{weibo_id}"  -> 同关键词数据物理连续, prefix scan O(1) 定位
    # 列族 (4):
    #   info      : text, user_name, publish_time
    #   sentiment : label, score, confidence
    #   metrics   : comment_count, like_count, repost_count
    #   ranking   : comprehensive_score (后续 spark_ranking.py 写入, 此处先占位)
    if args.hbase_host:
        hbase_host  = args.hbase_host
        hbase_port  = args.hbase_port
        hbase_table = args.hbase_table

        # 把原始字段 join 回结果, 这样写 HBase 时能拿到 text/user/metrics
        joined = result_df.join(
            working, result_df.weibo_id == working[args.id_col], how='left'
        )

        text_col = args.text_col
        id_col   = args.id_col

        def _write_partition_to_hbase(rows):
            try:
                import happybase
            except ImportError:
                return
            import time as _time
            conn = happybase.Connection(hbase_host, port=hbase_port, timeout=10000)
            try:
                tbl = conn.table(hbase_table)
                with tbl.batch(batch_size=100) as b:
                    for r in rows:
                        d = r.asDict()
                        wid = str(d.get('weibo_id') or d.get(id_col) or '')
                        kw  = (d.get('keyword') or 'unknown')[:32]
                        # 论文 4.3.1: 反转时间戳让最新数据排前
                        rev_ts = 9999999999 - int(_time.time())
                        rk = f"{kw}|{rev_ts:010d}|{wid}".encode()
                        # 数值统一 str(...).encode(), 缺值跳过 (符合 HBase 稀疏写入)
                        data = {}
                        # info 列族
                        if d.get(text_col):
                            data[b'info:text'] = str(d[text_col])[:1024].encode()
                        if d.get('user_name'):
                            data[b'info:user_name'] = str(d['user_name']).encode()
                        if d.get('publish_time') or d.get('created_at'):
                            pt = d.get('publish_time') or d.get('created_at')
                            data[b'info:publish_time'] = str(pt).encode()
                        # sentiment 列族
                        data[b'sentiment:label']      = (d.get('label') or '').encode()
                        data[b'sentiment:score']      = str(d.get('score') or 0.0).encode()
                        # 简单的 confidence: |score| (论文置信度 [0,1])
                        try:
                            conf = abs(float(d.get('score') or 0.0))
                        except Exception:
                            conf = 0.0
                        data[b'sentiment:confidence'] = f"{conf:.4f}".encode()
                        # metrics 列族
                        if d.get('comments_count') is not None:
                            data[b'metrics:comment_count'] = str(d['comments_count']).encode()
                        if d.get('attitudes_count') is not None:
                            data[b'metrics:like_count']    = str(d['attitudes_count']).encode()
                        if d.get('reposts_count') is not None:
                            data[b'metrics:repost_count']  = str(d['reposts_count']).encode()
                        # ranking 列族 (此处仅初始化, 三维度排序作业后续 update)
                        data[b'ranking:comprehensive_score'] = b'0.0'

                        b.put(rk, data)
            finally:
                conn.close()

        try:
            joined.foreachPartition(_write_partition_to_hbase)
            print(f"[spark_sentiment] ✅ 已写入 HBase {hbase_host}:{hbase_port}/{hbase_table} "
                  f"(RowKey=keyword|reverse_ts|weibo_id, 4 列族)")
        except Exception as e:
            print(f"[spark_sentiment] ⚠️ HBase 写入失败: {e}")
    else:
        print("[spark_sentiment] 未配置 HBase, 跳过 HBase 写入")

    # ---- 备份 JSON 输出 ----
    if args.output_json:
        try:
            result_df.write.mode("overwrite").json(args.output_json)
            print(f"[spark_sentiment] 结果备份: {args.output_json}")
        except Exception as e:
            print(f"[spark_sentiment] ⚠️ JSON 备份失败: {e}")

    spark.stop()


if __name__ == "__main__":
    main()
