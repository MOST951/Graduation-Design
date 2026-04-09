package com.weibo.sentiment.dto;

/**
 * Configuration for a sentiment analysis request.
 */
public class AnalysisConfig {
    private AnalysisModelType modelType = AnalysisModelType.BERT_MODEL; // Default model
    private String domain = "base"; // For rule-based model
    private boolean enableConfidence = false;

    public AnalysisConfig(AnalysisModelType modelType) {
        this.modelType = modelType;
    }

    // Getters and Setters
    public AnalysisModelType getModelType() {
        return modelType;
    }

    public void setModelType(AnalysisModelType modelType) {
        this.modelType = modelType;
    }

    public String getDomain() {
        return domain;
    }

    public void setDomain(String domain) {
        this.domain = domain;
    }

    public boolean isEnableConfidence() {
        return enableConfidence;
    }

    public void setEnableConfidence(boolean enableConfidence) {
        this.enableConfidence = enableConfidence;
    }
}
