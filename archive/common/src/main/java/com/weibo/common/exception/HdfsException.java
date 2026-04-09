package com.weibo.common.exception;

import com.weibo.common.constants.ErrorCode;

/**
 * HDFS相关操作异常。
 */
public class HdfsException extends BaseException {

    public HdfsException(String message) {
        super(ErrorCode.INTERNAL_ERROR, "HDFS error: " + message);
    }

    public HdfsException(String message, Throwable cause) {
        super(ErrorCode.INTERNAL_ERROR, "HDFS error: " + message);
        initCause(cause);
    }
}
