package com.weibo.web.dto.spark;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class SparkClusterInfo {
    private String masterUrl;
    private String sparkVersion;
    private int activeWorkers;
    private int cores;
    private int memoryGb;
    private String status;
    private List<String> runningApps;
}
