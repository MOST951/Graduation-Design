package com.weibo.collector.api;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * OAuth 2.0认证处理器
 */
@Component
public class OAuth2Authenticator {

    @Autowired
    private AccessTokenManager accessTokenManager;

    public String getAccessToken() {
        if (!accessTokenManager.isTokenValid()) {
            refreshToken();
        }
        return accessTokenManager.getToken();
    }

    public void authenticate(String code) {
        // Exchange code for token
        // In a real app, this would make a POST request to Weibo's token endpoint
        String newToken = "new_token_from_code_" + code;
        accessTokenManager.saveToken(newToken);
    }

    public void refreshToken() {
        // Use refresh token to get a new access token
        // In a real app, this would make a POST request to Weibo's token endpoint
        String refreshedToken = "refreshed_token_" + System.currentTimeMillis();
        accessTokenManager.saveToken(refreshedToken);
    }

    public boolean validateToken(String token) {
        // In a real app, this might involve a call to a token info endpoint
        return token != null && !token.isEmpty();
    }

    /**
     * 使当前token失效，下次调用getAccessToken时将触发刷新
     */
    public void invalidateToken() {
        accessTokenManager.invalidateToken();
    }
}
