package com.weibo.collector.task;

/**
 * 任务配置类
 */
import lombok.Getter;

@Getter
public class TaskConfig {

    private int maxRetries;
    private int timeout;
    private int rateLimit;
    private String outputFormat;

    private TaskConfig(Builder builder) {
        this.maxRetries = builder.maxRetries;
        this.timeout = builder.timeout;
        this.rateLimit = builder.rateLimit;
        this.outputFormat = builder.outputFormat;
    }

    // Getters

    public static class Builder {
        private int maxRetries = 3;
        private int timeout = 10000; // 10 seconds
        private int rateLimit = 1; // 1 request per second
        private String outputFormat = "json";

        public Builder maxRetries(int maxRetries) {
            this.maxRetries = maxRetries;
            return this;
        }

        public Builder timeout(int timeout) {
            this.timeout = timeout;
            return this;
        }

        public Builder rateLimit(int rateLimit) {
            this.rateLimit = rateLimit;
            return this;
        }

        public Builder outputFormat(String outputFormat) {
            this.outputFormat = outputFormat;
            return this;
        }

        public TaskConfig build() {
            return new TaskConfig(this);
        }
    }
}
