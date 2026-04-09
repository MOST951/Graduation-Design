package com.weibo.web.repository;

import com.weibo.web.dto.response.SentimentTrendDTO;
import com.weibo.web.entity.SentimentResult;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * 情感分析结果的仓库接口。
 */
@Repository
public interface ResultRepository extends JpaRepository<SentimentResult, Long> {

    /**
     * 根据任务ID分页查询结果。
     */
    Page<SentimentResult> findByTaskId(Long taskId, Pageable pageable);

    /**
     * 根据任务ID查询所有结果，用于导出。
     */
    List<SentimentResult> findAllByTaskId(Long taskId);

    /**
     * 按天聚合情感数据，用于趋势分析。
     * 注意：DATE()函数在不同数据库中可能需要调整（例如，在H2中使用CAST(r.createdAt AS DATE)）。
     */
    @Query("SELECT new com.weibo.web.dto.response.SentimentTrendDTO(CAST(r.createdAt AS java.time.LocalDate), r.sentiment, COUNT(r)) " +
           "FROM SentimentResult r WHERE r.task.id = :taskId " +
           "GROUP BY CAST(r.createdAt AS java.time.LocalDate), r.sentiment " +
           "ORDER BY CAST(r.createdAt AS java.time.LocalDate) ASC")
    List<SentimentTrendDTO> getSentimentTrendByTaskId(@Param("taskId") Long taskId);
}
