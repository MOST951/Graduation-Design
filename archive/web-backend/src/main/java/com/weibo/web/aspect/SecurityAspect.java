package com.weibo.web.aspect;

import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.aspectj.lang.annotation.Pointcut;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

@Aspect
@Component
public class SecurityAspect {

    private static final Logger logger = LoggerFactory.getLogger(SecurityAspect.class);

    /**
     * This is a placeholder for a more complex security check.
     * In a real application, you would likely use Spring Security's @PreAuthorize annotation.
     */
    @Pointcut("@annotation(com.weibo.web.aspect.PreAuthorizeAdmin)")
    public void adminOnly() {}

    @Before("adminOnly()")
    public void checkAdminAccess() {
        boolean isAdmin = SecurityContextHolder.getContext().getAuthentication().getAuthorities().stream()
                .anyMatch(grantedAuthority -> grantedAuthority.getAuthority().equals("ROLE_ADMIN"));

        if (!isAdmin) {
            logger.warn("Unauthorized access attempt to an admin-only resource.");
            throw new SecurityException("Access Denied: Admin role required.");
        }
    }
}
