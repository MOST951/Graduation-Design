package com.weibo.web.aspect;

import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.AfterReturning;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.aspectj.lang.annotation.Pointcut;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Aspect
@Component
public class LogAspect {

    private static final Logger logger = LoggerFactory.getLogger(LogAspect.class);

    @Pointcut("execution(* com.weibo.web.controller..*(..))")
    public void controllerLog() {}

    @Before("controllerLog()")
    public void doBefore(JoinPoint joinPoint) {
        logger.info("Request: {}.{}() with args = {}", 
                    joinPoint.getSignature().getDeclaringTypeName(), 
                    joinPoint.getSignature().getName(), 
                    joinPoint.getArgs());
    }

    @AfterReturning(pointcut = "controllerLog()", returning = "ret")
    public void doAfterReturning(Object ret) {
        logger.info("Response: {}", ret);
    }
}
