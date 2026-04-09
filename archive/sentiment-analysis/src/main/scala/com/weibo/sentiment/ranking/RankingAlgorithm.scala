package com.weibo.sentiment.ranking

import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.functions._

/**
 * Ranks Weibo posts based on a combination of sentiment and hotness.
 * <p>
 * This object defines an algorithm that balances the emotional intensity (sentiment)
 * and the public engagement (hotness) to produce a final ranking score.
 * </p>
 */
object RankingAlgorithm {

  /**
   * Ranks a DataFrame of Weibo posts.
   *
   * @param df The input DataFrame with "sentiment_score" and "hotness_score" columns.
   * @return A DataFrame with an added "rank_score" column, sorted in descending order.
   */
  def rank(df: DataFrame): DataFrame = {
    val rankedDF = df.withColumn("rank_score", 
      col("sentiment_score") * 0.6 + log("hotness_score" + 1) * 0.4 // Log transform hotness to balance scales
    )
    rankedDF.sort(desc("rank_score"))
  }
}
