package com.weibo.web.controller;

import com.weibo.common.model.ResponseResult;
import com.weibo.web.dto.request.LoginRequest;
import com.weibo.web.dto.response.LoginResponse;
import com.weibo.web.entity.User;
import com.weibo.web.repository.UserRepository;
import com.weibo.web.security.JwtTokenProvider;
import com.weibo.web.service.AuthService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/auth")
public class AuthController {

    @Autowired
    private AuthService authService;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private JwtTokenProvider tokenProvider;

    @PostMapping("/register")
    public ResponseResult<String> register(@RequestBody LoginRequest request) {
        authService.register(request);
        return ResponseResult.success("User registered successfully");
    }

    @PostMapping("/login")
    public ResponseResult<LoginResponse> login(@RequestBody LoginRequest request) {
        LoginResponse response = authService.login(request);
        return ResponseResult.success(response);
    }

    @PostMapping("/refresh")
    public ResponseResult<LoginResponse> refreshToken(@RequestHeader("Authorization") String token) {
        String jwt = token.replace("Bearer ", "");
        LoginResponse response = authService.refreshToken(jwt);
        return ResponseResult.success(response);
    }

    @GetMapping("/info")
    public ResponseResult<Map<String, Object>> getUserInfo(
            @RequestHeader(value = "Authorization", required = false) String authHeader) {
        Map<String, Object> info = new LinkedHashMap<>();
        if (StringUtils.hasText(authHeader) && authHeader.startsWith("Bearer ")) {
            String jwt = authHeader.substring(7);
            if (tokenProvider.validateToken(jwt)) {
                String username = tokenProvider.getUsernameFromJWT(jwt);
                Optional<User> userOpt = userRepository.findByUsername(username);
                if (userOpt.isPresent()) {
                    User user = userOpt.get();
                    info.put("id", user.getId());
                    info.put("username", user.getUsername());
                    info.put("email", user.getEmail());
                    info.put("roles", user.getRoles());
                    info.put("status", user.getStatus());
                    info.put("created_at", user.getCreatedAt());
                    return ResponseResult.success(info);
                }
            }
        }
        info.put("message", "Not authenticated or invalid token");
        return ResponseResult.error("Unauthorized");
    }

    @GetMapping("/health")
    public ResponseResult<Map<String, Object>> health() {
        Map<String, Object> h = new LinkedHashMap<>();
        h.put("status", "UP");
        h.put("service", "auth-service");
        h.put("timestamp", LocalDateTime.now());
        return ResponseResult.success(h);
    }
}
