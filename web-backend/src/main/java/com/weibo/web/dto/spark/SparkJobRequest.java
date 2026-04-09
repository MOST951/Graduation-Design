package com.weibo.web.dto.spark;

import lombok.Data;

import java.util.Map;

/**
 * A request object for submitting a new Spark job.
 */
@Data
public class SparkJobRequest {
    private String jobName;
    private JobType jobType;
    private String mainClass;
    private String jarPath;
    private Map<String, String> parameters;
    private String sparkMaster;
    private String deployMode;
}
