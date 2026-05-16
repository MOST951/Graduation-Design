package com.weibo.web.controller;

import org.springframework.boot.web.servlet.error.ErrorController;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestMapping;

import javax.servlet.http.HttpServletRequest;

/**
 * 自定义错误控制器: 当访问根路径 / (在 /api context-path 之外) 时,
 * 返回友好的 HTML 页面而非 Tomcat 默认 404.
 */
@Controller
public class CustomErrorController implements ErrorController {

    @RequestMapping("/error")
    public ResponseEntity<String> handleError(HttpServletRequest request) {
        Integer statusCode = (Integer) request.getAttribute("javax.servlet.error.status_code");
        if (statusCode == null) statusCode = 500;

        String html = "<!DOCTYPE html>\n"
                + "<html lang=\"zh-CN\"><head><meta charset=\"UTF-8\">\n"
                + "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
                + "<title>微博舆情分析系统 - Java 后端</title>\n"
                + "<style>\n"
                + "  *{margin:0;padding:0;box-sizing:border-box}\n"
                + "  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
                + "  min-height:100vh;display:flex;align-items:center;justify-content:center;"
                + "  background:linear-gradient(135deg,#667eea 0%,#764ba2 100%)}\n"
                + "  .card{background:#fff;border-radius:16px;padding:48px;max-width:520px;width:90%;"
                + "  box-shadow:0 20px 60px rgba(0,0,0,.15);text-align:center}\n"
                + "  .icon{font-size:48px;margin-bottom:16px}\n"
                + "  h1{font-size:24px;color:#1a1a2e;margin-bottom:8px}\n"
                + "  .desc{color:#666;font-size:14px;margin-bottom:24px;line-height:1.6}\n"
                + "  .status{display:inline-flex;align-items:center;gap:8px;padding:8px 20px;"
                + "  background:#e8f5e9;border-radius:20px;font-size:14px;color:#2e7d32;margin-bottom:24px}\n"
                + "  .dot{width:8px;height:8px;border-radius:50%;background:#4caf50;"
                + "  animation:pulse 2s infinite}\n"
                + "  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}\n"
                + "  .endpoints{text-align:left;background:#f8f9fa;border-radius:8px;padding:16px;"
                + "  margin-top:16px}\n"
                + "  .endpoints h3{font-size:13px;color:#999;margin-bottom:8px;text-transform:uppercase;"
                + "  letter-spacing:1px}\n"
                + "  .ep{display:flex;justify-content:space-between;padding:6px 0;"
                + "  border-bottom:1px solid #eee;font-size:13px}\n"
                + "  .ep:last-child{border:none}\n"
                + "  .ep a{color:#667eea;text-decoration:none}\n"
                + "  .ep a:hover{text-decoration:underline}\n"
                + "</style></head><body>\n"
                + "<div class=\"card\">\n"
                + "  <div class=\"icon\">\u2601\uFE0F</div>\n"
                + "  <h1>\u5FAE\u535A\u8206\u60C5\u5206\u6790\u7CFB\u7EDF</h1>\n"
                + "  <p class=\"desc\">Java \u540E\u7AEF\u670D\u52A1 (Spring Boot) \u00B7 \u8BBA\u6587 6.2 \u5206\u5C42\u67B6\u6784\u4E2D\u7684\u4E1A\u52A1\u903B\u8F91\u5C42</p>\n"
                + "  <div class=\"status\"><span class=\"dot\"></span> \u670D\u52A1\u8FD0\u884C\u4E2D</div>\n"
                + "  <div class=\"endpoints\">\n"
                + "    <h3>API \u7AEF\u70B9</h3>\n"
                + "    <div class=\"ep\"><span>\u670D\u52A1\u4FE1\u606F</span><a href=\"/api/\">/api/</a></div>\n"
                + "    <div class=\"ep\"><span>\u4EEA\u8868\u76D8\u7EDF\u8BA1</span><a href=\"/api/dashboard/stats\">/api/dashboard/stats</a></div>\n"
                + "    <div class=\"ep\"><span>\u91C7\u96C6\u4EFB\u52A1</span><a href=\"/api/collection/tasks\">/api/collection/tasks</a></div>\n"
                + "    <div class=\"ep\"><span>\u60C5\u611F\u5206\u5E03</span><a href=\"/api/dashboard/sentiment-distribution\">/api/dashboard/sentiment-distribution</a></div>\n"
                + "    <div class=\"ep\"><span>\u7CFB\u7EDF\u6307\u6807</span><a href=\"/api/dashboard/metrics\">/api/dashboard/metrics</a></div>\n"
                + "  </div>\n"
                + "</div></body></html>";

        return ResponseEntity.status(statusCode == 404 ? 200 : statusCode)
                .contentType(MediaType.TEXT_HTML)
                .body(html);
    }
}
