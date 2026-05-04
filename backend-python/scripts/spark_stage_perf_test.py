import json
import os
import time
from pathlib import Path

import pandas as pd
from pyspark.sql import SparkSession

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

from spark.spark_pipeline import DataCleaner, ChineseTokenizer, FeatureExtractor, SentimentProcessor

DATA_PATH = ROOT / 'data' / 'weibo_senti_100k.csv'
OUT_PATH = ROOT / 'scripts' / 'spark_stage_perf_results_large.json'
DATA_SIZES = [50000, 99999]


def build_spark(mode: str, run_id: int, data_size: int) -> SparkSession:
    builder = (
        SparkSession.builder
        .master('local[2]')
        .appName(f'SparkStagePerf-{data_size}-{mode}-run{run_id}')
        .config('spark.driver.memory', '4g')
        .config('spark.executor.memory', '4g')
        .config('spark.sql.shuffle.partitions', '8')
        .config('spark.ui.showConsoleProgress', 'false')
        .config('spark.python.worker.reuse', 'false')
        .config('spark.network.timeout', '300s')
        .config('spark.executor.heartbeatInterval', '30s')
    )
    if mode == 'optimized':
        builder = (
            builder
            .config('spark.sql.adaptive.enabled', 'true')
            .config('spark.sql.adaptive.coalescePartitions.enabled', 'true')
            .config('spark.serializer', 'org.apache.spark.serializer.KryoSerializer')
            .config('spark.sql.autoBroadcastJoinThreshold', '10485760')
        )
    else:
        builder = (
            builder
            .config('spark.sql.adaptive.enabled', 'false')
            .config('spark.sql.adaptive.coalescePartitions.enabled', 'false')
            .config('spark.serializer', 'org.apache.spark.serializer.JavaSerializer')
            .config('spark.sql.autoBroadcastJoinThreshold', '-1')
        )
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    return spark


def timed_count(stage_name, fn, df):
    start = time.perf_counter()
    out = fn(df)
    rows = out.count()
    elapsed = time.perf_counter() - start
    print(f'{stage_name}: {elapsed:.4f}s, rows={rows}', flush=True)
    return out, elapsed, rows


def run_once(mode: str, run_id: int, data_size: int):
    print(f'===== SIZE {data_size} | {mode.upper()} RUN {run_id} =====', flush=True)
    spark = build_spark(mode, run_id, data_size)
    try:
        pdf = pd.read_csv(DATA_PATH, usecols=['review', 'label']).head(data_size)
        pdf = pdf.rename(columns={'review': 'text'})
        pdf['text'] = pdf['text'].fillna('').astype(str)
        pdf['label'] = pdf['label'].astype(int)
        df = spark.createDataFrame(pdf[['text', 'label']]).repartition(8)
        source_count = df.count()
        print(f'Input rows: {source_count}', flush=True)

        total_start = time.perf_counter()
        clean_df, clean_time, clean_rows = timed_count(
            'data_cleaning',
            lambda x: DataCleaner.clean_dataframe(x, text_column='text'),
            df,
        )
        token_df, token_time, token_rows = timed_count(
            'tokenization',
            lambda x: ChineseTokenizer.tokenize_dataframe(x, text_column='cleaned_text'),
            clean_df,
        )
        feature_df, feature_time, feature_rows = timed_count(
            'feature_extraction',
            lambda x: FeatureExtractor.extract_keywords(x, tokens_column='tokens'),
            token_df,
        )
        sent_df, sentiment_time, sentiment_rows = timed_count(
            'sentiment_analysis',
            lambda x: SentimentProcessor.process_sentiment(x, text_column='cleaned_text'),
            feature_df,
        )
        total_rows = sent_df.count()
        total_time = time.perf_counter() - total_start
        print(f'total: {total_time:.4f}s, rows={total_rows}', flush=True)

        return {
            'mode': mode,
            'run': run_id,
            'data_size': data_size,
            'input_rows': source_count,
            'output_rows': total_rows,
            'data_cleaning_seconds': clean_time,
            'tokenization_seconds': token_time,
            'feature_extraction_seconds': feature_time,
            'sentiment_analysis_seconds': sentiment_time,
            'total_seconds': total_time,
            'spark_conf': {
                'spark.sql.adaptive.enabled': spark.conf.get('spark.sql.adaptive.enabled'),
                'spark.sql.adaptive.coalescePartitions.enabled': spark.conf.get('spark.sql.adaptive.coalescePartitions.enabled'),
                'spark.serializer': spark.conf.get('spark.serializer'),
                'spark.sql.autoBroadcastJoinThreshold': spark.conf.get('spark.sql.autoBroadcastJoinThreshold'),
            },
        }
    finally:
        spark.stop()


def main():
    results = []
    if OUT_PATH.exists():
        results = json.loads(OUT_PATH.read_text(encoding='utf-8'))
    completed = {(item['data_size'], item['mode'], item['run']) for item in results}
    for data_size in DATA_SIZES:
        for mode in ['baseline', 'optimized']:
            for run_id in [1, 2]:
                key = (data_size, mode, run_id)
                if key in completed:
                    print(f'Skip completed: size={data_size}, mode={mode}, run={run_id}', flush=True)
                    continue
                result = run_once(mode, run_id, data_size)
                results.append(result)
                OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print('===== ALL RESULTS JSON =====')
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f'Results saved to: {OUT_PATH}')


if __name__ == '__main__':
    main()
