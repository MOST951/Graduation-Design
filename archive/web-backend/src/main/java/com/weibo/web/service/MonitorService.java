package com.weibo.web.service;

import java.util.Map;

/**
 * Service interface for system monitoring operations.
 */
public interface MonitorService {

    /**
     * Collects various system and application metrics.
     *
     * @return a map of collected metrics
     */
    Map<String, Object> collectMetrics();

    /**
     * Checks the health of the system and its dependencies.
     *
     * @return true if the system is healthy, false otherwise
     */
    boolean checkSystemHealth();

    /**
     * Sends an alert with the given message and severity.
     *
     * @param message the alert message
     * @param severity the severity of the alert
     */
    void sendAlert(String message, String severity);

}
