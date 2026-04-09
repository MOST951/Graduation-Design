package com.weibo.web.service;

import com.weibo.web.config.SparkProperties;
import com.weibo.web.dto.spark.*;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.*;
import java.util.stream.Collectors;

@Service
@Slf4j
public class SparkJobServiceImpl implements SparkJobService {

    private final SparkProperties sparkProperties;
    private final Map<String, SparkJob> jobStore = new ConcurrentHashMap<>();
    private final Map<String, List<String>> logStore = new ConcurrentHashMap<>();
    private ExecutorService submissionExecutor;

    public SparkJobServiceImpl(SparkProperties sparkProperties) {
        this.sparkProperties = sparkProperties;
    }

    @PostConstruct
    public void init() {
        submissionExecutor = Executors.newCachedThreadPool();
    }

    @PreDestroy
    public void shutdown() {
        submissionExecutor.shutdown();
    }

    @Override
    public SparkJob submitJob(SparkJobRequest request) {
        String jobId = UUID.randomUUID().toString();
        SparkJob job = new SparkJob();
        job.setJobId(jobId);
        job.setJobName(request.getJobName());
        job.setStatus(JobStatus.SUBMITTED);
        job.setSubmitTime(LocalDateTime.now());

        jobStore.put(jobId, job);
        logStore.put(jobId, new CopyOnWriteArrayList<>());

        CompletableFuture.runAsync(() -> {
            try {
                submitSparkJob(job, request);
            } catch (Exception e) {
                log.error("Spark job submission failed for jobId: {}", jobId, e);
                job.setStatus(JobStatus.FAILED);
                job.setErrorMessage(e.getMessage());
            }
        }, submissionExecutor);

        return job;
    }

    private void submitSparkJob(SparkJob job, SparkJobRequest request) throws Exception {
        List<String> command = buildSparkSubmitCommand(request);
        ProcessBuilder processBuilder = new ProcessBuilder(command);
        Process process = processBuilder.start();
        monitorProcess(job, process);
    }

    private void monitorProcess(SparkJob job, Process process) {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                log.info("Spark Job [{}]: {}", job.getJobId(), line);
                logStore.get(job.getJobId()).add(line);

                if (line.contains("application_")) {
                    String appId = extractAppId(line);
                    if (job.getAppId() == null) { // Set AppId only once
                        job.setAppId(appId);
                        job.setSparkUiUrl(constructSparkUiUrl(appId));
                        job.setStatus(JobStatus.RUNNING);
                    }
                }
            }

            int exitCode = process.waitFor();
            job.setStatus(exitCode == 0 ? JobStatus.SUCCEEDED : JobStatus.FAILED);

        } catch (Exception e) {
            log.error("Failed while monitoring Spark job process for jobId: {}", job.getJobId(), e);
            job.setStatus(JobStatus.FAILED);
            job.setErrorMessage(e.getMessage());
        } finally {
            job.setFinishTime(LocalDateTime.now());
        }
    }

    @Override
    public boolean stopJob(String jobId) {
        // Implementation for stopping a job via command line
        return false; // Placeholder
    }

    @Override
    public SparkJob getJobStatus(String jobId) {
        return jobStore.get(jobId);
    }

    @Override
    public List<SparkJob> listJobs(JobStatus status) {
        return jobStore.values().stream()
                .filter(job -> status == null || job.getStatus() == status)
                .collect(Collectors.toList());
    }

    @Override
    public String getJobLogs(String jobId, int lines) {
        List<String> logs = logStore.get(jobId);
        if (logs == null) return "No logs found for job " + jobId;
        int start = Math.max(0, logs.size() - lines);
        return String.join("\n", logs.subList(start, logs.size()));
    }

    @Override
    public SparkClusterInfo getClusterInfo() {
        return SparkClusterInfo.builder().masterUrl(sparkProperties.getMasterUrl()).status("PLACEHOLDER").build();
    }

    private List<String> buildSparkSubmitCommand(SparkJobRequest request) {
        List<String> command = new ArrayList<>();
        command.add(sparkProperties.getSubmitPath());
        command.add("--class");
        command.add(request.getMainClass());
        command.add("--master");
        command.add(sparkProperties.getMasterUrl());
        command.add("--deploy-mode");
        command.add("cluster");
        command.add("--name");
        command.add(request.getJobName());

        if (request.getParameters() != null) {
            request.getParameters().forEach((key, value) -> {
                command.add("--conf");
                command.add(String.format("%s=%s", key, value));
            });
        }

        command.add(request.getJarPath());
        return command;
    }

    private String extractAppId(String logLine) {
        int startIndex = logLine.indexOf("application_");
        if (startIndex == -1) return null;
        // Assuming app ID is the last word in the line
        String[] parts = logLine.substring(startIndex).split("\\s+");
        return parts[0];
    }

    private String constructSparkUiUrl(String appId) {
        // This might need to be more sophisticated depending on your cluster setup (e.g., YARN vs. Standalone)
        return sparkProperties.getUiUrl() + "/cluster/app/" + appId;
    }
}
