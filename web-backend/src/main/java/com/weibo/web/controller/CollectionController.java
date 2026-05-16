package com.weibo.web.controller;

import com.weibo.common.model.ResponseResult;
import com.weibo.web.entity.CollectionTask;
import com.weibo.web.repository.TaskRepository;
import com.weibo.web.service.SparkService;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 数据采集任务管理控制器。
 *
 * <p>负责将前端的采集请求落库 (collection_task), 并通过 spark-submit 调起
 * {@code com.weibo.collector.DataCollectorJob} 完成异步采集. 同时提供任务的
 * 分页列表 / 详情 / 删除 / 批量删除等基础 CRUD 接口, 以及一个聚合统计端点.
 */
@Slf4j
@RestController
@RequestMapping("/api/collection")
public class CollectionController {

    private static final String JAR_NAME = "data-collector.jar";
    private static final String MAIN_CLASS = "com.weibo.collector.DataCollectorJob";

    @Autowired
    private SparkService sparkService;

    @Autowired
    private TaskRepository taskRepository;

    // -------------------------------------------------------------- create

    @PostMapping("/tasks")
    public ResponseResult<TaskDto> createTask(@RequestBody CreateTaskRequest req) {
        // 1) 入库
        CollectionTask task = new CollectionTask();
        task.setTaskName(req.resolveName());
        task.setKeywords(req.resolveKeywordsAsString());
        task.setStatus("running");
        task.setStartTime(LocalDateTime.now());
        task = taskRepository.save(task);
        log.info("Persisted CollectionTask id={}, name={}, keywords={}",
                task.getId(), task.getTaskName(), task.getKeywords());

        // 2) 调起 Spark 作业 (keywords + taskId 作为参数)
        String keywordsArg = task.getKeywords();
        String taskIdArg = String.valueOf(task.getId());
        try {
            String jobId = sparkService.submitJob(JAR_NAME, MAIN_CLASS, keywordsArg, taskIdArg);
            log.info("Spark job submitted: taskId={}, jobId={}", task.getId(), jobId);
        } catch (Exception e) {
            // 落库的同时把任务标记为 failed, 让前端可见错误
            task.setStatus("failed");
            task.setEndTime(LocalDateTime.now());
            taskRepository.save(task);
            log.error("Spark submit failed for taskId={}: {}", task.getId(), e.getMessage(), e);
            throw new RuntimeException("Spark job submission failed: " + e.getMessage(), e);
        }
        return ResponseResult.success(TaskDto.from(task));
    }

    // -------------------------------------------------------------- list

    /**
     * 获取任务列表 (分页). 前端 {@code TaskListParams} 中可能带 page/pageSize/status/keyword 等过滤,
     * 这里做最小集合: 仅支持分页 + 状态过滤 + 关键词模糊.
     */
    @GetMapping("/tasks")
    public ResponseResult<Map<String, Object>> listTasks(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int pageSize,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String keyword
    ) {
        // 转换前端 status (waiting) 到 DB status (pending)
        String dbStatus = "waiting".equalsIgnoreCase(status) ? "pending" : status;
        Pageable pageable = PageRequest.of(Math.max(0, page - 1), Math.max(1, pageSize),
                Sort.by(Sort.Direction.DESC, "id"));

        Page<CollectionTask> p;
        if (dbStatus != null && !dbStatus.isEmpty()) {
            p = taskRepository.findAll(pageable);
            // JPA 简单内存过滤即可 (任务表数据量小); 如未来量大再加自定义查询
            List<CollectionTask> filtered = p.getContent().stream()
                    .filter(t -> dbStatus.equalsIgnoreCase(t.getStatus()))
                    .filter(t -> keyword == null || keyword.isEmpty()
                            || (t.getTaskName() != null && t.getTaskName().contains(keyword))
                            || (t.getKeywords() != null && t.getKeywords().contains(keyword)))
                    .collect(Collectors.toList());
            return ResponseResult.success(buildPage(filtered, filtered.size(), page, pageSize));
        }
        p = taskRepository.findAll(pageable);
        List<CollectionTask> content = p.getContent();
        if (keyword != null && !keyword.isEmpty()) {
            content = content.stream()
                    .filter(t -> (t.getTaskName() != null && t.getTaskName().contains(keyword))
                            || (t.getKeywords() != null && t.getKeywords().contains(keyword)))
                    .collect(Collectors.toList());
        }
        return ResponseResult.success(buildPage(content, p.getTotalElements(), page, pageSize));
    }

    private Map<String, Object> buildPage(List<CollectionTask> tasks, long total, int page, int pageSize) {
        List<TaskDto> list = tasks.stream().map(TaskDto::from).collect(Collectors.toList());
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("list", list);
        body.put("total", total);
        body.put("page", page);
        body.put("pageSize", pageSize);
        body.put("pages", (int) Math.ceil((double) total / Math.max(1, pageSize)));
        return body;
    }

    // -------------------------------------------------------------- detail / delete

    @GetMapping("/tasks/{id}")
    public ResponseResult<TaskDto> getTask(@PathVariable Long id) {
        return taskRepository.findById(id)
                .map(t -> ResponseResult.success(TaskDto.from(t)))
                .orElseGet(() -> {
                    ResponseResult<TaskDto> r = new ResponseResult<>();
                    r.setCode(404);
                    r.setMessage("Task not found: " + id);
                    return r;
                });
    }

