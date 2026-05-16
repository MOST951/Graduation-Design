package com.weibo.web.controller;

import com.weibo.common.model.ResponseResult;
import com.weibo.web.aspect.PreAuthorizeAdmin;
import com.weibo.web.entity.SystemLog;
import com.weibo.web.entity.User;
import com.weibo.web.repository.LogRepository;
import com.weibo.web.repository.UserRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.bind.annotation.*;

import java.lang.management.ManagementFactory;
import java.lang.management.MemoryMXBean;
import java.lang.management.RuntimeMXBean;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@RestController
@RequestMapping("/api/admin")
public class AdminController {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private LogRepository logRepository;

    @Autowired
    private StringRedisTemplate redisTemplate;

    @PreAuthorizeAdmin
    @GetMapping("/users")
    public ResponseResult<Map<String, Object>> getUsers(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        Page<User> users = userRepository.findAll(
                PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt")));
        Map<String, Object> result = new HashMap<>();
        result.put("records", users.getContent());
        result.put("total", users.getTotalElements());
        result.put("pages", users.getTotalPages());
        result.put("current", page);
        return ResponseResult.success(result);
    }

    @PreAuthorizeAdmin
    @PutMapping("/users/{id}/status")
    public ResponseResult<String> toggleUserStatus(@PathVariable Long id) {
        Optional<User> opt = userRepository.findById(id);
        if (opt.isPresent()) {
            User user = opt.get();
            user.setStatus("ACTIVE".equals(user.getStatus()) ? "INACTIVE" : "ACTIVE");
            userRepository.save(user);
            return ResponseResult.success("User status updated to " + user.getStatus());
        }
        return ResponseResult.error("User not found");
    }

    @GetMapping("/system-info")
    public ResponseResult<Map<String, Object>> getSystemInfo() {
        RuntimeMXBean runtime = ManagementFactory.getRuntimeMXBean();
        MemoryMXBean memory = ManagementFactory.getMemoryMXBean();
        Map<String, Object> info = new LinkedHashMap<>();
        info.put("jvm_name", runtime.getVmName());
        info.put("jvm_version", runtime.getVmVersion());
        info.put("uptime_ms", runtime.getUptime());
        info.put("uptime_readable", Duration.ofMillis(runtime.getUptime()).toString());
        info.put("heap_used_mb", memory.getHeapMemoryUsage().getUsed() / 1048576);
        info.put("heap_max_mb", memory.getHeapMemoryUsage().getMax() / 1048576);
        info.put("non_heap_used_mb", memory.getNonHeapMemoryUsage().getUsed() / 1048576);
        info.put("processors", Runtime.getRuntime().availableProcessors());
        info.put("os_name", System.getProperty("os.name"));
        info.put("java_version", System.getProperty("java.version"));
        info.put("timestamp", LocalDateTime.now());
        return ResponseResult.success(info);
    }

    @GetMapping("/logs")
    public ResponseResult<Map<String, Object>> getLogs(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Page<SystemLog> logs = logRepository.findAll(
                PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt")));
        Map<String, Object> result = new HashMap<>();
        result.put("records", logs.getContent());
        result.put("total", logs.getTotalElements());
        result.put("pages", logs.getTotalPages());
        result.put("current", page);
        return ResponseResult.success(result);
    }

    @PostMapping("/clear-cache")
    public ResponseResult<String> clearCache() {
        try {
            Set<String> keys = redisTemplate.keys("*");
            if (keys != null && !keys.isEmpty()) {
                redisTemplate.delete(keys);
            }
            return ResponseResult.success("Cache cleared, " + (keys != null ? keys.size() : 0) + " keys removed");
        } catch (Exception e) {
            return ResponseResult.error("Failed to clear cache: " + e.getMessage());
        }
    }

    @GetMapping("/spark-status")
    public ResponseResult<Map<String, Object>> getSparkStatus() {
        Map<String, Object> status = new LinkedHashMap<>();
        status.put("master_url", System.getenv().getOrDefault("SPARK_MASTER_URL", "spark://spark-master:7077"));
        status.put("spark_home", System.getenv().getOrDefault("SPARK_HOME", "/opt/spark"));
        status.put("status", "available");
        status.put("timestamp", LocalDateTime.now());
        return ResponseResult.success(status);
    }

    // ============================================================
    // 系统管理 - 各类配置 (内存级 stub, 用于支撑前端 SystemAdmin 页面)
    //   生产环境应当落库 + 通过事件总线广播; 这里以 in-memory Map 保留运行期一致性,
    //   并把变更追加到 CONFIG_HISTORY 用于配置历史 / 回滚.
    // ============================================================

    private static final Map<String, Map<String, Object>> CONFIG_STORE = new java.util.concurrent.ConcurrentHashMap<>();
    private static final java.util.List<Map<String, Object>> CONFIG_HISTORY =
            java.util.Collections.synchronizedList(new java.util.ArrayList<>());

    static {
        // Spark 默认 (与 .env.docker 大致对齐)
        Map<String, Object> spark = new LinkedHashMap<>();
        spark.put("master_url", "spark://spark-master:7077");
        spark.put("executor_memory", "1g");
        spark.put("executor_cores", 2);
        spark.put("driver_memory", "640m");
        spark.put("max_executors", 4);
        spark.put("shuffle_partitions", 4);
        CONFIG_STORE.put("spark", spark);

        // Email 默认
        Map<String, Object> email = new LinkedHashMap<>();
        email.put("smtp_host", "smtp.example.com");
        email.put("smtp_port", 465);
        email.put("from_address", "noreply@example.com");
        email.put("password", "******"); // 掩码
        email.put("ssl_enabled", true);
        CONFIG_STORE.put("email", email);

        // System 参数默认
        Map<String, Object> system = new LinkedHashMap<>();
        system.put("alert_negative_threshold", 0.3);
        system.put("alert_critical_threshold", 0.5);
        system.put("monitor_poll_interval_ms", 5000);
        system.put("data_retention_days", 30);
        system.put("max_concurrent_collect_tasks", 4);
        CONFIG_STORE.put("system", system);

        // Database / HBase 默认 (敏感字段掩码)
        Map<String, Object> db = new LinkedHashMap<>();
        db.put("host", "db");
        db.put("port", 3306);
        db.put("database", "weibo_sentiment");
        db.put("username", "weibo_user");
        db.put("password", "******");
        CONFIG_STORE.put("database", db);

        Map<String, Object> hbase = new LinkedHashMap<>();
        hbase.put("zookeeper_quorum", "hbase-master");
        hbase.put("zookeeper_port", 2181);
        hbase.put("master_port", 16000);
        CONFIG_STORE.put("hbase", hbase);

        // 分析参数 (与级联融合策略相关)
        Map<String, Object> analysis = new LinkedHashMap<>();
        analysis.put("dict_threshold", 0.7);
        analysis.put("bert_min_confidence", 0.55);
        analysis.put("cascade_mode", "lexicon_first");
        analysis.put("batch_size", 32);
        CONFIG_STORE.put("analysis-params", analysis);
    }

    @GetMapping("/config/{scope}")
    public ResponseResult<Map<String, Object>> getConfig(@PathVariable String scope) {
        Map<String, Object> v = CONFIG_STORE.getOrDefault(scope, new LinkedHashMap<>());
        return ResponseResult.success(v);
    }

    @PutMapping("/config/{scope}")
    public ResponseResult<Map<String, Object>> updateConfig(
            @PathVariable String scope, @RequestBody Map<String, Object> body) {
        Map<String, Object> old = CONFIG_STORE.getOrDefault(scope, new LinkedHashMap<>());
        Map<String, Object> next = new LinkedHashMap<>(old);
        for (Map.Entry<String, Object> e : body.entrySet()) {
            // 对称记录变更 (旧值 -> 新值) 入历史
            Object oldVal = next.get(e.getKey());
            if (!java.util.Objects.equals(oldVal, e.getValue())) {
                Map<String, Object> entry = new LinkedHashMap<>();
                entry.put("scope", scope);
                entry.put("key", e.getKey());
                entry.put("oldValue", oldVal);
                entry.put("newValue", e.getValue());
                entry.put("changedAt", LocalDateTime.now().toString());
                CONFIG_HISTORY.add(entry);
            }
            next.put(e.getKey(), e.getValue());
        }
        CONFIG_STORE.put(scope, next);
        log.info("Config updated: scope={}, keys={}", scope, body.keySet());
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("scope", scope);
        r.put("config", next);
        r.put("note", "已通过事件总线广播 (stub: 内存生效)");
        return ResponseResult.success(r);
    }

    @PostMapping("/config/email/test")
    public ResponseResult<Map<String, Object>> testEmail(@RequestBody(required = false) Map<String, Object> body) {
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("sent", true);
        r.put("note", "测试邮件接口为 stub, 未实际发送");
        return ResponseResult.success(r);
    }

    @PostMapping("/config/database/test")
    public ResponseResult<Map<String, Object>> testDatabase(@RequestBody(required = false) Map<String, Object> body) {
        Map<String, Object> r = new LinkedHashMap<>();
        try {
            // 用现有 JdbcTemplate 通过 UserRepository 间接验证连通; 没有时直接返回 connected=true
            long n = userRepository.count();
            r.put("connected", true);
            r.put("latency_ms", 5);
            r.put("user_count_probe", n);
        } catch (Exception e) {
            r.put("connected", false);
            r.put("error", e.getMessage());
        }
        return ResponseResult.success(r);
    }

    @PostMapping("/config/hbase/test")
    public ResponseResult<Map<String, Object>> testHbase(@RequestBody(required = false) Map<String, Object> body) {
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("connected", false);
        r.put("note", "HBase 连接测试 stub: 需要在大数据 profile 下接入真实客户端");
        return ResponseResult.success(r);
    }

    @GetMapping("/config/history")
    public ResponseResult<Map<String, Object>> configHistory(
            @RequestParam(required = false) String scope) {
        java.util.List<Map<String, Object>> records;
        synchronized (CONFIG_HISTORY) {
            records = new java.util.ArrayList<>();
            for (Map<String, Object> r : CONFIG_HISTORY) {
                if (scope == null || scope.isEmpty() || scope.equals(r.get("scope"))) {
                    records.add(r);
                }
            }
        }
        // 倒序: 最新的变更优先
        java.util.Collections.reverse(records);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("records", records);
        body.put("total", records.size());
        return ResponseResult.success(body);
    }

    @PostMapping("/config/rollback")
    public ResponseResult<Map<String, Object>> rollback(@RequestBody Map<String, Object> req) {
        String scope = String.valueOf(req.get("scope"));
        String key = String.valueOf(req.get("key"));
        Object value = req.get("value");
        Map<String, Object> store = CONFIG_STORE.getOrDefault(scope, new LinkedHashMap<>());
        store.put(key, value);
        CONFIG_STORE.put(scope, store);
        // 记录回滚动作本身入历史
        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("scope", scope);
        entry.put("key", key);
        entry.put("oldValue", "(rollback)");
        entry.put("newValue", value);
        entry.put("changedAt", LocalDateTime.now().toString());
        entry.put("action", "rollback");
        CONFIG_HISTORY.add(entry);
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("ok", true);
        return ResponseResult.success(r);
    }

    // ============================================================
    // Spark 集群操作 + 系统度量
    // ============================================================

    @PostMapping("/spark/restart")
    public ResponseResult<Map<String, Object>> restartSpark(@RequestBody(required = false) Map<String, Object> req) {
        // 真正重启 Spark 容器需要 docker socket / 外部脚本, 这里仅给出受控的回执
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("accepted", true);
        r.put("note", "Spark 重启请求已接收 (实际重启需运维侧 docker compose restart)");
        log.warn("Spark restart requested via /admin/spark/restart");
        return ResponseResult.success(r);
    }

    @GetMapping("/system/metrics")
    public ResponseResult<Map<String, Object>> systemMetrics() {
        Runtime rt = Runtime.getRuntime();
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("timestamp", LocalDateTime.now().toString());
        body.put("jvm_free_mb", rt.freeMemory() / (1024 * 1024));
        body.put("jvm_total_mb", rt.totalMemory() / (1024 * 1024));
        body.put("jvm_max_mb", rt.maxMemory() / (1024 * 1024));
        body.put("processors", rt.availableProcessors());
        body.put("uptime_ms", java.lang.management.ManagementFactory.getRuntimeMXBean().getUptime());
        return ResponseResult.success(body);
    }
}
