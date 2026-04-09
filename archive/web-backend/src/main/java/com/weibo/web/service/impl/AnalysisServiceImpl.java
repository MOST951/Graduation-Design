package com.weibo.web.service.impl;

import com.weibo.common.exception.BusinessException;
import com.weibo.web.dto.request.AnalysisRequest;
import com.weibo.web.dto.response.AnalysisResponse;
import com.weibo.web.dto.response.PageResponse;
import com.weibo.web.dto.response.SentimentTrendDTO;
import com.weibo.web.entity.SentimentResult;
import com.weibo.web.mapper.SentimentResultMapper;
import com.weibo.web.repository.ResultRepository;
import com.weibo.web.service.AnalysisService;
import com.weibo.web.service.SparkService;
import com.weibo.web.utils.ExcelExportUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 情感分析服务的完整实现。
 * <p>
 * 特性:
 * - 异步提交Spark作业进行批量分析。
 * - 使用Redis缓存分析结果和趋势数据。
 * - 提供分页查询和结果导出功能。
 * - 统一的异常处理和日志记录。
 */
@Slf4j
@Service
public class AnalysisServiceImpl implements AnalysisService {

    private final ResultRepository resultRepository;
    private final SparkService sparkService;
    private final SentimentResultMapper resultMapper;

    @Autowired
    public AnalysisServiceImpl(ResultRepository resultRepository, SparkService sparkService, SentimentResultMapper resultMapper) {
        this.resultRepository = resultRepository;
        this.sparkService = sparkService;
        this.resultMapper = resultMapper;
    }

    @Override
    @Async("taskExecutor") // 使用在AsyncConfig中定义的线程池
    public void batchAnalyze(AnalysisRequest request) {
        log.info("Submitting batch analysis job for task ID: {}", request.getTaskId());
        try {
            // 提交Spark作业，并传递必要的参数 (转换为String)
            sparkService.submitJob("sentiment-analysis-job", String.valueOf(request.getTaskId()));
            log.info("Successfully submitted Spark job for task ID: {}", request.getTaskId());
        } catch (Exception e) {
            log.error("Failed to submit Spark job for task ID: {}. Reason: {}", request.getTaskId(), e.getMessage());
            // 这里可以添加失败处理逻辑，例如更新任务状态为失败
        }
    }

    @Override
    @Cacheable(value = "analysis_results", key = "#taskId + '_' + #pageable.pageNumber + '_' + #pageable.pageSize")
    public PageResponse<AnalysisResponse> getResults(Long taskId, Pageable pageable) {
        log.info("Fetching analysis results for task ID: {} with pagination: {}", taskId, pageable);
        Page<SentimentResult> page = resultRepository.findByTaskId(taskId, pageable);
        List<AnalysisResponse> content = page.getContent().stream()
                .map(resultMapper::toDto)
                .collect(Collectors.toList());
        return new PageResponse<>(content, page.getNumber(), page.getSize(), page.getTotalElements(), page.getTotalPages());
    }

    @Override
    @Cacheable(value = "trend_analysis", key = "#taskId")
    public List<SentimentTrendDTO> getTrendAnalysis(Long taskId) {
        log.info("Performing trend analysis for task ID: {}", taskId);
        return resultRepository.getSentimentTrendByTaskId(taskId);
    }

    @Override
    public byte[] exportResults(Long taskId, String format) {
        log.info("Exporting results for task ID: {} in {} format", taskId, format);
        List<SentimentResult> results = resultRepository.findAllByTaskId(taskId);

        try {
            switch (format.toLowerCase()) {
                case "excel":
                    return ExcelExportUtils.exportToExcel(results);
                // case "csv":
                // return CsvExportUtils.exportToCsv(results); // 未来可以添加
                default:
                    throw new BusinessException("Unsupported export format: " + format);
            }
        } catch (IOException e) {
            log.error("Failed to export results for task ID: {}. Format: {}. Reason: {}", taskId, format, e.getMessage());
            throw new BusinessException("Export failed: " + e.getMessage());
        }
    }
}
