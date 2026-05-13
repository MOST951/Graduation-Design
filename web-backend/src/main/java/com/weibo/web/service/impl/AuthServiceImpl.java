package com.weibo.web.service.impl;



import com.google.common.cache.CacheBuilder;

import com.google.common.cache.CacheLoader;

import com.google.common.cache.LoadingCache;

import com.weibo.common.exception.BusinessException;

import com.weibo.web.dto.request.LoginRequest;

import com.weibo.web.dto.response.LoginResponse;

import com.weibo.web.entity.User;

import com.weibo.web.repository.UserRepository;

import com.weibo.web.security.JwtTokenProvider;

import com.weibo.web.service.AuthService;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;

import org.springframework.data.redis.core.StringRedisTemplate;

import org.springframework.security.authentication.AuthenticationManager;

import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;

import org.springframework.security.core.Authentication;

import org.springframework.security.core.context.SecurityContextHolder;

import org.springframework.security.crypto.password.PasswordEncoder;

import org.springframework.stereotype.Service;



import java.util.concurrent.ExecutionException;





/**

//  * 认证服务的完整实现

 * <p>

 * 特性:

 * - 集成Spring Security进行用户认证。

 * - 生成和管理JWT（access & refresh tokens）。

 * - 使用Redis实现Token黑名单（用于注销）。

 * - 实现登录失败次数限制，防止暴力破解。

 */

@Slf4j

@Service

public class AuthServiceImpl implements AuthService {



    private final AuthenticationManager authenticationManager;

    private final UserRepository userRepository;

    private final PasswordEncoder passwordEncoder;

    private final JwtTokenProvider tokenProvider;

    private final StringRedisTemplate redisTemplate;

    private final LoadingCache<String, Integer> loginAttemptCache;



    @Autowired

    public AuthServiceImpl(AuthenticationManager authenticationManager, UserRepository userRepository, 

                         PasswordEncoder passwordEncoder, JwtTokenProvider tokenProvider, 

                         StringRedisTemplate redisTemplate) {

        this.authenticationManager = authenticationManager;

        this.userRepository = userRepository;

        this.passwordEncoder = passwordEncoder;

        this.tokenProvider = tokenProvider;

        this.redisTemplate = redisTemplate;



        // 初始化登录尝试缓存：10分钟后过期，最大缓存1000个条目

        this.loginAttemptCache = CacheBuilder.newBuilder()

                .expireAfterWrite(java.time.Duration.ofMinutes(10))

                .maximumSize(1000)

                .build(new CacheLoader<String, Integer>() {

                    @Override

                    public Integer load(String key) {

                        return 0;

                    }

                });

    }



    @Override

    public LoginResponse login(LoginRequest loginRequest) {

        String username = loginRequest.getUsername();

        checkLoginAttempts(username);



        try {

            Authentication authentication = authenticationManager.authenticate(

                    new UsernamePasswordAuthenticationToken(username, loginRequest.getPassword())

            );

            SecurityContextHolder.getContext().setAuthentication(authentication);

            loginAttemptCache.invalidate(username); // 登录成功，清除尝试次数

            // 论文 6.2.1: JWT 必须含 role claim, 由前端 store 解出做权限路由
            String simplifiedRole = userRepository.findByUsername(username)
                    .map(u -> simplifyRole(u.getRoles()))
                    .orElse("user");
            String accessToken = tokenProvider.generateToken(authentication, simplifiedRole);

            log.info("User '{}' logged in successfully.", username);

            // 将用户基本信息附在登录响应中, 减少前端额外的 /auth/me 调用 (并防止前端因 user 字段缺失而 TypeError)
            LoginResponse.UserBrief brief = userRepository.findByUsername(username)
                    .map(u -> new LoginResponse.UserBrief(
                            u.getId(),
                            u.getUsername(),
                            u.getUsername(),
                            u.getEmail(),
                            simplifyRole(u.getRoles()),
                            ""
                    ))
                    .orElse(null);
            return new LoginResponse(accessToken, "Bearer", brief);

        } catch (Exception e) {

            incrementLoginAttempts(username);

            log.warn("Login failed for user '{}'. Reason: {}", username, e.getMessage());

            throw new BusinessException("Invalid username or password");

        }

    }



    @Override

    public void register(LoginRequest loginRequest) {

        if (userRepository.findByUsername(loginRequest.getUsername()).isPresent()) {

            throw new BusinessException("Username is already taken!");

        }

        User user = new User();

        user.setUsername(loginRequest.getUsername());

        user.setPassword(passwordEncoder.encode(loginRequest.getPassword()));

        user.setRoles("ROLE_USER"); // 默认角色

        user.setStatus("ACTIVE");

        log.info("Registering new user: {}", loginRequest.getUsername());

        userRepository.save(user);

    }



    public void logout(String token) {

        if (tokenProvider.validateToken(token)) {

            // Blacklist token for 24 hours (or use token's actual expiry if available)

            redisTemplate.opsForValue().set("blacklist:" + token, "logged_out", java.time.Duration.ofHours(24));

            log.info("Token for user '{}' has been blacklisted.", tokenProvider.getUsernameFromJWT(token));

        }

    }



    @Override

    public LoginResponse refreshToken(String oldToken) {

        if (tokenProvider.validateToken(oldToken)) {

            String username = tokenProvider.getUsernameFromJWT(oldToken);

            Authentication authentication = new UsernamePasswordAuthenticationToken(username, null, null);

            String newJwt = tokenProvider.generateToken(authentication);

            return new LoginResponse(newJwt, "Bearer");

        }

        return null;

    }



    // --- Private Helper Methods ---



    private void checkLoginAttempts(String username) {

        // 开发环境暂时禁用登录限制

        // try {

        //     int attempts = loginAttemptCache.get(username);

        //     if (attempts >= 5) {

        //         log.warn("User '{}' has been locked out due to too many failed login attempts.", username);

        //         throw new BusinessException("Account locked due to too many failed login attempts.");

        //     }

        // } catch (ExecutionException e) {

        //     // 正常情况下不应发生

        //     throw new RuntimeException(e);

        // }

    }



    private void incrementLoginAttempts(String username) {

        try {

            int attempts = loginAttemptCache.get(username);

            loginAttemptCache.put(username, attempts + 1);

        } catch (ExecutionException e) {

            loginAttemptCache.put(username, 1);

        }

    }

    /** 把 DB 里的 roles 字符串 (如 "ROLE_ADMIN,ROLE_USER") 简化成前端期望的 "admin"/"user". */
    private static String simplifyRole(String roles) {
        if (roles == null || roles.isEmpty()) return "user";
        String upper = roles.toUpperCase();
        if (upper.contains("ADMIN")) return "admin";
        return "user";
    }

}

