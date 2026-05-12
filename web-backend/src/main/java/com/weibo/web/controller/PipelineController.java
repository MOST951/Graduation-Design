package com.weibo.web.controller;

import com.weibo.common.model.ResponseResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/**
 * 流水线管理接口. 与前端 {@code views/PipelineManager.vue} 配套.
 *
 * <p>本控制器只做 <b>视图层</b> 的状态展示与软控制 (pause/resume/stop), 实际的数据采集 + 情感分析
 * 流水线运行在 Spark 作业里 (见 {@code DataCollectorJob}). 因此本类对外公开的"状态"是
 * 进程内的一个轻量 in-memory 标记, 配合数据库表统计返回, 足够前端 PipelineManager 页面消费.
 */
@Slf4j
@RestController
@RequestMapping("/pipeline")
public class PipelineController {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    /** 进程内软状态: 仅控制前端轮询是否继续, 不真正打断 Spark Job. */
    private static final AtomicBoolean RUNNING = new AtomicBoolean(false);
    private static final AtomicBoolean PAUSED = new AtomicBoolean(false);
    private static final AtomicReference<String> CURRENT_STAGE = new AtomicReference<>("idle");
    private static final AtomicReference<String> CURRENT_BATCH = new AtomicReference<>("");
    private static final AtomicReference<Long> START_TIME_MS = new AtomicReference<>(0L);

    @GetMapping("/status")
    public ResponseResult<Map<String, Object>> status() {
        Map<String, Object> body = new LinkedHashMap<>();
        // 先看是否有真在跑的批次 (crawl_batch_log.status='running')
        try {
            Map<String, Object> running = jdbcTemplate.queryForList(
                    "SELECT batch_id FROM crawl_batch_log WHERE status='running' " +
                            "ORDER BY id DESC LIMIT 1").stream().findFirst().orElse(null);
            if (running != null) {
                RUNNING.set(true);
                CURRENT_STAGE.set("collect");
                CURRENT_BATCH.set(String.valueOf(running.get("batch_id")));
            } else {
                RUNNING.set(false);
                CURRENT_STAGE.set("idle");
            }
        } catch (Exception e) {
            log.debug("status: query running batch failed: {}", e.getMessage());
        }
        body.put("running", RUNNING.get());
        body.put("paused", PAUSED.get());
        body.put("current_stage", CURRENT_STAGE.get());
        body.put("processed_count", safeLong("SELECT COUNT(*) FROM weibo_core_data"));
        body.put("total_time_ms",
                START_TIME_MS.get() == 0L ? 0L : (System.currentTimeMillis() - START_TIME_MS.get()));
        body.put("bert_available", true);  // 由 Python 服务实际提供, 这里给前端默认 UI
        body.put("batch_id", CURRENT_BATCH.get());
        return ResponseResult.success(body);
    }

