package com.weibo.common.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * Spark 配置类，用于从 application.yml 文件中加载 Spark 相关配置。
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "spark")
public class SparkConfig {

    private String master;
    private String appName;
    private String executorMemory;
    private String driverMemory;
    private int executorCores;

    // 本类现在仅作为 Spark 配置参数的载体，Web 后端通过 spark-submit 进程使用这些参数，
    // 不在当前 JVM 内直接依赖 Spark 的类，以避免运行时 NoClassDefFoundError。
}
