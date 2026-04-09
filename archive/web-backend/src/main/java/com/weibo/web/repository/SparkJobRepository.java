package com.weibo.web.repository;

import com.weibo.web.entity.SparkJob;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

/**
 * Spark作业实体的仓库接口。
 */
@Repository
public interface SparkJobRepository extends JpaRepository<SparkJob, Long> {

    Optional<SparkJob> findByJobId(String jobId);
}
