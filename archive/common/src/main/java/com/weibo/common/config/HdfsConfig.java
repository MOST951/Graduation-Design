package com.weibo.common.config;

import lombok.Data;
import org.apache.hadoop.conf.Configuration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * HDFS 配置类，用于加载 HDFS 连接信息。
 */
@Data
@Component
@ConfigurationProperties(prefix = "hdfs")
public class HdfsConfig {

    private String namenodeUrl;
    private String username;
    private String basePath;

    /**
     * 根据当前配置构建一个 Hadoop Configuration 对象。
     * @return A new Hadoop Configuration object.
     */
    public Configuration getConfiguration() {
        Configuration conf = new Configuration();
        conf.set("fs.defaultFS", namenodeUrl);
        if (username != null) {
            System.setProperty("HADOOP_USER_NAME", username);
        }
        return conf;
    }
}
