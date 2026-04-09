package com.weibo.sentiment.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "sentiment.analysis")
public class AnalysisProperties {
    /**
     * Default analysis strategy to use when none is specified in the request.
     * Can be 'hybrid', 'rule', or 'bert'.
     */
    private String defaultStrategy = "hybrid";

    /**
     * The weight assigned to the rule-based score in a static hybrid analysis.
     */
    private double ruleWeight = 0.3;

    /**
     * The weight assigned to the BERT model score in a static hybrid analysis.
     */
    private double bertWeight = 0.7;

    /**
     * The minimum text length to trigger the BERT model in a dynamic hybrid analysis.
     */
    private int bertMinLength = 20;

    /**
     * The confidence threshold below which the BERT model will be triggered in a dynamic hybrid analysis.
     */
    private double confidenceThreshold = 0.6;

    /**
     * Whether to enable caching for sentiment analysis results.
     */
    private boolean enableCache = true;

    /**
     * The maximum number of entries in the sentiment analysis cache.
     */
    private int cacheSize = 10000;

    /**
     * The time-to-live for cache entries in milliseconds (e.g., 3600000 for 1 hour).
     */
    private long cacheTtl = 3600000; // 1 hour
}
