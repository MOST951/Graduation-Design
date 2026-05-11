package com.weibo.web.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/dashboard")
public class DashboardController {

    @GetMapping("/summary")
    public String getSummary() {
        return "Dashboard Summary"; // Placeholder
    }

    @GetMapping("/charts")
    public String getCharts() {
        return "Chart Data"; // Placeholder
    }

    @GetMapping("/alerts")
    public String getAlerts() {
        return "Alerts Data"; // Placeholder
    }

    @GetMapping("/metrics")
    public String getMetrics() {
        return "Metrics Data"; // Placeholder
    }
}
