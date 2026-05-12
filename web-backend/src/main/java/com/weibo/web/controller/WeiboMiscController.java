package com.weibo.web.controller;

import com.weibo.common.model.ResponseResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 杂项接口集合: 三维度排序 ({@code POST /weibo/rank/tri}) 与 传播网络 ({@code GET /propagation/network}).
 *
 * <p>这两个接口在前端属于"轻量后端 + 前端可视"的设计, 本类把它们集中在一起以减少 controller 数量.
 */
@Slf4j
@RestController
public class WeiboMiscController {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    /**
     * 三维度热点排序. 前端 {@code views/TriDimensionAnalysis.vue} 在用户调整权重后调用此接口,
     * 把传入的若干条候选数据按 {@code α·sentiment + β·heat + γ·timeliness} 重排返回.
     */
    @PostMapping("/weibo/rank/tri")
    public ResponseResult<Map<String, Object>> rankTri(@RequestBody Map<String, Object> req) {
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> items = req.get("data") instanceof List
                ? (List<Map<String, Object>>) req.get("data") : new ArrayList<>();
        double alpha = num(req.get("sentiment_weight"), 0.4);
        double beta = num(req.get("heat_weight"), 0.4);
        double gamma = num(req.get("time_weight"), 0.2);
        // 归一化权重, 保证三者之和 = 1
        double sum = alpha + beta + gamma;
        if (sum <= 0) { alpha = 0.4; beta = 0.4; gamma = 0.2; sum = 1.0; }
        alpha /= sum; beta /= sum; gamma /= sum;

        for (Map<String, Object> r : items) {
            double s = num(r.get("sentiment_score"), 0.0);
            double h = num(r.get("popularity_score"), num(r.get("heat_score"), 0.0));
            // popularity_score 在 ranking 表中可能 >1, 简单归一化到 [0,1]
            if (h > 1.0) h = Math.min(1.0, h / 10.0);
            double t = num(r.get("time_decay"), num(r.get("timeliness_score"), 1.0));
            double composite = alpha * s + beta * h + gamma * t;
            r.put("composite_score", Math.round(composite * 10000) / 10000.0);
        }
        items.sort(Comparator.comparingDouble(
                (Map<String, Object> m) -> num(m.get("composite_score"), 0.0)).reversed());
        // 重新分配排名
        for (int i = 0; i < items.size(); i++) {
            items.get(i).put("ranking_position", i + 1);
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("items", items);
        body.put("weights", Map.of("sentiment", alpha, "heat", beta, "timeliness", gamma));
        body.put("total", items.size());
        return ResponseResult.success(body);
    }

    /**
     * 传播网络. 用 {@code weibo_core_data} 中按转发热度构造一个简化的星型/层级图,
     * 满足前端 {@code components/PropagationNetwork.vue} 的可视化需要.
     */
    @GetMapping("/propagation/network")
    public ResponseResult<Map<String, Object>> propagationNetwork(
            @RequestParam(defaultValue = "30") int max_nodes) {
        List<Map<String, Object>> nodes = new ArrayList<>();
        List<Map<String, Object>> edges = new ArrayList<>();
        try {
            int limit = Math.max(5, Math.min(100, max_nodes));
            List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                    "SELECT weibo_id, user_id, user_name, reposts_count, comments_count, attitudes_count " +
                            "FROM weibo_core_data WHERE reposts_count IS NOT NULL " +
                            "ORDER BY reposts_count DESC LIMIT " + limit);
            // 选取"种子"节点 (转发量 Top 5%) 作为中心
            int seedCount = Math.max(1, rows.size() / 10);
            for (int i = 0; i < rows.size(); i++) {
                Map<String, Object> r = rows.get(i);
                Map<String, Object> n = new LinkedHashMap<>();
                n.put("id", String.valueOf(r.get("weibo_id")));
                n.put("name", r.get("user_name"));
                n.put("symbolSize", Math.min(60.0,
                        10.0 + Math.log1p(((Number) r.getOrDefault("reposts_count", 0)).longValue()) * 5));
                n.put("category", i < seedCount ? 0 : 1); // 种子=0, 普通=1
                n.put("value", r.get("reposts_count"));
                nodes.add(n);
            }
            // 简化的边: 把每个非种子节点连到第 (i % seedCount) 个种子上
            for (int i = seedCount; i < rows.size(); i++) {
                Map<String, Object> e = new LinkedHashMap<>();
                e.put("source", nodes.get(i % seedCount).get("id"));
                e.put("target", nodes.get(i).get("id"));
                edges.add(e);
            }
        } catch (Exception e) {
            log.warn("/propagation/network failed: {}", e.getMessage());
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("nodes", nodes);
        body.put("edges", edges);
        body.put("links", edges); // 兼容 ECharts 命名
        body.put("categories", List.of(
                Map.of("name", "种子节点"),
                Map.of("name", "传播节点")));
        return ResponseResult.success(body);
    }

    private static double num(Object v, double def) {
        if (v instanceof Number) return ((Number) v).doubleValue();
        if (v == null) return def;
        try { return Double.parseDouble(String.valueOf(v)); } catch (NumberFormatException e) { return def; }
    }
}
