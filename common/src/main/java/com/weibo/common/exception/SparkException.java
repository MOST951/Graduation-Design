package com.weibo.common.exception;

import com.weibo.common.constants.ErrorCode;

/**
 * Spark相关操作异常。
 */
public class SparkException extends BaseException {

    public SparkException(String message) {
        super(ErrorCode.INTERNAL_ERROR, "Spark error: " + message);
    }

    public SparkException(String message, Throwable cause) {
        super(ErrorCode.INTERNAL_ERROR, "Spark error: " + message);
        initCause(cause);
    }
}
