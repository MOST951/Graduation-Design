package com.weibo.collector.api;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

/**
 * Token管理器
 */
@Component
public class AccessTokenManager {

    private static final String TOKEN_KEY = "weibo_access_token";

    @Autowired
    private StringRedisTemplate redisTemplate;

    public String getToken() {
        return redisTemplate.opsForValue().get(TOKEN_KEY);
    }

    public void saveToken(String token) {
        // Weibo tokens typically expire in a few hours to a day
        redisTemplate.opsForValue().set(TOKEN_KEY, token, 1, TimeUnit.DAYS);
    }

    public void removeToken() {
        redisTemplate.delete(TOKEN_KEY);
    }

    public boolean isTokenValid() {
        return redisTemplate.hasKey(TOKEN_KEY);
    }

    /**
     * 使当前token失效
     */
    public void invalidateToken() {
        redisTemplate.delete(TOKEN_KEY);
    }
}
