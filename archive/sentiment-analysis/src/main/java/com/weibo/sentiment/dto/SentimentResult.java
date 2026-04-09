package com.weibo.sentiment.dto;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class SentimentResult {
    private final String originalText;
    private final double score;
    private final String label;
    private final double confidence;
    private final String method; // e.g., "rule-based", "bert", "hybrid"

    public static String scoreToLabel(double score) {
        if (score > 0.2) return "Positive";
        if (score < -0.2) return "Negative";
        return "Neutral";
    }

    @Override
    public String toString() {
        return String.format("SentimentResult{text='%s', score=%.4f, label='%s', confidence=%.2f, method=%s}",
                originalText, score, label, confidence, method);
    }
}
