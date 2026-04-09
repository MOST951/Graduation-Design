package com.weibo.sentiment.dto;

/**
 * Enum representing the different types of analysis models available.
 */
public enum AnalysisModelType {
    /**
     * Rule-based model using sentiment lexicons.
     */
    RULE_BASED,

    /**
     * Deep learning model based on BERT.
     */
    BERT_MODEL,

    /**
     * A hybrid approach combining multiple models.
     */
    HYBRID
}
