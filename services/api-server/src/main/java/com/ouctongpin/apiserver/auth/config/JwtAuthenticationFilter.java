package com.ouctongpin.apiserver.auth.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.auth.entity.User;
import com.ouctongpin.apiserver.auth.mapper.UserMapper;
import com.ouctongpin.apiserver.common.Result;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.dao.DataAccessException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;
import java.io.IOException;
import java.util.Collections;
import java.util.List;

public class JwtAuthenticationFilter extends OncePerRequestFilter {
    private final JwtUtil jwt;
    private final UserMapper users;
    private final ObjectMapper json;

    public JwtAuthenticationFilter(JwtUtil jwt, UserMapper users, ObjectMapper json) {
        this.jwt = jwt;
        this.users = users;
        this.json = json;
    }

    @Override protected boolean shouldNotFilter(HttpServletRequest request) {
        return request.getServletPath().equals("/api/auth/login")
                || request.getServletPath().equals("/internal/health");
    }

    @Override protected void doFilterInternal(HttpServletRequest request,
            HttpServletResponse response, FilterChain chain) throws ServletException, IOException {
        List<String> values = Collections.list(request.getHeaders("Authorization"));
        if (!values.isEmpty()) {
            try {
                String header = values.get(0);
                if (values.size() != 1 || !header.regionMatches(true, 0, "Bearer ", 0, 7)
                        || header.length() > 4103) throw new IllegalArgumentException("Invalid header");
                long id = jwt.verify(header.substring(7));
                User user = users.selectById(id);
                if (user == null || !Integer.valueOf(0).equals(user.getDeleted())) {
                    throw new IllegalArgumentException("Inactive identity");
                }
                var context = SecurityContextHolder.createEmptyContext();
                context.setAuthentication(new UsernamePasswordAuthenticationToken(id, null,
                        List.of(new SimpleGrantedAuthority("ROLE_USER"))));
                SecurityContextHolder.setContext(context);
            } catch (JwtException | IllegalArgumentException error) {
                reject(response, 401, "登录凭证无效或已过期");
                return;
            } catch (DataAccessException error) {
                reject(response, 503, "认证服务暂不可用");
                return;
            }
        }
        chain.doFilter(request, response);
    }

    private void reject(HttpServletResponse response, int status, String message) throws IOException {
        response.setStatus(status);
        response.setContentType("application/json;charset=UTF-8");
        if (status == 401) response.setHeader("WWW-Authenticate", "Bearer");
        json.writeValue(response.getOutputStream(), Result.fail(status, message));
    }
}
