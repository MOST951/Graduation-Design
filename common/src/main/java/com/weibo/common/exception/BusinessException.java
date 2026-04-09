package com.weibo.common.exception;

import com.weibo.common.constants.ErrorCode;

/**
 * 业务逻辑异常。
 */
public class BusinessException extends BaseException {

    public BusinessException(ErrorCode errorCode, String message) {
        super(errorCode, message);
    }

    public BusinessException(ErrorCode errorCode) {
        super(errorCode);
    }

    public BusinessException(String message) {
        super(ErrorCode.BAD_REQUEST, message);
    }
}
