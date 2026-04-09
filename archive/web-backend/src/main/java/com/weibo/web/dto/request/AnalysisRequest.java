package com.weibo.web.dto.request;

import lombok.Data;

import javax.validation.constraints.NotEmpty;
import javax.validation.constraints.Size;
import java.util.List;

/**
 * DTO for submitting a batch sentiment analysis request.
 */
@Data
public class AnalysisRequest {

    @NotEmpty(message = "Content list cannot be empty")
    @Size(max = 100, message = "Cannot process more than 100 items at a time")
    private Long taskId;

    @NotEmpty(message = "Content list cannot be empty")
    @Size(max = 100, message = "Cannot process more than 100 items at a time")
    private List<String> contents;
}
