package com.weibo.web.controller;

import com.weibo.common.model.ResponseResult;
import com.weibo.web.repository.TaskRepository;
import com.weibo.web.repository.UserRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 仪表盘 / 全局概览接口. 与具体业务子模块解耦, 只做跨表的轻量聚合.
 */
@Slf4j
@RestController
@RequestMapping("/dashboard")
public class DashboardController {

    @Autowired
    private TaskRepository taskRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    /**
     * 仪表盘概览统计. 前端 {@code /api/dashboard/stats} 入口使用.
     */
    @GetMapping("/stats")
    public ResponseResult<Map<String, Object>> getStats() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("timestamp", LocalDateTime.now().toString());
        body.put("totalUsers", safeCount(userRepository::count));
        body.put("totalTasks", safeCount(taskRepository::count));
        body.put("totalWeibos", safeQueryCount("SELECT COUNT(*) FROM weibo_core_data"));
        body.put("totalAnalyzed", safeQueryCount("SELECT COUNT(*) FROM sentiment_analysis_results"));
        body.put("totalBatches", safeQueryCount("SELECT COUNT(*) FROM crawl_batch_log"));
        return ResponseResult.success(body);
    }

    /**
     * 情感分布: 前端 {@code MainLayout.checkAlerts()} 在每个页面上轮询此接口判断是否触发告警.
     * 数据源: {@code sentiment_analysis_results.sentiment_class}.
     */
    @GetMapping("/sentiment-distribution")
    public ResponseResult<Map<String, Object>> getSentimentDistribution() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("positive", 0);
        body.put("neutral", 0);
        body.put("negative", 0);
        body.put("total", 0);
        body.put("negativeRatio", 0.0);

        try {
            List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                    "SELECT sentiment_class, COUNT(*) AS cnt FROM sentiment_analysis_results " +
                            "GROUP BY sentiment_class");
            long pos = 0, neu = 0, neg = 0;
            for (Map<String, Object> r : rows) {
                String cls = String.valueOf(r.get("sentiment_class"));
                long cnt = ((Number) r.get("cnt")).longValue();
                if ("positive".equalsIgnoreCase(cls)) pos = cnt;
                else if ("negative".equalsIgnoreCase(cls)) neg = cnt;
                else if ("neutral".equalsIgnoreCase(cls)) neu = cnt;
            }
            long total = pos + neu + neg;
            body.put("positive", pos);
            body.put("neutral", neu);
            body.put("negative", neg);
            body.put("total", total);
            body.put("negativeRatio", total == 0 ? 0.0 : (double) neg / total);
        } catch (Exception e) {
            log.warn("Failed to query sentiment distribution: {}", e.getMessage());
        }
        return ResponseResult.success(body);
    }

    /**
     * 简化告警: 仅基于负向占比生成 0~1 条告警, 真实告警逻辑在 RealTimeMonitor 模块.
     */
    @GetMapping("/alerts")
    public ResponseResult<List<Map<String, Object>>> getAlerts() {
        List<Map<String, Object>> alerts = new java.util.ArrayList<>();
        try {
            Map<String, Object> dist = (Map<String, Object>) getSentimentDistribution().getData();
            double ratio = dist.get("negativeRatio") instanceof Number
                    ? ((Number) dist.get("negativeRatio")).doubleValue() : 0.0;
            if (ratio >= 0.3) {
                Map<String, Object> alert = new LinkedHashMap<>();
                alert.put("id", 1);
                alert.put("level", ratio >= 0.5 ? "critical" : "warning");
                alert.put("message", String.format("\u8d1f\u5411\u60c5\u611f\u5360\u6bd4 %.1f%%, \u8d85\u8fc7\u9608\u503c", ratio * 100));
                alert.put("timestamp", LocalDateTime.now().toString());
                alerts.add(alert);
            }
        } catch (Exception e) {
            log.warn("Failed to compute alerts: {}", e.getMessage());
        }
        return ResponseResult.success(alerts);
    }

    /** 系统运行指标: 简单 JVM 概览, 给前端仪表盘的健康卡片. */
    @GetMapping("/metrics")
    public ResponseResult<Map<String, Object>> getMetrics() {
        Runtime rt = Runtime.getRuntime();
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("timestamp", LocalDateTime.now().toString());
        body.put("jvmFreeMemoryMB", rt.freeMemory() / (1024 * 1024));
        body.put("jvmTotalMemoryMB", rt.totalMemory() / (1024 * 1024));
        body.put("jvmMaxMemoryMB", rt.maxMemory() / (1024 * 1024));
        body.put("availableProcessors", rt.availableProcessors());
        return ResponseResult.success(body);
    }

    @GetMapping("/summary")
    public ResponseResult<Map<String, Object>> getSummary() {
        return getStats();
    }

    @GetMapping("/charts")
    public ResponseResult<Map<String, Object>> getCharts() {
        return getSentimentDistribution();
    }

    // ---------------- helpers ----------------

    private long safeCount(java.util.function.LongSupplier supplier) {
        try { return supplier.getAsLong(); } catch (Exception e) { return 0L; }
    }

    private long safeQueryCount(String sql) {
        try {
            Long n = jdbcTemplate.queryForObject(sql, Long.class);
            return n == null ? 0L : n;
        } catch (Exception e) {
            log.debug("safeQueryCount failed for sql={}: {}", sql, e.getMessage());
            return 0L;
        }
    }
}
