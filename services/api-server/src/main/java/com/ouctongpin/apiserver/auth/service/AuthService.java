package com.ouctongpin.apiserver.auth.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.ouctongpin.apiserver.auth.config.JwtUtil;
import com.ouctongpin.apiserver.auth.entity.Auth;
import com.ouctongpin.apiserver.auth.entity.User;
import com.ouctongpin.apiserver.auth.mapper.AuthMapper;
import com.ouctongpin.apiserver.auth.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import com.ouctongpin.apiserver.privacy.AnonymousIdGenerator;

import java.util.HashMap;
import java.util.Map;

@Service
public class AuthService {
    @Autowired private UserMapper userMapper;
    @Autowired private AuthMapper authMapper;
    @Autowired private JwtUtil jwtUtil;
    @Autowired private WeChatSessionClient wechat;
    @Autowired private IdentityRegistration registration;
    @Autowired private AnonymousIdGenerator anonymousIds;

    // 契约响应：{ token, userId, isNewUser, needStudentVerify }
    public Map<String, Object> login(String code) {
        String lookup = anonymousIds.generate(wechat.exchange(code), "wechat-login");
        Auth auth = find(lookup);
        Long userId;
        boolean isNewUser;
        if (auth == null) {
            try {
                userId = registration.create(lookup);
                isNewUser = true;
            } catch (DuplicateKeyException concurrentLogin) {
                // The separate transaction rolled back the losing user's insert.
                auth = find(lookup);
                if (auth == null) throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE);
                userId = auth.getUserId();
                isNewUser = false;
            }
        } else {
            userId = auth.getUserId();
            isNewUser = false;
        }

        User user = userMapper.selectById(userId);
        if (user == null || !Integer.valueOf(0).equals(user.getDeleted())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED);
        }
        String token = jwtUtil.generateToken(userId);
        Map<String, Object> res = new HashMap<>();
        res.put("token", token);
        res.put("userId", String.valueOf(userId));
        res.put("isNewUser", isNewUser);
        res.put("needStudentVerify", auth == null || auth.getStudentNo() == null
                || auth.getStudentNo().isBlank());
        return res;
    }

    private Auth find(String lookup) {
        return authMapper.selectOne(new LambdaQueryWrapper<Auth>().eq(Auth::getOpenid, lookup));
    }
}
