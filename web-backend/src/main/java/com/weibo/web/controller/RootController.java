package com.weibo.web.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

/**
 * 根路径重定向到 Swagger API 文档 (论文 6.2.2 图6-9).
 */
@Controller
public class RootController {

    @GetMapping("/")
    public String root() {
        return "redirect:/swagger-ui.html";
    }
}
