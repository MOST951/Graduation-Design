package com.weibo.web.dto.response;

import com.weibo.web.entity.SentimentResult;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * DTO for representing a sentiment analysis result.
 */
@Data
public class AnalysisResponse {

    private Long id;
    private String weiboId;
    private String content;
    private String sentiment;
    private Double confidence;
    private LocalDateTime publishTime;
    private LocalDateTime createdAt;

    /**
     * Factory method to create an AnalysisResponse from a SentimentResult entity.
     *
     * @param result the entity to convert
     * @return a new AnalysisResponse DTO
     */
    public static AnalysisResponse fromEntity(SentimentResult result) {
        AnalysisResponse response = new AnalysisResponse();
        response.setId(result.getId());
        response.setWeiboId(result.getWeiboId());
        response.setContent(result.getContent());
        response.setSentiment(result.getSentiment());
        response.setConfidence(result.getConfidence());
        response.setPublishTime(result.getPublishTime());
        response.setCreatedAt(result.getCreatedAt());
        return response;
    }
}
