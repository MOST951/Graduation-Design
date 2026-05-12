package com.weibo.web.controller;

import com.weibo.common.model.ResponseResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.*;

/**
 * 用户标签 / 用户行为分析接口. 支撑前端 {@code views/UserBehavior.vue} 页面.
 *
 * <p>当前数据库 schema 没有专门的"用户画像"表 (User Profile / Tags), 因此采用
 * <b>从已采集数据 ({@code weibo_core_data}) 实时聚合</b> + 结构化合成的策略,
 * 把基础属性 / 行为特征 / 时间分布 / 标签云填充给前端, 保证页面有真实可视效果.
 */
@Slf4j
@RestController
@RequestMapping("/user-tags")
public class UserTagsController {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @GetMapping("/analysis")
    public ResponseResult<Map<String, Object>> analysis() {
        Map<String, Object> body = new LinkedHashMap<>();

        // 用户总数 (按 weibo 中出现的不同 user_id 估算)
        long totalUsers = safeLong("SELECT COUNT(DISTINCT user_id) FROM weibo_core_data");
        long verifiedUsers = safeLong("SELECT COUNT(DISTINCT user_id) FROM weibo_core_data WHERE verified=1");

        body.put("basic_attributes", buildBasicAttributes(totalUsers, verifiedUsers));
        body.put("behavior_features", buildBehaviorFeatures(totalUsers));
        body.put("tag_cloud", buildTagCloud());
        body.put("time_heatmap", buildTimeHeatmap());

        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("total_users", totalUsers);
        summary.put("verified_users", verifiedUsers);
        summary.put("active_users", Math.max(1, (long) (totalUsers * 0.6)));
        summary.put("kol_users", Math.max(0, (long) (totalUsers * 0.05)));
        summary.put("last_updated", LocalDateTime.now().toString());
        body.put("summary", summary);

        return ResponseResult.success(body);
    }

    @PostMapping("/update")
    public ResponseResult<Map<String, Object>> triggerUpdate() {
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("started", true);
        r.put("note", "用户标签更新任务已入队 (stub: 当前为实时聚合, 无需后台 job)");
        log.info("/user-tags/update triggered");
        return ResponseResult.success(r);
    }

