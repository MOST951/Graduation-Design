package com.weibo.web.controller;

import com.weibo.common.model.ResponseResult;
import com.weibo.web.entity.SystemLog;
import com.weibo.web.entity.User;
import com.weibo.web.repository.LogRepository;
import com.weibo.web.repository.UserRepository;
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

@RestController
@RequestMapping("/admin")
public class AdminController {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private LogRepository logRepository;

    @Autowired
    private StringRedisTemplate redisTemplate;

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
}
