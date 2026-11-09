package com.ouctongpin.apiserver.auth.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.ouctongpin.apiserver.auth.config.JwtUtil;
import com.ouctongpin.apiserver.auth.entity.Auth;
import com.ouctongpin.apiserver.auth.entity.User;
import com.ouctongpin.apiserver.auth.mapper.AuthMapper;
import com.ouctongpin.apiserver.auth.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
public class AuthService {
    @Autowired private UserMapper userMapper;
    @Autowired private AuthMapper authMapper;
    @Autowired private JwtUtil jwtUtil;

    // 契约响应：{ token, userId, isNewUser, needStudentVerify }
    public Map<String, Object> login(String code) {
        // Mock 微信的 code2session
        String mockOpenid = "openid_" + code;

        Auth auth = authMapper.selectOne(new LambdaQueryWrapper<Auth>().eq(Auth::getOpenid, mockOpenid));
        Long userId;
        boolean isNewUser;
        if (auth == null) {
            // 新用户注册
            User newUser = new User();
            newUser.setNickname("新用户");
            userMapper.insert(newUser);
            userId = newUser.getId();

            auth = new Auth();
            auth.setUserId(userId);
            auth.setOpenid(mockOpenid);
            authMapper.insert(auth);
            isNewUser = true;
        } else {
            userId = auth.getUserId();
            isNewUser = false;
        }

        String token = jwtUtil.generateToken(userId);
        Map<String, Object> res = new HashMap<>();
        res.put("token", token);
        res.put("userId", String.valueOf(userId));
        res.put("isNewUser", isNewUser);
        res.put("needStudentVerify", auth.getStudentNo() == null || auth.getStudentNo().isBlank());
        return res;
    }
}
