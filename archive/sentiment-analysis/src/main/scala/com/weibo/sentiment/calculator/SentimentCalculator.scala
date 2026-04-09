package com.weibo.sentiment.calculator

import com.weibo.sentiment.analysis.RuleBasedAnalyzer
import com.weibo.sentiment.model.BertModelWrapper
import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.functions._
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Component

/**
 * Calculates a hybrid sentiment score using both rule-based and model-based approaches.
 */
@Component
class SentimentCalculator @Autowired()(ruleBasedAnalyzer: RuleBasedAnalyzer, bertModel: BertModelWrapper) {

  /**
   * Calculates sentiment scores for a DataFrame.
   *
   * @param df The input DataFrame with a "tokens" and a "cleaned_text" column.
   * @return A DataFrame with an added "sentiment_score" column.
   */
  def calculate(df: DataFrame): DataFrame = {
    val ruleUDF = udf((tokens: Seq[String]) => ruleBasedAnalyzer.analyze(tokens.toList))
    val bertUDF = udf((text: String) => bertModel.predict(text))

    df.withColumn("rule_score", ruleUDF(col("tokens")))
      .withColumn("bert_score", bertUDF(col("cleaned_text")))
      .withColumn("sentiment_score", col("rule_score") * 0.3 + col("bert_score") * 0.7) // Weighted average
  }
}
