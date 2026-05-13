package com.weibo.web.aspect;

import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.aspectj.lang.annotation.Pointcut;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.Authentication;
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
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || auth.getAuthorities() == null) {
            logger.warn("Anonymous access attempt to an admin-only resource.");
            throw new SecurityException("Access Denied: authentication required.");
        }
        boolean isAdmin = auth.getAuthorities().stream()
                .anyMatch(grantedAuthority -> "ROLE_ADMIN".equals(grantedAuthority.getAuthority()));

        if (!isAdmin) {
            logger.warn("Unauthorized access by user '{}' to admin-only resource.", auth.getName());
            throw new SecurityException("Access Denied: Admin role required.");
        }
    }
}
