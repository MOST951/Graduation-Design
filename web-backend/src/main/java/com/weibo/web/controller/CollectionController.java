package com.weibo.web.controller;

import com.weibo.common.model.ResponseResult;
import com.weibo.web.entity.CollectionTask;
import com.weibo.web.service.SparkService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/collection")
public class CollectionController {

    @Autowired
    private SparkService sparkService;

    @PostMapping("/tasks")
    public ResponseResult<String> createTask(@RequestBody CollectionTask task) throws Exception {
        // Logic to save the task and submit it to Spark
        String jobId = sparkService.submitJob(
            "data-collector.jar",
            "com.weibo.collector.DataCollectorJob",
            task.getKeywords()
        );
        return ResponseResult.success("Task created and submitted with job ID: " + jobId);
    }
}
