package com.weibo.sentiment.service;

import com.weibo.sentiment.dto.AnalysisConfig;
import com.weibo.sentiment.dto.SentimentResult;
import com.weibo.sentiment.dto.ServiceStatus;

import java.util.List;

/**
 * Defines the contract for the sentiment analysis service.
 * This service provides methods for analyzing text sentiment using various strategies.
 */
public interface SentimentAnalysisService {

    /**
     * Analyzes the sentiment of a single piece of text based on the provided configuration.
     *
     * @param text The text to analyze.
     * @param config The configuration specifying which model to use and other parameters.
     * @return A SentimentResult object containing the analysis outcome.
     */
    SentimentResult analyzeText(String text, AnalysisConfig config);

    /**
     * Analyzes the sentiment of a batch of texts.
     *
     * @param texts A list of texts to analyze.
     * @param config The configuration for the analysis.
     * @return A list of SentimentResult objects, one for each input text.
     */
    List<SentimentResult> analyzeBatch(List<String> texts, AnalysisConfig config);

    /**
     * Performs a hybrid sentiment analysis by combining results from multiple models
     * (e.g., rule-based and deep learning) for a more robust conclusion.
     *
     * @param text The text to analyze.
     * @return A single, consolidated SentimentResult.
     */
    SentimentResult hybridAnalyze(String text);

    /**
     * Retrieves the current operational status of the sentiment analysis service,
     * including the health of its underlying models.
     *
     * @return A ServiceStatus object.
     */
    ServiceStatus getServiceStatus();
}
