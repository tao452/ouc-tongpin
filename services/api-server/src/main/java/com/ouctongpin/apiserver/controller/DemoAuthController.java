package com.ouctongpin.apiserver.controller;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;

/**
 * 演示用登录桩，仅用于本地 / 测试环境打通「登录 → 打卡 → 日历回显」链路。
 *
 * 契约见 packages/contract/openapi.yaml 的 POST /api/auth/login：
 * 正式实现应由 M5 完成 code2session、签发 JWT 与学号认证（US-33），届时删除本类。
 * 这里不校验微信 code、不签发真实 JWT、不写日志，且绝不记录 code 本身（临时凭证属敏感信息）。
 * 返回的 userId 与 InMemoryCheckinService 当前写死的 "demoUser" 保持一致。
 */
@RestController
@RequestMapping("/api/auth")
public class DemoAuthController {

    static final String DEMO_TOKEN = "demo-token-v0.1";
    static final String DEMO_USER_ID = "demoUser";

    @PostMapping("/login")
    public Map<String, Object> login(@RequestBody(required = false) LoginRequest request) {
        if (request == null || request.code == null || request.code.isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "invalid code");
        }
        return Map.of(
                "token", DEMO_TOKEN,
                "userId", DEMO_USER_ID,
                "isNewUser", false,
                "needStudentVerify", false
        );
    }

    public static class LoginRequest {
        public String code;
    }
}
