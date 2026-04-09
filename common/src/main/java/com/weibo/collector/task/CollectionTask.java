package com.weibo.collector.task;

import lombok.Data;
import java.io.Serializable;

/**
 * 数据采集任务定义。
 */
@Data
public class CollectionTask implements Serializable {

    private String taskId;
    // Other fields would go here

}
