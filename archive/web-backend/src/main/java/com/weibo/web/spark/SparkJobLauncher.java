package com.weibo.web.spark;

import com.weibo.common.exception.BusinessException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.UUID;

/**
 * 负责通过命令行启动Spark作业的组件。
 */
@Slf4j
@Component
public class SparkJobLauncher {

    @Value("${spark.home}")
    private String sparkHome;

    @Value("${spark.master.url}")
    private String sparkMasterUrl;

    public String launch(String jobName, String jarPath, String mainClass, String... args) {
        String jobId = jobName + "-" + UUID.randomUUID().toString();
        log.info("Launching Spark job '{}' with ID: {}.", jobName, jobId);

        try {
            ProcessBuilder processBuilder = new ProcessBuilder(
                sparkHome + "/bin/spark-submit",
                "--class", mainClass,
                "--master", sparkMasterUrl,
                jarPath,
                String.join(" ", args)
            );

            processBuilder.redirectErrorStream(true);
            Process process = processBuilder.start();

            // 异步读取输出，防止阻塞
            new Thread(() -> {
                try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        log.info("[Spark Job - {}]: {}", jobId, line);
                    }
                } catch (Exception e) {
                    log.error("Error reading Spark job output for '{}': {}", jobId, e.getMessage());
                }
            }).start();

            log.info("Spark job '{}' submitted successfully.", jobId);
            return jobId;
        } catch (Exception e) {
            log.error("Failed to launch Spark job '{}'. Reason: {}", jobId, e.getMessage());
            throw new BusinessException("Spark job submission failed: " + e.getMessage());
        }
    }
}
