package com.weibo.web.service;

import java.io.IOException;

/**
 * Service interface for interacting with Apache Spark.
 */
public interface SparkService {

    /**
     * Submits a Spark job.
     *
     * @param appResource the path to the application JAR
     * @param mainClass the main class to execute
     * @param appArgs arguments for the Spark application
     * @return the application handle ID
     * @throws IOException if there is an error launching the job
     * @throws InterruptedException if the thread is interrupted while waiting for the job to launch
     */
    String submitJob(String appResource, String mainClass, String... appArgs) throws IOException, InterruptedException;

    /**
     * Gets the status of a Spark job.
     *
     * @param appId the application handle ID
     * @return the state of the job (e.g., RUNNING, FINISHED, FAILED)
     */
    String getJobStatus(String appId);

    /**
     * Stops a running Spark job.
     *
     * @param appId the application handle ID
     */
    void stopJob(String appId);

}
