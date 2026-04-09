package com.weibo.web.dto.request;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;

/**
 * Task Request DTO for creating/updating a collection task.
 */
@Data
public class TaskRequest {

    @NotBlank(message = "Task name cannot be blank")
    @Size(max = 255, message = "Task name must be less than 255 characters")
    private String taskName;

    @NotBlank(message = "Keywords cannot be blank")
    private String keywords;
}