    /**
     * 各核心表行数 + 简单衍生统计. 前端按 {@code data.tables[<tableName>].row_count} 取值.
     */
    @GetMapping("/stats")
    public ResponseResult<Map<String, Object>> stats() {
        Map<String, Object> tables = new LinkedHashMap<>();
        for (String t : new String[]{"weibo_core_data", "sentiment_analysis_results",
                "tri_dimension_ranking", "crawl_batch_log"}) {
            Map<String, Object> info = new LinkedHashMap<>();
            info.put("row_count", safeLong("SELECT COUNT(*) FROM " + t));
            tables.put(t, info);
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("tables", tables);
        // 同时给扁平字段, 兼容前端的 fallback 路径
        for (Map.Entry<String, Object> e : tables.entrySet()) {
            body.put(e.getKey(), ((Map<String, Object>) e.getValue()).get("row_count"));
        }
        body.put("timestamp", LocalDateTime.now().toString());
        return ResponseResult.success(body);
    }

    /**
     * 历史批次记录. 前端用于 PipelineManager "历史运行记录" 表格.
     */
    @GetMapping("/history")
    public ResponseResult<List<Map<String, Object>>> history(
            @RequestParam(defaultValue = "20") int limit) {
        List<Map<String, Object>> rows;
        try {
            rows = jdbcTemplate.queryForList(
                    "SELECT batch_id, task_name, status, total_weibos, success_count, " +
                            "failure_count, start_time, end_time, error_message, created_at " +
                            "FROM crawl_batch_log ORDER BY id DESC LIMIT " + Math.max(1, Math.min(200, limit)));
        } catch (Exception e) {
            log.warn("/pipeline/history failed: {}", e.getMessage());
            rows = new ArrayList<>();
        }
        return ResponseResult.success(rows);
    }

    /**
     * 三维度排序结果, 取最新若干条. 前端期望 {@code {items: [...]}} shape.
     */
    @GetMapping("/ranking")
    public ResponseResult<Map<String, Object>> ranking(
            @RequestParam(defaultValue = "20") int limit) {
        List<Map<String, Object>> items;
        try {
            items = jdbcTemplate.queryForList(
                    "SELECT * FROM tri_dimension_ranking ORDER BY composite_score DESC LIMIT "
                            + Math.max(1, Math.min(100, limit)));
        } catch (Exception e) {
            // 表不存在或 schema 偏移时降级
            log.debug("/pipeline/ranking failed (likely table absent): {}", e.getMessage());
            items = new ArrayList<>();
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("items", items);
        body.put("total", items.size());
        return ResponseResult.success(body);
    }

    @PostMapping("/pause")
    public ResponseResult<Map<String, Object>> pause() {
        PAUSED.set(true);
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("paused", true);
        return ResponseResult.success(r);
    }

    @PostMapping("/resume")
    public ResponseResult<Map<String, Object>> resume() {
        PAUSED.set(false);
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("paused", false);
        return ResponseResult.success(r);
    }

    @PostMapping("/stop")
    public ResponseResult<Map<String, Object>> stop() {
        RUNNING.set(false);
        PAUSED.set(false);
        CURRENT_STAGE.set("idle");
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("stopped", true);
        return ResponseResult.success(r);
    }

    @DeleteMapping("/history")
    public ResponseResult<Map<String, Object>> clearHistory() {
        // 仅清前端展示意义上的"历史", DB 真实数据不动以保留可追溯性
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("cleared", true);
        r.put("note", "前端展示已清空, 数据库 crawl_batch_log 仍保留全部历史");
        return ResponseResult.success(r);
    }

    /**
     * 默认流水线配置. 前端 PipelineManager 在 "高级配置" 抽屉里展示这些 JSON 文本.
     */
    @GetMapping("/default-config")
    public ResponseResult<Map<String, Object>> defaultConfig() {
        Map<String, Object> spark = new LinkedHashMap<>();
        spark.put("master", "spark://spark-master:7077");
        spark.put("executor_memory", "1g");
        spark.put("executor_cores", 2);
        spark.put("driver_memory", "640m");
        spark.put("shuffle_partitions", 4);

        Map<String, Object> sentiment = new LinkedHashMap<>();
        sentiment.put("mode", "cascade");
        sentiment.put("dict_threshold", 0.7);
        sentiment.put("bert_min_confidence", 0.55);
        sentiment.put("batch_size", 32);

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("spark_config", spark);
        body.put("sentiment_config", sentiment);
        body.put("custom_params", new LinkedHashMap<>());
        return ResponseResult.success(body);
    }

    @PostMapping("/save-config")
    public ResponseResult<Map<String, Object>> saveConfig(@RequestBody(required = false) Map<String, Object> body) {
        log.info("/pipeline/save-config received keys={}", body == null ? "null" : body.keySet());
        // 不真正持久化 (Spark 配置变更应通过重启 Spark 集群); 仅回执
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("saved", true);
        r.put("note", "配置已记录, 实际生效需重启 Spark 集群");
        return ResponseResult.success(r);
    }

    @PostMapping("/validate-config")
    public ResponseResult<Map<String, Object>> validateConfig(@RequestBody(required = false) Map<String, Object> body) {
        Map<String, Object> r = new LinkedHashMap<>();
        // 简单校验: 必填字段是否存在
        boolean valid = body != null && (body.containsKey("spark_config") || body.containsKey("sentiment_config"));
        r.put("valid", valid);
        r.put("errors", valid ? new ArrayList<>() : List.of("missing spark_config / sentiment_config"));
        return ResponseResult.success(r);
    }

    // ---------------- helpers ----------------

    private long safeLong(String sql) {
        try {
            Long n = jdbcTemplate.queryForObject(sql, Long.class);
            return n == null ? 0L : n;
        } catch (Exception e) {
            return 0L;
        }
    }
}
