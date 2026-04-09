package com.weibo.web.dto.request;

import lombok.Data;

import javax.validation.constraints.NotBlank;

/**
 * Login Request DTO
 */
@Data
public class LoginRequest {

    @NotBlank(message = "Username cannot be blank")
    private String username;

    @NotBlank(message = "Password cannot be blank")
    private String password;
}
