package com.weibo.collector.client;

import com.weibo.common.anno.Retryable;
import com.weibo.common.utils.HttpUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.IOException;

/**
 * A client for interacting with the Weibo API.
 * <p>
 * This class provides methods for making authenticated requests to various Weibo API endpoints.
 * It includes error handling and retry logic.
 * </p>
 */
@Slf4j
@Component
public class WeiboApiClient {

    private final String baseUrl = "https://api.weibo.com/2/";

    /**
     * Fetches public timeline data from the Weibo API.
     *
     * @param accessToken The OAuth2 access token.
     * @return The API response as a JSON string.
     * @throws IOException If an I/O error occurs.
     */
    @Retryable(maxAttempts = 3, delay = 2000)
    public String getPublicTimeline(String accessToken) throws IOException {
        log.info("Fetching public timeline...");
        String url = baseUrl + "statuses/public_timeline.json?access_token=" + accessToken;
        try {
            return HttpUtils.get(url);
        } catch (IOException e) {
            log.error("Failed to fetch public timeline", e);
            throw e;
        }
    }

    /**
     * Fetches user information from the Weibo API.
     *
     * @param accessToken The OAuth2 access token.
     * @param uid         The user ID.
     * @return The API response as a JSON string.
     * @throws IOException If an I/O error occurs.
     */
    @Retryable(maxAttempts = 3, delay = 2000)
    public String getUserInfo(String accessToken, String uid) throws IOException {
        log.info("Fetching user info for UID: {}", uid);
        String url = String.format("%susers/show.json?access_token=%s&uid=%s", baseUrl, accessToken, uid);
        try {
            return HttpUtils.get(url);
        } catch (IOException e) {
            log.error("Failed to fetch user info for UID: {}", uid, e);
            throw e;
        }
    }
}
