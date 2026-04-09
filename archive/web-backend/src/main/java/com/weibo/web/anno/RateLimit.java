package com.weibo.web.anno;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 自定义注解，用于API速率限制。
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface RateLimit {

    /**
     * 允许的最大请求数
     */
    int count() default 100;

    /**
     * 时间窗口，单位为秒
     */
    long time() default 60;
}
