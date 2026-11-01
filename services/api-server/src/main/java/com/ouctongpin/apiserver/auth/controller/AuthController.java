package com.ouctongpin.apiserver.auth.controller;

import com.ouctongpin.apiserver.auth.dto.LoginReq;
import com.ouctongpin.apiserver.auth.service.AuthService;
import com.ouctongpin.apiserver.common.Result;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {
    @Autowired private AuthService authService;

    @PostMapping("/login")
    public Result<Map<String, Object>> login(@Valid @RequestBody LoginReq req) {
        return Result.ok(authService.login(req.getCode()));
    }
}