    @DeleteMapping("/tasks/{id}")
    public ResponseResult<Void> deleteTask(@PathVariable Long id) {
        taskRepository.deleteById(id);
        return ResponseResult.success();
    }

    @PostMapping("/tasks/batch-delete")
    public ResponseResult<Map<String, Object>> batchDelete(@RequestBody BatchDeleteRequest req) {
        if (req == null || req.getIds() == null || req.getIds().isEmpty()) {
            ResponseResult<Map<String, Object>> r = new ResponseResult<>();
            r.setCode(400);
            r.setMessage("ids is empty");
            return r;
        }
        taskRepository.deleteAllById(req.getIds());
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("deleted", req.getIds().size());
        return ResponseResult.success(r);
    }

    // -------------------------------------------------------------- stats

    /**
     * 采集统计 (用于前端仪表盘 / 概览). 暂时只返回任务总数及按状态分桶,
     * 不依赖 crawl_batch_log 等其它表, 避免 schema 偏移.
     */
    @GetMapping("/stats")
    public ResponseResult<Map<String, Object>> stats() {
        List<CollectionTask> all = taskRepository.findAll();
        long total = all.size();
        Map<String, Long> byStatus = all.stream()
                .collect(Collectors.groupingBy(
                        t -> t.getStatus() == null ? "unknown" : t.getStatus(),
                        Collectors.counting()));
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("totalTasks", total);
        body.put("byStatus", byStatus);
        // 占位字段, 与前端 TaskStats 接口对齐
        body.put("totalCollected", 0);
        body.put("totalFailed", 0);
        body.put("successRate", total == 0 ? 0.0 : 1.0);
        body.put("speed", 0);
        body.put("platformDistribution", Collections.emptyList());
        body.put("hourlyStats", Collections.emptyList());
        return ResponseResult.success(body);
    }

    // ============================================================== DTOs

    /** 创建任务请求 (兼容前端 {@code CreateTaskRequest} 与历史直传 entity 两种 schema). */
    @Data
    public static class CreateTaskRequest {
        /** 前端字段: 任务名. */
        private String name;
        /** 兼容历史调用方: 直接传 taskName. */
        private String taskName;
        /** 前端字段: 关键词数组. */
        private List<String> keywords;
        /** 兼容历史调用方: 直接传 keywords 字符串. */
        private String keywordsRaw;

        /** 解析任务名: name 优先, 否则 taskName, 否则用关键词拼接生成. */
        public String resolveName() {
            if (name != null && !name.isEmpty()) return name;
            if (taskName != null && !taskName.isEmpty()) return taskName;
            String kws = resolveKeywordsAsString();
            return "task_" + (kws.length() > 30 ? kws.substring(0, 30) : kws);
        }

        /** 解析关键词为单一字符串 (空格分隔, 与 DataCollectorJob 的解析约定一致). */
        public String resolveKeywordsAsString() {
            if (keywords != null && !keywords.isEmpty()) {
                return String.join(" ", keywords);
            }
            return keywordsRaw == null ? "" : keywordsRaw;
        }
    }

    @Data
    public static class BatchDeleteRequest {
        private List<Long> ids;
    }

    /**
     * 响应 DTO: 把后端 {@link CollectionTask} 实体映射成前端期望的 schema (camelCase + 字段名对齐).
     * 这里只填能从 DB 直接获得的字段, 不查 crawl_batch_log 以避免跨表耦合.
     */
    @Data
    public static class TaskDto {
        private static final DateTimeFormatter ISO = DateTimeFormatter.ISO_LOCAL_DATE_TIME;

        private Long id;
        private String name;
        private List<String> keywords;
        /** 前端枚举: waiting | running | completed | failed | paused. */
        private String status;
        private int progress;
        private int collectedCount;
        private int failedCount;
        private Map<String, Object> config;
        private String createdAt;
        private String updatedAt;
        private String startedAt;
        private String completedAt;
        private String errorMessage;

        public static TaskDto from(CollectionTask t) {
            TaskDto dto = new TaskDto();
            dto.id = t.getId();
            dto.name = t.getTaskName();
            dto.keywords = parseKeywords(t.getKeywords());
            dto.status = mapStatus(t.getStatus());
            dto.progress = "completed".equals(dto.status) ? 100 : ("running".equals(dto.status) ? 50 : 0);
            dto.collectedCount = 0;
            dto.failedCount = 0;
            dto.config = Collections.emptyMap();
            dto.createdAt = fmt(t.getCreatedAt());
            dto.updatedAt = fmt(t.getUpdatedAt());
            dto.startedAt = fmt(t.getStartTime());
            dto.completedAt = fmt(t.getEndTime());
            return dto;
        }

        private static List<String> parseKeywords(String raw) {
            if (raw == null || raw.isEmpty()) return new ArrayList<>();
            return Arrays.stream(raw.split("[,\\s]+"))
                    .filter(s -> !s.isEmpty())
                    .collect(Collectors.toList());
        }

        /** DB 状态 → 前端枚举: pending → waiting; 其它原样透传. */
        private static String mapStatus(String dbStatus) {
            if (dbStatus == null) return "waiting";
            String s = dbStatus.toLowerCase();
            if ("pending".equals(s)) return "waiting";
            return s;
        }

        private static String fmt(LocalDateTime dt) {
            return dt == null ? null : dt.format(ISO);
        }
    }
}
