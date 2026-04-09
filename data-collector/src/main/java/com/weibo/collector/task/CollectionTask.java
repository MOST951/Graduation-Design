package com.weibo.collector.task;

import java.io.Serializable;

/**
 * 数据采集任务定义
 */
import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class CollectionTask implements Serializable {

    private static final long serialVersionUID = 1L;

    private String taskId;
    private String[] keywords;
    private long startTime;
    private long endTime;
    private String status;
    private double progress;

    // Getters and Setters
}
