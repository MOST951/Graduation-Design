package com.weibo.model.data;

import org.apache.spark.ml.linalg.Vector;
import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Row;
import org.nd4j.linalg.api.ndarray.INDArray;
import org.nd4j.linalg.dataset.DataSet;
import org.nd4j.linalg.dataset.api.iterator.DataSetIterator;
import org.nd4j.linalg.factory.Nd4j;
import org.nd4j.linalg.util.FeatureUtil;

import java.util.ArrayList;
import java.util.List;

/**
 * 一个工具类，用于将Spark DataFrame转换为DL4J的DataSetIterator。
 */
public class WeiboDataSetIterator {

    /**
     * 从Spark Dataset创建一个DataSetIterator。
     *
     * @param df          包含特征和标签的Spark Dataset。
     * @param featuresCol 特征向量所在的列名。
     * @param labelCol    标签所在的列名。
     * @param numClasses  总类别数。
     * @param batchSize   每个批次的大小。
     * @return 一个可用于DL4J模型训练的DataSetIterator。
     */
    public static DataSetIterator fromSpark(Dataset<Row> df, String featuresCol, String labelCol, int numClasses, int batchSize) {

        // Collect Spark rows to local and convert to DL4J DataSets
        List<Row> rows = df.collectAsList();
        List<DataSet> dataSets = new ArrayList<>();

        for (Row row : rows) {
            // 1. 提取特征向量并转换为INDArray
            Vector featuresVector = row.getAs(featuresCol);
            INDArray features = Nd4j.create(featuresVector.toArray());

            // 2. 提取标签并转换为one-hot编码的INDArray
            int labelIndex = row.getAs(labelCol);
            INDArray labels = FeatureUtil.toOutcomeVector(labelIndex, numClasses);

            dataSets.add(new DataSet(features, labels));
        }

        // Use org.deeplearning4j.datasets.iterator.impl.ListDataSetIterator from DL4J core
        return new org.deeplearning4j.datasets.iterator.impl.ListDataSetIterator<>(dataSets, batchSize);
    }
}
