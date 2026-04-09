package com.weibo.web.dto.request;

import lombok.Data;

import javax.validation.constraints.Max;
import javax.validation.constraints.Min;

/**
 * Reusable DTO for pagination requests.
 */
@Data
public class PageRequest {

    @Min(value = 0, message = "Page number must be non-negative.")
    private int page = 0;

    @Min(value = 1, message = "Page size must be at least 1.")
    @Max(value = 100, message = "Page size cannot exceed 100.")
    private int size = 10;
}
