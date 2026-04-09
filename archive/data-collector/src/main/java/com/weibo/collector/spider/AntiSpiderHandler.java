package com.weibo.collector.spider;

import com.google.common.util.concurrent.RateLimiter;
import lombok.extern.slf4j.Slf4j;
import org.apache.http.HttpHost;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.List;
import java.util.Random;
import java.util.stream.Collectors;

/**
 * Manages anti-spidering measures like proxy rotation and rate limiting.
 * <p>
 * This class maintains a pool of proxies and enforces a rate limit on outgoing requests
 * to avoid being blocked by the target server.
 * </p>
 */
@Slf4j
@Component
public class AntiSpiderHandler {

        @Autowired
    private ProxyManager proxyManager;
    private final Random random = new Random();
    private final RateLimiter rateLimiter = RateLimiter.create(1.0); // 1 request per second

    /**
     * Initializes the proxy list from a configuration file.
     */
    @PostConstruct
    public void init() {
        try {
                    // Proxy loading is now handled by ProxyManager
        } catch (IOException e) {
            log.error("Failed to load proxy list", e);
            proxyList = Collections.emptyList();
        }
    }

    /**
     * Acquires a permit from the rate limiter, blocking if necessary.
     */
    public void acquire() {
        rateLimiter.acquire();
    }

    /**
     * Retrieves a random proxy from the pool.
     *
     * @return An HttpHost object representing a proxy, or null if the pool is empty.
     */
        public boolean detectAntiSpider(String pageContent) {
        // Simple detection based on keywords in the page content
        return pageContent.contains("验证码") || pageContent.contains("访问受限");
    }

    public void bypassAntiSpider() {
        // In a real scenario, this could trigger a CAPTCHA solving service
        // or switch to a different user agent.
        log.warn("Anti-spider measure detected. Attempting to bypass by delaying...");
        randomDelay(5000, 15000);
    }

    public void randomDelay(int minMillis, int maxMillis) {
        try {
            Thread.sleep(minMillis + random.nextInt(maxMillis - minMillis));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

        public HttpHost getProxy() {
        return proxyManager.getProxy();
    }
}
