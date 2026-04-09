package com.weibo.collector.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.google.common.util.concurrent.RateLimiter;
import com.weibo.common.utils.HttpUtils;
import com.weibo.common.utils.JsonUtils;
import com.weibo.common.exception.BusinessException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * 微博开放API客户端，负责与微博API进行交互。
 * <p>
 * 特性:
 * - 自动处理OAuth 2.0认证和Token刷新。
 * - 内置请求速率限制。
 * - 统一的API错误处理和重试逻辑。
 * - 将JSON响应解析为Java对象。
 */
@Slf4j
@Component
public class WeiboApiClient {

    @Value("${weibo.api.baseUrl:https://api.weibo.com/2/}")
    private String apiBaseUrl;

    @Autowired
    private OAuth2Authenticator authenticator;

    // Guava RateLimiter，限制每秒的请求速率，可从配置注入
    private final RateLimiter rateLimiter = RateLimiter.create(1.0);

    /**
     * 获取用户信息。
     * @param uid 用户ID
     * @return 包含用户信息的JsonNode
     */
    public JsonNode getUserInfo(String uid) {
        String endpoint = "users/show.json";
        String url = String.format("%s%s?uid=%s", apiBaseUrl, endpoint, uid);
        return executeGetRequest(url);
    }

    /**
     * 根据关键词搜索微博话题。
     * @param keyword 搜索关键词
     * @param count 返回数量
     * @return 包含微博列表的JsonNode
     */
    public JsonNode searchTopics(String keyword, int count) {
        String endpoint = "search/topics.json";
        String url = String.format("%s%s?q=%s&count=%d", apiBaseUrl, endpoint, keyword, count);
        return executeGetRequest(url);
    }

    /**
     * 获取指定用户的微博时间线。
     * @param uid 用户ID
     * @param count 返回数量
     * @return 包含微博列表的JsonNode
     */
    public JsonNode getUserTimeline(String uid, int count) {
        String endpoint = "statuses/user_timeline.json";
        String url = String.format("%s%s?uid=%s&count=%d", apiBaseUrl, endpoint, uid);
        return executeGetRequest(url);
    }

    /**
     * 执行GET请求的核心逻辑，包含认证、速率限制和错误处理。
     * @param url 请求的完整URL
     * @return 解析后的JsonNode
     */
    private JsonNode executeGetRequest(String url) {
        rateLimiter.acquire(); // 等待直到获取到令牌
        log.debug("Acquired rate limit token, proceeding with request to: {}", url);

        String accessToken = authenticator.getAccessToken();
        Map<String, String> headers = Collections.singletonMap("Authorization", "Bearer " + accessToken);

        try {
            String jsonResponse = HttpUtils.get(url, headers);
            JsonNode responseNode = JsonUtils.toJsonNode(jsonResponse);

            // 检查微博API返回的错误
            if (responseNode.has("error_code")) {
                handleApiError(responseNode);
                // 如果错误被处理（如token刷新），则重试
                return executeGetRequest(url); // 递归重试
            }
            return responseNode;
        } catch (BusinessException e) {
            log.error("Failed to execute API request to {}: {}", url, e.getMessage());
            throw e; // 重新抛出业务异常
        }
    }

    /**
     * 处理微博API返回的特定错误码。
     * @param errorNode 包含错误信息的JsonNode
     */
    private void handleApiError(JsonNode errorNode) {
        int errorCode = errorNode.get("error_code").asInt();
        String errorMessage = errorNode.get("error").asText();
        log.warn("Weibo API returned an error. Code: {}, Message: {}", errorCode, errorMessage);

        switch (errorCode) {
            case 21332: // access_token无效或已过期
            case 21327:
                log.info("Access token expired or invalid. Attempting to refresh...");
                authenticator.invalidateToken(); // 使当前token失效
                // 下一次调用getAccessToken()时将触发刷新或重新认证
                break;
            case 10023: // 达到速率限制
                log.warn("Rate limit hit. Consider adjusting the rate limiter settings.");
                // 可以选择在这里等待一段时间，但RateLimiter本身已经处理了请求前的等待
                throw new BusinessException("Weibo API rate limit exceeded. Error code: " + errorCode);
            default:
                throw new BusinessException("Weibo API error: " + errorMessage + ", code: " + errorCode);
        }
    }
}
