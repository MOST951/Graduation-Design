package com.weibo.web.dto.response;

import com.weibo.web.entity.CollectionTask;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * DTO for representing a collection task.
 */
@Data
public class TaskResponse {

    private Long id;
    private String taskName;
    private String keywords;
    private String status;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    /**
     * Factory method to create a TaskResponse from a CollectionTask entity.
     *
     * @param task the entity to convert
     * @return a new TaskResponse DTO
     */
    public static TaskResponse fromEntity(CollectionTask task) {
        TaskResponse response = new TaskResponse();
        response.setId(task.getId());
        response.setTaskName(task.getTaskName());
        response.setKeywords(task.getKeywords());
        response.setStatus(task.getStatus());
        response.setStartTime(task.getStartTime());
        response.setEndTime(task.getEndTime());
        response.setCreatedAt(task.getCreatedAt());
        response.setUpdatedAt(task.getUpdatedAt());
        return response;
    }
}
