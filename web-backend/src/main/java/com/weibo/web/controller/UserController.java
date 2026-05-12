package com.weibo.web.controller;

import com.weibo.common.model.ResponseResult;
import com.weibo.web.entity.User;
import com.weibo.web.repository.UserRepository;
import com.weibo.web.security.JwtTokenProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

/**
 * 普通用户视角的 user API. 主要暴露 {@code /users/me} 给前端的用户菜单/权限路由消费,
 * 与 admin-side 的 /admin/users/* 区分开 (后者由 AdminController 负责).
 */
@RestController
@RequestMapping("/users")
public class UserController {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private JwtTokenProvider tokenProvider;

    @GetMapping("/me")
    public ResponseResult<Map<String, Object>> me(
            @RequestHeader(value = "Authorization", required = false) String authHeader) {
        Map<String, Object> info = new LinkedHashMap<>();
        if (StringUtils.hasText(authHeader) && authHeader.startsWith("Bearer ")) {
            String jwt = authHeader.substring(7);
            if (tokenProvider.validateToken(jwt)) {
                String username = tokenProvider.getUsernameFromJWT(jwt);
                Optional<User> userOpt = userRepository.findByUsername(username);
                if (userOpt.isPresent()) {
                    User u = userOpt.get();
                    info.put("id", u.getId());
                    info.put("username", u.getUsername());
                    info.put("name", u.getUsername());
                    info.put("email", u.getEmail());
                    String simpleRole = (u.getRoles() != null
                            && u.getRoles().toUpperCase().contains("ADMIN")) ? "admin" : "user";
                    info.put("role", simpleRole);
                    info.put("roles", u.getRoles());
                    info.put("status", u.getStatus());
                    info.put("avatar", "");
                    info.put("createdAt", u.getCreatedAt());
                    return ResponseResult.success(info);
                }
            }
        }
        return ResponseResult.error("Unauthorized");
    }
}
