package com.weibo.web.aspect;

import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Aspect
@Component
public class PerformanceAspect {

    private static final Logger logger = LoggerFactory.getLogger(PerformanceAspect.class);
    private static final long WARN_THRESHOLD_MS = 200; // Warn if execution takes longer than 200ms

    @Pointcut("within(com.weibo.web.service..*)")
    public void serviceMethods() {
        // Pointcut for all methods in the service layer
    }

    @Around("serviceMethods()")
    public Object measureExecutionTime(ProceedingJoinPoint joinPoint) throws Throwable {
        long start = System.currentTimeMillis();
        Object result = joinPoint.proceed();
        long end = System.currentTimeMillis();
        long duration = end - start;

        if (duration > WARN_THRESHOLD_MS) {
            logger.warn("PERFORMANCE-WARN: {}.{} took {} ms to execute.",
                    joinPoint.getSignature().getDeclaringTypeName(),
                    joinPoint.getSignature().getName(),
                    duration);
        }

        return result;
    }
}
