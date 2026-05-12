package com.weibo.web.dto.response;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Login Response DTO. 包含 JWT access token 与基本用户信息,
 * 让前端无需再额外调用一次 /auth/me 即可填充用户菜单 / 权限路由.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class LoginResponse {

    private String accessToken;
    private String tokenType;
    /** 当前登录用户基本信息 (前端 store/auth 直接消费). */
    private UserBrief user;

    /** 兼容仅传 token 的历史用法. */
    public LoginResponse(String accessToken, String tokenType) {
        this.accessToken = accessToken;
        this.tokenType = tokenType;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UserBrief {
        private Long id;
        private String username;
        /** 显示名 (优先取 nickname, 退回 username). */
        private String name;
        private String email;
        /** 简化后的单角色: admin / user. */
        private String role;
        private String avatar;
    }
}
