package com.weibo.web.security;



import com.weibo.web.entity.User;

import com.weibo.web.repository.UserRepository;

import lombok.RequiredArgsConstructor;

import org.springframework.security.core.GrantedAuthority;

import org.springframework.security.core.authority.SimpleGrantedAuthority;

import org.springframework.security.core.userdetails.UserDetails;

import org.springframework.security.core.userdetails.UserDetailsService;

import org.springframework.security.core.userdetails.UsernameNotFoundException;

import org.springframework.stereotype.Service;



import java.util.Arrays;

import java.util.Collections;

import java.util.List;

import java.util.stream.Collectors;



/**

 * 加载用户特定数据的核心接口实现。

 */

@Service

@RequiredArgsConstructor

public class CustomUserDetailsService implements UserDetailsService {



    private final UserRepository userRepository;



    @Override

    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {

        User user = userRepository.findByUsername(username)

                .orElseThrow(() -> new UsernameNotFoundException("User not found with username: " + username));



        // 论文 3.2.1 + 6.2.1 RBAC: 将 DB 中的 roles 字符串 (如 "ROLE_ADMIN,ROLE_USER")

        // 拆分为 Spring Security 的 GrantedAuthority 列表, 供 SecurityAspect 校验.

        List<GrantedAuthority> authorities = parseAuthorities(user.getRoles());

        return new org.springframework.security.core.userdetails.User(

                user.getUsername(),

                user.getPassword(),

                "active".equalsIgnoreCase(user.getStatus()),

                true, true, true,

                authorities

        );

    }



    private List<GrantedAuthority> parseAuthorities(String rolesStr) {

        if (rolesStr == null || rolesStr.trim().isEmpty()) {

            return Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER"));

        }

        return Arrays.stream(rolesStr.split(","))

                .map(String::trim)

                .filter(r -> !r.isEmpty())

                .map(r -> r.startsWith("ROLE_") ? r : "ROLE_" + r.toUpperCase())

                .map(SimpleGrantedAuthority::new)

                .collect(Collectors.toList());

    }

}

