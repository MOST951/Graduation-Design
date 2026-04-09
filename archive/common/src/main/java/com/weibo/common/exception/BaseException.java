package com.weibo.common.exception;

import com.weibo.common.constants.ErrorCode;
import lombok.Getter;
import java.time.LocalDateTime;

/**
 * 自定义异常基类。
 */
@Getter
public abstract class BaseException extends RuntimeException {

    private final ErrorCode errorCode;
    private final String errorMessage;
    private final LocalDateTime timestamp;

    public BaseException(ErrorCode errorCode, String errorMessage) {
        super(errorMessage);
        this.errorCode = errorCode;
        this.errorMessage = errorMessage;
        this.timestamp = LocalDateTime.now();
    }

    public BaseException(ErrorCode errorCode) {
        this(errorCode, errorCode.getMessage());
    }
}
