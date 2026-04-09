package com.weibo.model.training;

import com.weibo.model.data.SparkDataReader;
import com.weibo.model.data.WeiboDataSetIterator;
import lombok.extern.slf4j.Slf4j;
import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Row;
import org.apache.spark.sql.SparkSession;
import org.deeplearning4j.eval.Evaluation;
import org.deeplearning4j.nn.conf.MultiLayerConfiguration;
import org.deeplearning4j.nn.conf.NeuralNetConfiguration;
import org.deeplearning4j.nn.conf.layers.LSTM;
import org.deeplearning4j.nn.conf.layers.RnnOutputLayer;
import org.deeplearning4j.nn.multilayer.MultiLayerNetwork;
import org.deeplearning4j.nn.weights.WeightInit;
import org.nd4j.linalg.activations.Activation;
import org.nd4j.linalg.dataset.api.iterator.DataSetIterator;
import org.nd4j.linalg.learning.config.Adam;
import org.nd4j.linalg.lossfunctions.LossFunctions;

import java.io.File;

/**
 * 使用Deeplearning4j训练LSTM情感分析模型的主作业。
 */
@Slf4j
public class LSTMTrainingJob {

    private static final int VECTOR_SIZE = 100; // Word2Vec向量维度
    private static final int LSTM_LAYER_SIZE = 256; // LSTM层大小
    private static final int NUM_CLASSES = 3; // 类别数 (positive, negative, neutral)

    public static void main(String[] args) throws Exception {
        log.info("Starting LSTM model training job...");

        // 1. 初始化Spark Session
        SparkSession spark = SparkSession.builder()
                .appName("LSTMTrainingLoader")
                .master("local[*]")
                .getOrCreate();

        // 2. 加载数据
        log.info("Loading preprocessed data...");
        Dataset<Row> preprocessedData = SparkDataReader.readData(spark, "/path/to/processed/data");

        // 3. 准备DataSetIterator
        // 假设'label'列是整数类型 0, 1, 2
        // 假设数据已分为训练集和测试集
        Dataset<Row>[] splits = preprocessedData.randomSplit(new double[]{0.8, 0.2});
        Dataset<Row> trainingData = splits[0];
        Dataset<Row> testData = splits[1];

        log.info("Preparing training data iterator...");
        DataSetIterator trainIter = WeiboDataSetIterator.fromSpark(trainingData, "word2vec_features", "label", NUM_CLASSES, 32);
        log.info("Preparing test data iterator...");
        DataSetIterator testIter = WeiboDataSetIterator.fromSpark(testData, "word2vec_features", "label", NUM_CLASSES, 32);


        // 2. 构建LSTM网络配置
        MultiLayerConfiguration conf = new NeuralNetConfiguration.Builder()
                .seed(12345)
                .updater(new Adam(0.001))
                .weightInit(WeightInit.XAVIER)
                .list()
                .layer(0, new LSTM.Builder().nIn(VECTOR_SIZE).nOut(LSTM_LAYER_SIZE)
                        .activation(Activation.TANH).build())
                .layer(1, new RnnOutputLayer.Builder(LossFunctions.LossFunction.MCXENT)
                        .activation(Activation.SOFTMAX).nIn(LSTM_LAYER_SIZE).nOut(NUM_CLASSES).build())
                .build();

        // 3. 初始化网络
        MultiLayerNetwork model = new MultiLayerNetwork(conf);
        model.init();

        log.info("LSTM model configured. Starting training...");

        // 4. 训练模型
        log.info("Starting model training...");
        for (int i = 0; i < 5; i++) { // 训练5个epoch
            log.info("Epoch {}/5", i + 1);
            model.fit(trainIter);
        }
        log.info("Model training completed.");

        // 5. 评估模型
        log.info("Evaluating model performance...");
        Evaluation eval = model.evaluate(testIter);
        log.info(eval.stats());

        // 6. 保存模型
        File modelFile = new File("/path/to/save/weibo-sentiment-lstm-model.zip");
        model.save(modelFile, true);
        log.info("Model saved successfully to: {}", modelFile.getAbsolutePath());
    }
}
