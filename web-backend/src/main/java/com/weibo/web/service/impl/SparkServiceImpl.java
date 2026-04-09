package com.weibo.web.service.impl;

import com.weibo.web.entity.SparkJob;
import com.weibo.web.repository.SparkJobRepository;
import com.weibo.web.service.SparkService;
import com.weibo.web.spark.SparkJobLauncher;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;

@Slf4j
@Service
public class SparkServiceImpl implements SparkService {

    private final SparkJobLauncher jobLauncher;
    private final SparkJobRepository jobRepository;

    @Autowired
    public SparkServiceImpl(SparkJobLauncher jobLauncher, SparkJobRepository jobRepository) {
        this.jobLauncher = jobLauncher;
        this.jobRepository = jobRepository;
    }

    @Override
    public String submitJob(String appResource, String mainClass, String... appArgs) throws IOException, InterruptedException {
        log.info("Submitting Spark job from resource: {} with main class: {}", appResource, mainClass);
        
        String jobId = jobLauncher.launch(appResource, appResource, mainClass, appArgs);

        SparkJob sparkJob = new SparkJob();
        sparkJob.setJobId(jobId);
        sparkJob.setJobName(appResource); // Use resource as job name for simplicity
        sparkJob.setStatus("SUBMITTED");
        sparkJob.setArguments(String.join(" ", appArgs));
        jobRepository.save(sparkJob);

        return jobId;
    }

    @Override
    public String getJobStatus(String appId) {
        return jobRepository.findByJobId(appId)
                .map(SparkJob::getStatus)
                .orElse("UNKNOWN");
    }

    @Override
    public void stopJob(String appId) {
        log.warn("stopJob is not yet implemented. App ID: {}", appId);
        // A real implementation would need to interact with the Spark/YARN API to kill the job.
    }
}
