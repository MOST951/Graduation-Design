package com.weibo.sentiment.cache;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.weibo.sentiment.config.AnalysisProperties;
import com.weibo.sentiment.dto.SentimentResult;
import org.springframework.stereotype.Component;

import java.util.Optional;
import java.util.concurrent.TimeUnit;

/**
 * An in-memory cache for sentiment analysis results to avoid re-computation for the same text.
 * Uses the high-performance Caffeine caching library.
 */
@Component
public class SentimentCache {

    private final Cache<String, SentimentResult> cache;
    private final AnalysisProperties properties;

    public SentimentCache(AnalysisProperties properties) {
        this.properties = properties;
        this.cache = Caffeine.newBuilder()
                .maximumSize(properties.getCacheSize())
                .expireAfterWrite(properties.getCacheTtl(), TimeUnit.MILLISECONDS)
                .recordStats() // Useful for monitoring cache performance via JMX or Actuator
                .build();
    }

    /**
     * Retrieves a sentiment result from the cache if it exists.
     *
     * @param text The original text.
     * @return An Optional containing the cached SentimentResult, or an empty Optional if not found.
     */
    public Optional<SentimentResult> get(String text) {
        if (!properties.isEnableCache()) {
            return Optional.empty();
        }
        return Optional.ofNullable(cache.getIfPresent(generateKey(text)));
    }

    /**
     * Stores a sentiment result in the cache.
     *
     * @param text   The original text.
     * @param result The SentimentResult to cache.
     */
    public void put(String text, SentimentResult result) {
        if (!properties.isEnableCache()) {
            return;
        }
        cache.put(generateKey(text), result);
    }

    /**
     * Generates a consistent cache key from the input text.
     *
     * @param text The input text.
     * @return A normalized, lowercase string to be used as a cache key.
     */
    private String generateKey(String text) {
        // Normalize the key to ensure "Hello World" and "hello world " are treated the same.
        return text.trim().toLowerCase();
    }

    /**
     * Provides access to the underlying cache's statistics.
     *
     * @return The Caffeine cache stats object.
     */
    public com.github.benmanes.caffeine.cache.stats.CacheStats getStats() {
        return cache.stats();
    }
}
