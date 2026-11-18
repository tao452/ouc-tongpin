package com.ouctongpin.apiserver.auth.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.auth.mapper.UserMapper;
import com.ouctongpin.apiserver.common.Result;
import jakarta.servlet.DispatcherType;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
public class SecurityConfig {
    @Bean UserDetailsService noPasswordAuthentication() {
        return username -> { throw new UsernameNotFoundException("Password login is disabled"); };
    }

    @Bean SecurityFilterChain apiSecurity(HttpSecurity http, JwtUtil jwt, UserMapper users,
                                         ObjectMapper json) throws Exception {
        return http.csrf(c -> c.disable()).httpBasic(c -> c.disable()).formLogin(c -> c.disable())
                .logout(c -> c.disable()).requestCache(c -> c.disable())
                .sessionManagement(c -> c.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(c -> c
                        .dispatcherTypeMatchers(DispatcherType.ERROR).permitAll()
                        .requestMatchers(HttpMethod.POST, "/api/auth/login").permitAll()
                        .requestMatchers(HttpMethod.GET, "/internal/health", "/api/emotions/words").permitAll()
                        .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                        .requestMatchers("/api/admin/**", "/api/internal/**", "/api/privacy/**",
                                "/api/auth/**").denyAll()
                        .anyRequest().authenticated())
                .exceptionHandling(c -> c.authenticationEntryPoint((request, response, error) -> {
                    response.setStatus(401);
                    response.setHeader("WWW-Authenticate", "Bearer");
                    response.setContentType("application/json;charset=UTF-8");
                    json.writeValue(response.getOutputStream(), Result.fail(401, "请先登录"));
                }).accessDeniedHandler((request, response, error) -> {
                    response.setStatus(403);
                    response.setContentType("application/json;charset=UTF-8");
                    json.writeValue(response.getOutputStream(), Result.fail(403, "无权访问"));
                }))
                // Not a servlet Filter bean: run exactly once inside the security chain.
                .addFilterBefore(new JwtAuthenticationFilter(jwt, users, json),
                        UsernamePasswordAuthenticationFilter.class).build();
    }
}
