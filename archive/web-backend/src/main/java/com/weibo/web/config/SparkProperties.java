package com.weibo.web.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "spark")
public class SparkProperties {
    /**
     * The URL of the Spark Master.
     * e.g., spark://spark-master:7077
     */
    private String masterUrl;

    /**
     * The base URL for the Spark Web UI.
     * e.g., http://spark-master:8080
     */
    private String uiUrl;

    /**
     * The path to the spark-submit executable.
     * Can be an absolute path if not in the system's PATH.
     */
    private String submitPath = "spark-submit";

    /**
     * The default deployment mode (e.g., client or cluster).
     */
    private String deployMode = "client";
}
