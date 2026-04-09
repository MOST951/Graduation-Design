package com.weibo.web.repository;

import com.weibo.web.entity.CollectionTask;
import com.weibo.web.entity.User;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Task Repository
 */
@Repository
public interface TaskRepository extends JpaRepository<CollectionTask, Long> {

    /**
     * Find all tasks belonging to a specific user, with pagination.
     *
     * @param user the user who owns the tasks
     * @param pageable pagination information
     * @return a page of collection tasks
     */
    Page<CollectionTask> findByUser(User user, Pageable pageable);
}
