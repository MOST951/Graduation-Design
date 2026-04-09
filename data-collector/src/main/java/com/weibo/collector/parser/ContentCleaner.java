package com.weibo.collector.parser;

import org.springframework.stereotype.Component;

/**
 * 内容清洗器
 */
@Component
public class ContentCleaner {

    public String removeHtmlTags(String text) {
        return text.replaceAll("<[^>]*>", "");
    }

    public String removeEmoji(String text) {
        return text.replaceAll("[\\ud800-\\udbff\\udc00-\\udfff]", "");
    }

    public String normalizeText(String text) {
        // Example: convert full-width characters to half-width
        return text.replaceAll("[\\uff01-\\uff5e]", "");
    }
}
