package com.weibo.web.aspect;

import com.weibo.common.exception.BusinessException;
import com.weibo.web.anno.RateLimit;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ClassPathResource;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import javax.servlet.http.HttpServletRequest;
import java.lang.reflect.Method;
import java.util.Collections;
import java.util.List;

/**
 * API速率限制的AOP切面实现。
 */
@Slf4j
// @Aspect   // temporarily disabled in dev to avoid Redis dependency on startup
// @Component
public class RateLimitAspect {

    @Autowired
    private StringRedisTemplate redisTemplate;

    private final DefaultRedisScript<Long> redisScript;

    public RateLimitAspect() {
        redisScript = new DefaultRedisScript<>();
        redisScript.setLocation(new ClassPathResource("scripts/rate_limit.lua"));
        redisScript.setResultType(Long.class);
    }

    @Around("@annotation(rateLimit)")
    public Object around(ProceedingJoinPoint joinPoint, RateLimit rateLimit) throws Throwable {
        HttpServletRequest request = ((ServletRequestAttributes) RequestContextHolder.currentRequestAttributes()).getRequest();
        String key = "ratelimit:" + request.getRemoteAddr() + ":" + request.getRequestURI();

        List<String> keys = Collections.singletonList(key);
        Long count = redisTemplate.execute(redisScript, keys, String.valueOf(rateLimit.count()), String.valueOf(rateLimit.time()));

        if (count != null && count == 0) {
            log.warn("Rate limit exceeded for key: {}", key);
            throw new BusinessException("Too many requests, please try again later.");
        }

        return joinPoint.proceed();
    }
}
