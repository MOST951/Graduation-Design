package com.weibo.common.utils;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.jayway.jsonpath.JsonPath;
import com.weibo.common.constants.AppConstants;
import com.weibo.common.constants.ErrorCode;
import com.weibo.common.exception.BusinessException;
import lombok.extern.slf4j.Slf4j;

import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.List;
import java.util.Map;

/**
 * 功能强大且线程安全的JSON工具类，基于Jackson 2.12.5。
 * <p>
 * 特性:
 * - 线程安全的单例ObjectMapper，预配置最佳实践。
 * - 支持Java 8日期时间类型 (LocalDate, LocalDateTime)。
 * - 支持泛型反序列化。
 * - 提供JSONPath支持，方便提取数据。
 * - 统一的异常处理和日志记录。
 */
@Slf4j
public final class JsonUtils {

    private static final ObjectMapper MAPPER;

    static {
        MAPPER = new ObjectMapper();

        // 配置序列化特性
        MAPPER.setSerializationInclusion(JsonInclude.Include.NON_NULL); // 忽略null字段
        MAPPER.disable(SerializationFeature.FAIL_ON_EMPTY_BEANS); // 忽略空对象
        MAPPER.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS); // 日期不写为时间戳

        // 配置反序列化特性
        MAPPER.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false); // 忽略未知字段

        // 配置日期格式和Java 8时间支持
        MAPPER.setDateFormat(new SimpleDateFormat(AppConstants.DATETIME_FORMAT));
        MAPPER.registerModule(new JavaTimeModule());

        log.info("JsonUtils initialized with custom ObjectMapper settings.");
    }

    private JsonUtils() {
    }

    /**
     * 将对象序列化为JSON字符串。
     * @param obj 要序列化的对象
     * @return JSON字符串
     */
    public static String toJson(Object obj) {
        if (obj == null) {
            return null;
        }
        try {
            return MAPPER.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            log.error("Error serializing object to JSON: {}", obj, e);
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, "JSON serialization error: " + e.getMessage());
        }
    }

    /**
     * 将JSON字符串反序列化为对象。
     * @param json JSON字符串
     * @param clazz 目标对象的Class
     * @return 反序列化后的对象
     */
    public static <T> T fromJson(String json, Class<T> clazz) {
        if (StringUtils.isBlank(json)) {
            return null;
        }
        try {
            return MAPPER.readValue(json, clazz);
        } catch (JsonProcessingException e) {
            log.error("Error deserializing JSON to object. Class: {}, JSON: {}", clazz.getSimpleName(), json, e);
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, "JSON deserialization error: " + e.getMessage());
        }
    }

    /**
     * 将JSON字符串反序列化为泛型集合（如List<T>, Map<String, T>）。
     * @param json JSON字符串
     * @param typeReference 泛型类型引用
     * @return 反序列化后的对象
     */
    public static <T> T fromJson(String json, TypeReference<T> typeReference) {
        if (StringUtils.isBlank(json)) {
            return null;
        }
        try {
            return MAPPER.readValue(json, typeReference);
        } catch (IOException e) {
            log.error("Error deserializing JSON to generic type. Type: {}, JSON: {}", typeReference.getType(), json, e);
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, "JSON generic deserialization error: " + e.getMessage());
        }
    }

    /**
     * 格式化（美化）JSON字符串。
     * @param json JSON字符串
     * @return 格式化后的JSON字符串
     */
    public static String prettify(String json) {
        if (StringUtils.isBlank(json)) {
            return null;
        }
        try {
            Object jsonObject = MAPPER.readValue(json, Object.class);
            return MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(jsonObject);
        } catch (JsonProcessingException e) {
            log.warn("Could not prettify invalid JSON: {}", json, e);
            return json; // 返回原始字符串
        }
    }

    /**
     * 验证字符串是否为有效的JSON。
     * @param json 要验证的字符串
     * @return 如果有效返回true，否则返回false
     */
    public static boolean isValid(String json) {
        if (StringUtils.isBlank(json)) {
            return false;
        }
        try {
            MAPPER.readTree(json);
            return true;
        } catch (JsonProcessingException e) {
            return false;
        }
    }

    /**
     * 使用JSONPath从JSON字符串中提取数据。
     * @param json JSON字符串
     * @param jsonPath JSONPath表达式
     * @return 提取到的数据
     */
    public static <T> T extractByPath(String json, String jsonPath) {
        if (StringUtils.isBlank(json) || StringUtils.isBlank(jsonPath)) {
            return null;
        }
        try {
            return JsonPath.read(json, jsonPath);
        } catch (Exception e) {
            log.error("Failed to extract data with JSONPath. Path: {}, JSON: {}", jsonPath, json, e);
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, "JSONPath extraction error: " + e.getMessage());
        }
    }

    /**
     * 将JSON字符串转换为JsonNode，便于进行灵活的节点操作。
     * @param json JSON字符串
     * @return JsonNode对象
     */
    public static JsonNode toJsonNode(String json) {
        if (StringUtils.isBlank(json)) {
            return null;
        }
        try {
            return MAPPER.readTree(json);
        } catch (JsonProcessingException e) {
            log.error("Error converting JSON to JsonNode: {}", json, e);
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, "JSON to JsonNode conversion error: " + e.getMessage());
        }
    }
}


