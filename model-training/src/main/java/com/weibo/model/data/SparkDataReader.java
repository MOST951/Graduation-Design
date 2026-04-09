package com.weibo.model.data;

import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Row;
import org.apache.spark.sql.SparkSession;

/**
 * 负责从Spark处理后的数据源（如Parquet文件）中读取特征数据。
 */
public class SparkDataReader {

    public static Dataset<Row> readData(SparkSession spark, String path) {
        return spark.read().parquet(path);
    }
}
