package com.weibo.common.model;

import com.weibo.common.constants.ErrorCode;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * API接口统一返回结果封装类。
 * @param <T> a
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ResponseResult<T> {

    private int code;
    private String message;
    private T data;
    private final LocalDateTime timestamp = LocalDateTime.now();

    public static <T> ResponseResult<T> success(T data) {
        return new ResponseResult<>(ErrorCode.SUCCESS.getCode(), ErrorCode.SUCCESS.getMessage(), data);
    }

    public static <T> ResponseResult<T> success() {
        return success(null);
    }

    public static <T> ResponseResult<T> fail(ErrorCode errorCode) {
        return new ResponseResult<>(errorCode.getCode(), errorCode.getMessage(), null);
    }

    public static <T> ResponseResult<T> error(String message) {
        return new ResponseResult<>(ErrorCode.INTERNAL_ERROR.getCode(), message, null);
    }
}
