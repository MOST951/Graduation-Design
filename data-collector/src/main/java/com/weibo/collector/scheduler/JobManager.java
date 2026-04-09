package com.weibo.collector.scheduler;

import com.weibo.collector.spider.WeiboSpider;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

import javax.annotation.PreDestroy;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * Manages the execution of data collection jobs.
 * <p>
 * This class is responsible for creating and submitting crawler tasks to a thread pool,
 * enabling concurrent data collection.
 * </p>
 */
@Slf4j
@Component
public class JobManager {
    private final Map<String, String> jobStatus = new ConcurrentHashMap<>();

    @Autowired
    private ApplicationContext context;

    private final ExecutorService executorService = Executors.newFixedThreadPool(10);

    /**
     * Starts a new crawling job for a given URL.
     *
     * @param url The URL to be crawled.
     */
    public void submitJob(String url) {
        startJob(url);
    }

    public String trackJobProgress(String url) {
        return jobStatus.getOrDefault(url, "NOT_STARTED");
    }

    public String getJobResult(String url) {
        // In a real application, this would retrieve the result from a persistent store
        return "Job result for " + url;
    }

    public void startJob(String url) {
        log.info("Starting new job for URL: {}", url);
        try {
            // Get a new prototype instance of WeiboSpider
            WeiboSpider spider = context.getBean(WeiboSpider.class);
            spider.setStartUrl(url);
            
            jobStatus.put(url, "RUNNING");
            executorService.submit(() -> {
                try {
                    spider.startCrawl(); // Use the startCrawl method we added earlier
                    jobStatus.put(url, "COMPLETED");
                } catch (Exception e) {
                    log.error("Job for URL {} failed", url, e);
                    jobStatus.put(url, "FAILED");
                }
            });
        } catch (Exception e) {
            log.error("Failed to start job for URL: {}", url, e);
            jobStatus.put(url, "FAILED_TO_START");
        }
    }

    @PreDestroy
    public void shutdown() {
        executorService.shutdown();
        try {
            if (!executorService.awaitTermination(60, TimeUnit.SECONDS)) {
                executorService.shutdownNow();
            }
        } catch (InterruptedException e) {
            executorService.shutdownNow();
        }
    }
}
