package com.weibo.collector.task;

import lombok.Builder;
import lombok.Data;

/**
 * 任务配置类。
 */
@Data
@Builder
public class TaskConfig {

    private int maxRetries;
    // Other fields would go here

}
