package com.weibo.web.service;

import com.weibo.web.dto.spark.JobStatus;
import com.weibo.web.dto.spark.SparkClusterInfo;
import com.weibo.web.dto.spark.SparkJob;
import com.weibo.web.dto.spark.SparkJobRequest;

import java.util.List;

public interface SparkJobService {

    /**
     * Submits a new Spark job.
     */
    SparkJob submitJob(SparkJobRequest request);

    /**
     * Stops a running Spark job.
     */
    boolean stopJob(String jobId);

    /**
     * Queries the status of a specific job.
     */
    SparkJob getJobStatus(String jobId);

    /**
     * Lists all jobs, optionally filtering by status.
     */
    List<SparkJob> listJobs(JobStatus status);

    /**
     * Retrieves the recent logs for a specific job.
     */
    String getJobLogs(String jobId, int lines);

    /**
     * Gets information about the Spark cluster.
     */
    SparkClusterInfo getClusterInfo();
}
