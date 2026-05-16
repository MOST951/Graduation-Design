package com.weibo.web.config;

import com.weibo.web.security.JwtAuthenticationFilter;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configuration.WebSecurityConfigurerAdapter;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
public class SecurityConfig extends WebSecurityConfigurerAdapter {

    /** 论文 6.2.1 RBAC: 显式声明 JWT filter, 由 SecurityConfig 在 chain 中挂载 */
    @Bean
    public JwtAuthenticationFilter jwtAuthenticationFilter() {
        return new JwtAuthenticationFilter();
    }

    /** 防止 Spring Boot 把 OncePerRequestFilter bean 自动注册到 servlet 容器导致重复执行 */
    @Bean
    public FilterRegistrationBean<JwtAuthenticationFilter> jwtFilterRegistration(JwtAuthenticationFilter filter) {
        FilterRegistrationBean<JwtAuthenticationFilter> reg = new FilterRegistrationBean<>(filter);
        reg.setEnabled(false);
        return reg;
    }

    @Bean
    @Override
    public org.springframework.security.authentication.AuthenticationManager authenticationManagerBean() throws Exception {
        return super.authenticationManagerBean();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http.cors().and().csrf().disable()
            .sessionManagement().sessionCreationPolicy(SessionCreationPolicy.STATELESS).and()
            .authorizeRequests()
            .antMatchers("/").permitAll()
            .antMatchers("/api/auth/**").permitAll()
            .antMatchers("/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html").permitAll()
            .antMatchers("/actuator/**").permitAll()
            .antMatchers("/error").permitAll()
            // 论文 3.2.1: 其他接口默认开放(保持向后兼容), admin 接口由 @PreAuthorizeAdmin + SecurityAspect 保护
            .anyRequest().permitAll();

        // 挂载 JWT filter 到 UsernamePasswordAuthenticationFilter 之前,
        // 让带 token 的请求把 ROLE_ADMIN/ROLE_USER 注入 SecurityContext, SecurityAspect 据此放行/拒绝
        http.addFilterBefore(jwtAuthenticationFilter(), UsernamePasswordAuthenticationFilter.class);
    }
}
