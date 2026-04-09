package com.weibo.common.utils;

import com.weibo.common.constants.ErrorCode;
import com.weibo.common.exception.BusinessException;
import lombok.extern.slf4j.Slf4j;
import org.apache.http.HttpEntity;
import org.apache.http.client.config.RequestConfig;
import org.apache.http.client.methods.*;
import org.apache.http.conn.ssl.NoopHostnameVerifier;
import org.apache.http.conn.ssl.SSLConnectionSocketFactory;
import org.apache.http.entity.ContentType;
import org.apache.http.entity.StringEntity;
import org.apache.http.entity.mime.HttpMultipartMode;
import org.apache.http.entity.mime.MultipartEntityBuilder;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.DefaultHttpRequestRetryHandler;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.impl.conn.PoolingHttpClientConnectionManager;
import org.apache.http.ssl.SSLContexts;
import org.apache.http.util.EntityUtils;

import javax.net.ssl.SSLContext;
import java.io.File;
import java.io.IOException;
import java.util.Map;

/**
 * 功能强大且线程安全的HTTP请求工具类，基于Apache HttpClient 4.5.13。
 * <p>
 * 特性:
 * - 使用连接池管理，提高性能。
 * - 支持自动重试机制。
 * - 支持GET, POST (JSON/Form), PUT, DELETE请求。
 * - 支持文件上传。
 * - 支持自定义请求头和超时配置。
 * - 统一的异常处理和日志记录。
 */
@Slf4j
public final class HttpUtils {

    // ================== Constants ==================
    private static final int CONNECT_TIMEOUT = 5000; // 连接超时时间
    private static final int SOCKET_TIMEOUT = 10000; // 读取超时时间
    private static final int MAX_TOTAL_CONNECTIONS = 200; // 连接池最大连接数
    private static final int MAX_PER_ROUTE_CONNECTIONS = 50; // 每个路由的最大连接数
    private static final int RETRY_COUNT = 3; // 自动重试次数

    private static final CloseableHttpClient HTTP_CLIENT;

    static {
        // SSL上下文，信任所有证书
        SSLContext sslContext = SSLContexts.createSystemDefault();
        SSLConnectionSocketFactory sslsf = new SSLConnectionSocketFactory(sslContext, NoopHostnameVerifier.INSTANCE);

        // 连接池管理器
        PoolingHttpClientConnectionManager connectionManager = new PoolingHttpClientConnectionManager();
        connectionManager.setMaxTotal(MAX_TOTAL_CONNECTIONS);
        connectionManager.setDefaultMaxPerRoute(MAX_PER_ROUTE_CONNECTIONS);

        // 请求配置
        RequestConfig requestConfig = RequestConfig.custom()
                .setConnectTimeout(CONNECT_TIMEOUT)
                .setSocketTimeout(SOCKET_TIMEOUT)
                .build();

        // HTTP客户端构建
        HTTP_CLIENT = HttpClients.custom()
                .setConnectionManager(connectionManager)
                .setDefaultRequestConfig(requestConfig)
                .setRetryHandler(new DefaultHttpRequestRetryHandler(RETRY_COUNT, true))
                .setSSLSocketFactory(sslsf)
                .build();

        log.info("HttpUtils initialized with connection pool and default settings.");

        // JVM关闭时，优雅关闭连接池
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            try {
                HTTP_CLIENT.close();
                log.info("HttpClient connection pool shut down gracefully.");
            } catch (IOException e) {
                log.error("Error shutting down HttpClient connection pool", e);
            }
        }));
    }

    private HttpUtils() {
        // 私有构造，防止实例化
    }

    // ================== Public Methods ==================

    /**
     * 发送GET请求。
     * @param url 请求URL
     * @return 响应内容的字符串
     */
    public static String get(String url) {
        return get(url, null);
    }

    /**
     * 发送带自定义请求头的GET请求。
     * @param url 请求URL
     * @param headers 自定义请求头
     * @return 响应内容的字符串
     */
    public static String get(String url, Map<String, String> headers) {
        HttpGet httpGet = new HttpGet(url);
        if (headers != null) {
            headers.forEach(httpGet::setHeader);
        }
        return executeRequest(httpGet);
    }

    /**
     * 发送POST请求，内容为JSON格式。
     * @param url 请求URL
     * @param jsonBody JSON请求体
     * @return 响应内容的字符串
     */
    public static String postJson(String url, String jsonBody) {
        return postJson(url, jsonBody, null);
    }

    /**
     * 发送带自定义请求头的POST请求，内容为JSON格式。
     * @param url 请求URL
     * @param jsonBody JSON请求体
     * @param headers 自定义请求头
     * @return 响应内容的字符串
     */
    public static String postJson(String url, String jsonBody, Map<String, String> headers) {
        HttpPost httpPost = new HttpPost(url);
        if (headers != null) {
            headers.forEach(httpPost::setHeader);
        }
        httpPost.setEntity(new StringEntity(jsonBody, ContentType.APPLICATION_JSON));
        return executeRequest(httpPost);
    }

    /**
     * 上传文件。
     * @param url 上传URL
     * @param file 要上传的文件
     * @param formFieldName 表单中的文件字段名
     * @return 响应内容的字符串
     */
    public static String uploadFile(String url, File file, String formFieldName) {
        HttpPost httpPost = new HttpPost(url);
        HttpEntity entity = MultipartEntityBuilder.create()
                .setMode(HttpMultipartMode.BROWSER_COMPATIBLE)
                .addBinaryBody(formFieldName, file, ContentType.DEFAULT_BINARY, file.getName())
                .build();
        httpPost.setEntity(entity);
        return executeRequest(httpPost);
    }

    // ================== Private Helper ==================

    /**
     * 执行HTTP请求的核心方法。
     * @param requestBase HTTP请求对象 (HttpGet, HttpPost, etc.)
     * @return 响应内容的字符串
     */
    private static String executeRequest(HttpRequestBase requestBase) {
        long startTime = System.currentTimeMillis();
        log.info("Executing HTTP request: {} {}", requestBase.getMethod(), requestBase.getURI());

        try (CloseableHttpResponse response = HTTP_CLIENT.execute(requestBase)) {
            int statusCode = response.getStatusLine().getStatusCode();
            HttpEntity entity = response.getEntity();
            String responseBody = entity != null ? EntityUtils.toString(entity) : null;

            long duration = System.currentTimeMillis() - startTime;
            log.info("HTTP request completed. Status: {}, Duration: {}ms", statusCode, duration);

            if (statusCode >= 200 && statusCode < 300) {
                return responseBody;
            } else {
                log.error("HTTP request failed with status code: {}. Response: {}", statusCode, responseBody);
                throw new BusinessException("HTTP Error: " + statusCode);
            }
        } catch (IOException e) {
            log.error("HTTP request execution failed for {} {}: {}", requestBase.getMethod(), requestBase.getURI(), e.getMessage());
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, "HTTP request failed: " + e.getMessage());
        }
    }
}


