package com.weibo.web.dto.spark;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.Map;

@Data
public class SparkJob {
    private String jobId;
    private String jobName;
    private JobType jobType;
    private String mainClass;
    private String jarPath;
    private Map<String, String> parameters;
    private JobStatus status;
    private String sparkMaster;
    private String deployMode;
    private LocalDateTime submitTime;
    private LocalDateTime finishTime;
    private String errorMessage;
    private String appId;
    private String sparkUiUrl;
}
