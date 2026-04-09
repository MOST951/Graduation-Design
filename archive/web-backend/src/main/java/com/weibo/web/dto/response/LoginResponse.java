package com.weibo.web.dto.response;

import lombok.AllArgsConstructor;
import lombok.Data;

/**
 * Login Response DTO containing the JWT access token.
 */
@Data
@AllArgsConstructor
public class LoginResponse {

    private String accessToken;
    private String tokenType = "Bearer";

}
