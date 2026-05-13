package com.weibo.web.security;

import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.security.Key;
import java.util.Date;

@Component
public class JwtTokenProvider {

    private static final Logger logger = LoggerFactory.getLogger(JwtTokenProvider.class);

    private final String jwtSecret;
    private final int jwtExpirationInMs;
    private Key key;

    public JwtTokenProvider(@Value("${jwt.secret}") String jwtSecret, @Value("${jwt.expiration-ms}") int jwtExpirationInMs) {
        this.jwtSecret = jwtSecret;
        this.jwtExpirationInMs = jwtExpirationInMs;
    }

    @PostConstruct
    public void init() {
        this.key = Keys.hmacShaKeyFor(jwtSecret.getBytes());
    }

    public String generateToken(Authentication authentication) {
        return generateToken(authentication, null);
    }

    /**
     * 生成 JWT (含 role claim, 对应论文 6.2.1 核心代码片段).
     * <pre>
     *   Jwts.builder()
     *       .setSubject(userId.toString())
     *       .claim("role", role)
     *       ...
     * </pre>
     * 缺 role claim 会导致前端权限路由 / 网关 RBAC / Python 后端 require_admin 解析时
     * 拿不到角色, 退化为只看 X-User-Role header. 在此把 role 写进 JWT.
     */
    public String generateToken(Authentication authentication, String role) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + jwtExpirationInMs);

        JwtBuilder builder = Jwts.builder()
                .setSubject(authentication.getName())
                .setIssuedAt(now)
                .setExpiration(expiryDate);

        if (role != null && !role.isEmpty()) {
            builder.claim("role", role);
        } else {
            // 兜底: 从 SecurityContext 中的 authorities 推断 role
            String inferred = authentication.getAuthorities().stream()
                    .map(a -> a.getAuthority())
                    .filter(a -> a != null && !a.isEmpty())
                    .findFirst()
                    .orElse(null);
            if (inferred != null) {
                // 形如 ROLE_ADMIN -> admin
                String simplified = inferred.startsWith("ROLE_")
                        ? inferred.substring(5).toLowerCase()
                        : inferred.toLowerCase();
                builder.claim("role", simplified);
            }
        }

        return builder.signWith(key, SignatureAlgorithm.HS512).compact();
    }

    public String getUsernameFromJWT(String token) {
        Claims claims = Jwts.parserBuilder()
                .setSigningKey(key)
                .build()
                .parseClaimsJws(token)
                .getBody();

        return claims.getSubject();
    }

    public boolean validateToken(String authToken) {
        try {
            Jwts.parserBuilder().setSigningKey(key).build().parseClaimsJws(authToken);
            return true;
        } catch (MalformedJwtException ex) {
            logger.error("Invalid JWT token");
        } catch (ExpiredJwtException ex) {
            logger.error("Expired JWT token");
        } catch (UnsupportedJwtException ex) {
            logger.error("Unsupported JWT token");
        } catch (IllegalArgumentException ex) {
            logger.error("JWT claims string is empty.");
        }
        return false;
    }
}
