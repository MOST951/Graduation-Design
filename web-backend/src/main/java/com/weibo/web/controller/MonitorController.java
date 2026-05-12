package com.weibo.web.controller;

import com.weibo.common.model.ResponseResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 实时监控接口. 与前端 {@code views/RealTimeMonitor.vue} 配套, 5s 轮询.
 *
 * <p>响应 schema 是 RealTimeMonitor 的 {@code stats} reactive 对象的镜像:
 * sentiment_distribution / alert / keyword_ranking / system_status / alert_history.
 */
@Slf4j
@RestController
@RequestMapping("/monitor")
public class MonitorController {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @GetMapping("/statistics")
    public ResponseResult<Map<String, Object>> statistics() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("timestamp", LocalDateTime.now().toString());

        body.put("sentiment_distribution", buildSentimentDistribution());
        Map<String, Object> alert = buildAlert();
        body.put("alert", alert);
        body.put("keyword_ranking", buildKeywordRanking(10));
        body.put("system_status", buildSystemStatus());
        body.put("alert_history", buildAlertHistory(20));
        return ResponseResult.success(body);
    }

    // ---------------- builders ----------------

    private Map<String, Object> buildSentimentDistribution() {
        Map<String, Object> d = new LinkedHashMap<>();
        d.put("positive", 0);
        d.put("neutral", 0);
        d.put("negative", 0);
        d.put("total", 0);
        try {
            List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                    "SELECT sentiment_class, COUNT(*) AS cnt FROM sentiment_analysis_results " +
                            "WHERE analysis_time >= NOW() - INTERVAL 1 HOUR GROUP BY sentiment_class");
            // 兜底: 如果一小时窗口为空, 退回全表 (避免页面始终显示 0)
            if (rows.isEmpty()) {
                rows = jdbcTemplate.queryForList(
                        "SELECT sentiment_class, COUNT(*) AS cnt FROM sentiment_analysis_results GROUP BY sentiment_class");
            }
            long pos = 0, neu = 0, neg = 0;
            for (Map<String, Object> r : rows) {
                String cls = String.valueOf(r.get("sentiment_class"));
                long cnt = ((Number) r.get("cnt")).longValue();
                if ("positive".equalsIgnoreCase(cls)) pos = cnt;
                else if ("negative".equalsIgnoreCase(cls)) neg = cnt;
                else if ("neutral".equalsIgnoreCase(cls)) neu = cnt;
            }
            d.put("positive", pos);
            d.put("neutral", neu);
            d.put("negative", neg);
            d.put("total", pos + neu + neg);
        } catch (Exception e) {
            log.debug("buildSentimentDistribution failed: {}", e.getMessage());
        }
        return d;
    }

    private Map<String, Object> buildAlert() {
        Map<String, Object> a = new LinkedHashMap<>();
        a.put("level", "normal");
        a.put("message", "舆情正常");
        a.put("negative_ratio", 0.0);
        try {
            Map<String, Object> dist = buildSentimentDistribution();
            long total = ((Number) dist.get("total")).longValue();
            long neg = ((Number) dist.get("negative")).longValue();
            double ratio = total == 0 ? 0.0 : (double) neg / total;
            a.put("negative_ratio", ratio);
            String level;
            String msg;
            if (ratio >= 0.5) {
                level = "critical";
                msg = "重大负面舆情, 立即处理";
            } else if (ratio >= 0.3) {
                level = "high";
                msg = "高负面占比, 关注事态";
            } else if (ratio >= 0.15) {
                level = "warning";
                msg = "负面情绪上升";
            } else {
                level = "normal";
                msg = "舆情整体正常";
            }
            a.put("level", level);
            a.put("message", msg);
        } catch (Exception e) {
            log.debug("buildAlert failed: {}", e.getMessage());
        }
        return a;
    }

    private List<Map<String, Object>> buildKeywordRanking(int limit) {
        try {
            return jdbcTemplate.queryForList(
                    "SELECT keyword, COUNT(*) AS count FROM weibo_core_data " +
                            "WHERE keyword IS NOT NULL AND keyword <> '' " +
                            "GROUP BY keyword ORDER BY count DESC LIMIT " + Math.max(1, Math.min(50, limit)));
        } catch (Exception e) {
            log.debug("buildKeywordRanking failed: {}", e.getMessage());
            return new ArrayList<>();
        }
    }

    private Map<String, Object> buildSystemStatus() {
        Map<String, Object> s = new LinkedHashMap<>();
        // crawler_tasks
        Map<String, Object> crawler = new LinkedHashMap<>();
        crawler.put("active", safeLong("SELECT COUNT(*) FROM collection_task WHERE status='running'"));
        crawler.put("completed", safeLong("SELECT COUNT(*) FROM collection_task WHERE status='completed'"));
        crawler.put("failed", safeLong("SELECT COUNT(*) FROM collection_task WHERE status='failed'"));
        s.put("crawler_tasks", crawler);

        // spark_jobs (基于 crawl_batch_log; 表里 status enum=pending|running|completed|failed)
        Map<String, Object> spark = new LinkedHashMap<>();
        spark.put("pending", safeLong("SELECT COUNT(*) FROM crawl_batch_log WHERE status='pending'"));
        spark.put("running", safeLong("SELECT COUNT(*) FROM crawl_batch_log WHERE status='running'"));
        spark.put("completed", safeLong("SELECT COUNT(*) FROM crawl_batch_log WHERE status='completed'"));
        spark.put("failed", safeLong("SELECT COUNT(*) FROM crawl_batch_log WHERE status='failed'"));
        s.put("spark_jobs", spark);

        s.put("unprocessed_count",
                safeLong("SELECT COUNT(*) FROM weibo_core_data WHERE is_processed=0"));
        s.put("subscribed_keywords",
                safeLong("SELECT COUNT(DISTINCT keyword) FROM weibo_core_data WHERE keyword IS NOT NULL"));
        s.put("sse_clients", 0);
        return s;
    }

    /**
     * 预警历史. 这里没单独的告警表, 用 crawl_batch_log 中 status=failed 的记录做替代展示.
     */
    private List<Map<String, Object>> buildAlertHistory(int limit) {
        try {
            return jdbcTemplate.queryForList(
                    "SELECT batch_id AS event_id, status AS level, " +
                            "COALESCE(error_message, CONCAT('Batch ', batch_id, ' ', status)) AS message, " +
                            "created_at AS time " +
                            "FROM crawl_batch_log WHERE status='failed' " +
                            "ORDER BY id DESC LIMIT " + Math.max(1, Math.min(50, limit)));
        } catch (Exception e) {
            log.debug("buildAlertHistory failed: {}", e.getMessage());
            return new ArrayList<>();
        }
    }

    private long safeLong(String sql) {
        try {
            Long n = jdbcTemplate.queryForObject(sql, Long.class);
            return n == null ? 0L : n;
        } catch (Exception e) {
            return 0L;
        }
    }
}
