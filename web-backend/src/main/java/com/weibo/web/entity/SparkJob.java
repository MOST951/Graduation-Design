package com.weibo.web.entity;

import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import javax.persistence.*;
import java.time.LocalDateTime;

/**
 * 用于持久化Spark作业状态的JPA实体。
 */
@Data
@Entity
@Table(name = "spark_jobs")
public class SparkJob {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false)
    private String jobId;

    @Column(nullable = false)
    private String jobName;

    @Column(nullable = false)
    private String status;

    @CreationTimestamp
    @Column(updatable = false)
    private LocalDateTime submitTime;

    private LocalDateTime finishTime;

    private String arguments;
}
