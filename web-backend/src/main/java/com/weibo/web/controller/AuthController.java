package com.weibo.web.controller;

import com.weibo.common.model.ResponseResult;
import com.weibo.web.dto.request.LoginRequest;
import com.weibo.web.dto.response.LoginResponse;
import com.weibo.web.service.AuthService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/auth")
public class AuthController {

    @Autowired
    private AuthService authService;

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
}
