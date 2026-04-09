package com.weibo.sentiment.dto;

import java.util.Map;

/**
 * Represents the operational status of the sentiment analysis service.
 */
public class ServiceStatus {
    private final boolean isHealthy;
    private final String message;
    private final Map<String, Object> modelStatuses;

    public ServiceStatus(boolean isHealthy, String message, Map<String, Object> modelStatuses) {
        this.isHealthy = isHealthy;
        this.message = message;
        this.modelStatuses = modelStatuses;
    }

    // Getters
    public boolean isHealthy() { return isHealthy; }
    public String getMessage() { return message; }
    public Map<String, Object> getModelStatuses() { return modelStatuses; }
}
