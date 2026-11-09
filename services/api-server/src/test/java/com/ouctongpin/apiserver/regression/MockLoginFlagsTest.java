package com.ouctongpin.apiserver.regression;

import com.ouctongpin.apiserver.auth.config.JwtUtil;
import com.ouctongpin.apiserver.auth.entity.Auth;
import com.ouctongpin.apiserver.auth.mapper.AuthMapper;
import com.ouctongpin.apiserver.auth.service.AuthService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class MockLoginFlagsTest {
    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {" "})
    void unboundMockUserNeedsVerification(String studentNo) {
        assertEquals(true, login(studentNo).get("needStudentVerify"));
    }

    @Test void boundMockUserDoesNotNeedVerification() {
        assertEquals(false, login("synthetic-student").get("needStudentVerify"));
    }

    private java.util.Map<String, Object> login(String studentNo) {
        AuthMapper mapper = mock(AuthMapper.class);
        Auth auth = new Auth();
        auth.setUserId(1L);
        auth.setStudentNo(studentNo);
        when(mapper.selectOne(any())).thenReturn(auth);
        JwtUtil jwt = mock(JwtUtil.class);
        when(jwt.generateToken(1L)).thenReturn("synthetic-token");
        AuthService service = new AuthService();
        ReflectionTestUtils.setField(service, "authMapper", mapper);
        ReflectionTestUtils.setField(service, "jwtUtil", jwt);
        return service.login("synthetic-code");
    }
}
