package com.ouctongpin.apiserver.auth.controller;

import com.ouctongpin.apiserver.auth.dto.LoginReq;
import com.ouctongpin.apiserver.auth.service.AuthService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {
    @Autowired private AuthService authService;

    // 契约：POST /api/auth/login -> { token, userId, isNewUser, needStudentVerify }
    @PostMapping("/login")
    public Map<String, Object> login(@Valid @RequestBody LoginReq req) {
        return authService.login(req.getCode());
    }
}
