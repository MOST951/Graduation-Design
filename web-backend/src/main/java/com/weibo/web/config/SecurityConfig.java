package com.weibo.web.config;



import com.weibo.web.security.JwtAuthenticationFilter;

import org.springframework.beans.factory.annotation.Autowired;

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



    // @Autowired

    // private JwtAuthenticationFilter jwtAuthenticationFilter;



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

            .antMatchers("/auth/**").permitAll()

            .antMatchers("/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html").permitAll()

            .antMatchers("/actuator/**").permitAll()

            .antMatchers("/error").permitAll()

            // 开发环境：暂时允许所有请求，生产环境应删除下面这行

            .anyRequest().permitAll();



        // http.addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

    }

}

