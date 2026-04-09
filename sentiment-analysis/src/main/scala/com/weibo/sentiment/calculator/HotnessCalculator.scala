package com.weibo.sentiment.calculator

import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.functions._

/**
 * Calculates a "hotness" score for Weibo posts.
 * <p>
 * The score is based on a weighted combination of engagement metrics like
 * comments, retweets, and likes.
 * </p>
 */
object HotnessCalculator {

  /**
   * Calculates hotness scores for a DataFrame of Weibo posts.
   *
   * @param df The input DataFrame, expected to have 'comments_count', 'reposts_count', and 'attitudes_count' columns.
   * @return A DataFrame with an added "hotness_score" column.
   */
  def calculate(df: DataFrame): DataFrame = {
    df.withColumn("hotness_score", 
      col("comments_count") * 0.4 + 
      col("reposts_count") * 0.3 + 
      col("attitudes_count") * 0.3
    )
  }
}
