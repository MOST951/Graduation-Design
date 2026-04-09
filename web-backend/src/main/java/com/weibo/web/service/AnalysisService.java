package com.weibo.web.service;

import com.weibo.web.dto.request.AnalysisRequest;
import com.weibo.web.dto.response.AnalysisResponse;
import com.weibo.web.dto.response.PageResponse;
import org.springframework.data.domain.Pageable;

import java.util.List;

/**
 * Service interface for sentiment analysis operations.
 */
public interface AnalysisService {

    /**
     * Performs batch sentiment analysis on a list of texts.
     *
     * @param request the request containing the texts to analyze
     * @return a list of analysis responses
     */
    void batchAnalyze(AnalysisRequest request);

    /**
     * Retrieves a paginated list of sentiment analysis results for a specific task.
     *
     * @param taskId the ID of the collection task
     * @param pageable pagination information
     * @return a paginated response of analysis results
     */
    PageResponse<AnalysisResponse> getResults(Long taskId, Pageable pageable);

    /**
     * Performs trend analysis.
     *
     * @return a map or object representing the trend analysis
     */
    List<com.weibo.web.dto.response.SentimentTrendDTO> getTrendAnalysis(Long taskId);

    byte[] exportResults(Long taskId, String format);

}