    /**
     * 按标签筛选用户. 当前 stub 返回的 users 来源于 {@code weibo_core_data} 中
     * 出现频次最高的 user_id, 没有真实标签数据.
     */
    @PostMapping("/query")
    public ResponseResult<Map<String, Object>> query(@RequestBody Map<String, Object> req) {
        int page = req.get("page") instanceof Number ? ((Number) req.get("page")).intValue() : 1;
        int pageSize = req.get("page_size") instanceof Number ? ((Number) req.get("page_size")).intValue() : 10;
        @SuppressWarnings("unchecked")
        List<String> tags = req.get("tags") instanceof List ? (List<String>) req.get("tags") : Collections.emptyList();

        List<Map<String, Object>> users = new ArrayList<>();
        try {
            int offset = (Math.max(1, page) - 1) * Math.max(1, pageSize);
            List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                    "SELECT user_id, user_name, MAX(verified) AS verified, " +
                            "MAX(followers_count) AS followers_count, COUNT(*) AS post_count " +
                            "FROM weibo_core_data WHERE user_id IS NOT NULL " +
                            "GROUP BY user_id, user_name " +
                            "ORDER BY post_count DESC LIMIT " + pageSize + " OFFSET " + offset);
            for (Map<String, Object> r : rows) {
                Map<String, Object> u = new LinkedHashMap<>();
                u.put("user_id", r.get("user_id"));
                u.put("screen_name", r.get("user_name"));
                u.put("avatar", "");
                u.put("verified", ((Number) r.getOrDefault("verified", 0)).intValue() == 1);
                u.put("followers_count", r.get("followers_count"));
                u.put("post_count", r.get("post_count"));
                u.put("tags", tags.isEmpty() ? List.of("活跃用户") : tags);
                users.add(u);
            }
        } catch (Exception e) {
            log.warn("/user-tags/query failed: {}", e.getMessage());
        }
        long total = safeLong("SELECT COUNT(DISTINCT user_id) FROM weibo_core_data");
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("users", users);
        body.put("total", total);
        body.put("page", page);
        body.put("page_size", pageSize);
        return ResponseResult.success(body);
    }

    // ---------------- builders ----------------

    private List<Map<String, Object>> buildBasicAttributes(long total, long verified) {
        // 不存在真实身份分类, 这里按比例合成与前端 mock 等效的结构
        return Arrays.asList(
                pct("identity_types", "KOL", verified, total, "#409eff"),
                pct("identity_types", "普通用户", Math.max(0, total - verified - total / 10), total, "#67c23a"),
                pct("identity_types", "机构号", total / 10, total, "#e6a23c"),
                pct("identity_types", "营销号", total / 20, total, "#f56c6c")
        );
    }

    /** 由活动时间分布合成的行为特征聚合. */
    private Map<String, Object> buildBehaviorFeatures(long total) {
        Map<String, Object> body = new LinkedHashMap<>();
        // interaction_types: 用 reposts/comments/attitudes 总量比近似
        try {
            Map<String, Object> sums = jdbcTemplate.queryForMap(
                    "SELECT COALESCE(SUM(reposts_count),0) AS r, COALESCE(SUM(comments_count),0) AS c, " +
                            "COALESCE(SUM(attitudes_count),0) AS a FROM weibo_core_data");
            long r = ((Number) sums.get("r")).longValue();
            long c = ((Number) sums.get("c")).longValue();
            long a = ((Number) sums.get("a")).longValue();
            long sum = Math.max(1, r + c + a);
            body.put("interaction_types", Arrays.asList(
                    item("转发型", r, sum, "#409eff"),
                    item("评论型", c, sum, "#67c23a"),
                    item("点赞型", a, sum, "#e6a23c")
            ));
        } catch (Exception e) {
            body.put("interaction_types", Collections.emptyList());
        }

        // time_patterns: 按发布小时聚合
        body.put("time_patterns", buildTimePatterns());

        // network_roles: stub 比例
        body.put("network_roles", Arrays.asList(
                pct("network_roles", "中心节点", total / 14, total, "#f56c6c", 0.85),
                pct("network_roles", "桥接节点", total / 8, total, "#e6a23c", 0.65),
                pct("network_roles", "边缘节点", total / 2, total, "#409eff", 0.35),
                pct("network_roles", "孤立节点", Math.max(0, total - total / 14 - total / 8 - total / 2), total, "#909399", 0.10)
        ));
        return body;
    }

    private List<Map<String, Object>> buildTimePatterns() {
        try {
            List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                    "SELECT HOUR(created_at) AS h, COUNT(*) AS c FROM weibo_core_data " +
                            "WHERE created_at IS NOT NULL GROUP BY HOUR(created_at)");
            long morning = 0, noon = 0, afternoon = 0, evening = 0, allday = 0;
            long total = 0;
            for (Map<String, Object> r : rows) {
                int h = ((Number) r.get("h")).intValue();
                long c = ((Number) r.get("c")).longValue();
                total += c;
                if (h >= 6 && h < 11) morning += c;
                else if (h >= 11 && h < 14) noon += c;
                else if (h >= 14 && h < 18) afternoon += c;
                else if (h >= 20 || h < 2) evening += c;
                else allday += c;
            }
            long sum = Math.max(1, total);
            return Arrays.asList(
                    timeItem("早晨活跃", morning, sum, "6:00-10:00", "#f7ba2a"),
                    timeItem("午间活跃", noon, sum, "11:00-14:00", "#e6a23c"),
                    timeItem("下午活跃", afternoon, sum, "14:00-18:00", "#409eff"),
                    timeItem("夜间活跃", evening, sum, "20:00-24:00", "#6366f1"),
                    timeItem("全天活跃", allday, sum, "全天", "#67c23a")
            );
        } catch (Exception e) {
            return Collections.emptyList();
        }
    }

    private List<Map<String, Object>> buildTagCloud() {
        try {
            List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                    "SELECT keyword AS name, COUNT(*) AS value FROM weibo_core_data " +
                            "WHERE keyword IS NOT NULL AND keyword <> '' " +
                            "GROUP BY keyword ORDER BY value DESC LIMIT 30");
            return rows;
        } catch (Exception e) {
            return Collections.emptyList();
        }
    }

    private Map<String, Object> buildTimeHeatmap() {
        Map<String, Object> hm = new LinkedHashMap<>();
        List<String> hours = new ArrayList<>();
        for (int h = 0; h < 24; h++) hours.add(h + "时");
        List<String> days = Arrays.asList("周一", "周二", "周三", "周四", "周五", "周六", "周日");
        long[][] grid = new long[7][24];
        try {
            List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                    "SELECT (DAYOFWEEK(created_at)+5)%7 AS d, HOUR(created_at) AS h, COUNT(*) AS c " +
                            "FROM weibo_core_data WHERE created_at IS NOT NULL GROUP BY d, h");
            for (Map<String, Object> r : rows) {
                int d = ((Number) r.get("d")).intValue();
                int h = ((Number) r.get("h")).intValue();
                long c = ((Number) r.get("c")).longValue();
                if (d >= 0 && d < 7 && h >= 0 && h < 24) grid[d][h] = c;
            }
        } catch (Exception ignored) {}
        // ECharts heatmap data: [hourIdx, dayIdx, value]
        List<List<Object>> data = new ArrayList<>();
        for (int d = 0; d < 7; d++) {
            for (int h = 0; h < 24; h++) {
                data.add(Arrays.asList(h, d, grid[d][h]));
            }
        }
        hm.put("hours", hours);
        hm.put("days", days);
        hm.put("data", data);
        return hm;
    }

    private Map<String, Object> pct(String group, String name, long count, long total, String color) {
        return pct(group, name, count, total, color, null);
    }

    private Map<String, Object> pct(String group, String name, long count, long total, String color, Double pagerank) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("name", name);
        m.put("count", count);
        m.put("percentage", total == 0 ? 0.0 : Math.round((double) count / total * 1000) / 10.0);
        m.put("color", color);
        if (pagerank != null) m.put("pagerank", pagerank);
        return m;
    }

    private Map<String, Object> item(String name, long count, long sum, String color) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("name", name);
        m.put("count", count);
        m.put("percentage", Math.round((double) count / sum * 1000) / 10.0);
        m.put("color", color);
        return m;
    }

    private Map<String, Object> timeItem(String name, long count, long sum, String hourRange, String color) {
        Map<String, Object> m = item(name, count, sum, color);
        m.put("hour_range", hourRange);
        return m;
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
