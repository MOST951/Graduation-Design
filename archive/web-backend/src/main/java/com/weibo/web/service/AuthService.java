package com.weibo.web.service;

import com.weibo.web.dto.request.LoginRequest;
import com.weibo.web.dto.response.LoginResponse;

/**
 * Service interface for authentication-related operations.
 */
public interface AuthService {

    /**
     * Authenticates a user and returns a JWT token.
     *
     * @param loginRequest the login request containing username and password
     * @return a LoginResponse containing the access token
     */
    LoginResponse login(LoginRequest loginRequest);

    /**
     * Registers a new user.
     *
     * @param loginRequest the registration request containing username and password
     */
    void register(LoginRequest loginRequest);

    /**
     * Refreshes an expired JWT token.
     *
     * @param oldToken the expired token
     * @return a new LoginResponse containing the new access token
     */
    LoginResponse refreshToken(String oldToken);

}
