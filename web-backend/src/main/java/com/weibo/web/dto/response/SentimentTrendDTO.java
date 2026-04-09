package com.weibo.web.dto.response;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

/**
 * 用于表示情感趋势数据的DTO。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class SentimentTrendDTO {
    private LocalDate date;
    private String sentiment;
    private Long count;
}
