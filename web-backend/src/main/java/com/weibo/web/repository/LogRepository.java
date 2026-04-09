package com.weibo.web.repository;

import com.weibo.web.entity.SystemLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Log Repository
 */
@Repository
public interface LogRepository extends JpaRepository<SystemLog, Long> {
    // JpaRepository provides all necessary CRUD operations.
    // Custom query methods can be added here if needed in the future.
}
