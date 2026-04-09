package com.weibo.web.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin")
public class AdminController {

    @GetMapping("/users")
    public String getUsers() {
        return "Users List"; // Placeholder
    }

    @GetMapping("/system-info")
    public String getSystemInfo() {
        return "System Info"; // Placeholder
    }

    @GetMapping("/logs")
    public String getLogs() {
        return "Logs Data"; // Placeholder
    }

    @PostMapping("/clear-cache")
    public String clearCache() {
        return "Cache Cleared"; // Placeholder
    }
}
