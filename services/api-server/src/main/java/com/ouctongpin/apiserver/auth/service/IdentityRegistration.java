package com.ouctongpin.apiserver.auth.service;

import com.ouctongpin.apiserver.auth.entity.Auth;
import com.ouctongpin.apiserver.auth.entity.User;
import com.ouctongpin.apiserver.auth.mapper.AuthMapper;
import com.ouctongpin.apiserver.auth.mapper.UserMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class IdentityRegistration {
    private final UserMapper users;
    private final AuthMapper identities;

    public IdentityRegistration(UserMapper users, AuthMapper identities) {
        this.users = users;
        this.identities = identities;
    }

    @Transactional
    public long create(String lookupHash) {
        User user = new User();
        user.setNickname("新用户");
        user.setDeleted(0);
        users.insert(user);
        Auth auth = new Auth();
        auth.setUserId(user.getId());
        auth.setOpenid(lookupHash);
        identities.insert(auth);
        return user.getId();
    }
}
