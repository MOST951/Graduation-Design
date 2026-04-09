package com.weibo.common.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

/**
 * Redis 配置类，用于配置 Redis 连接和 RedisTemplate。
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "spring.redis")
public class RedisConfig {

    private String host = "localhost";
    private int port = 6379;
    private String password;
    private int database = 0;

    @Bean
    public LettuceConnectionFactory redisConnectionFactory() {
        String resolvedHost = host;
        // Robust check for host
        if (resolvedHost == null || resolvedHost.trim().isEmpty()) {
            resolvedHost = "localhost";
        }
        
        System.out.println("DEBUG: Creating RedisConnectionFactory with host: " + resolvedHost + ", port: " + port);

        RedisStandaloneConfiguration config = new RedisStandaloneConfiguration();
        config.setHostName(resolvedHost);
        config.setPort(port > 0 ? port : 6379);
        
        if (password != null && !password.isEmpty()) {
            config.setPassword(password);
        }
        config.setDatabase(database);
        
        return new LettuceConnectionFactory(config);
    }

    @Bean
    public RedisTemplate<String, Object> redisTemplate(LettuceConnectionFactory redisConnectionFactory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(redisConnectionFactory);
        // Key使用String序列化
        template.setKeySerializer(new StringRedisSerializer());
        template.setHashKeySerializer(new StringRedisSerializer());
        // Value使用JSON序列化
        template.setValueSerializer(new GenericJackson2JsonRedisSerializer());
        template.setHashValueSerializer(new GenericJackson2JsonRedisSerializer());
        template.afterPropertiesSet();
        return template;
    }
}
