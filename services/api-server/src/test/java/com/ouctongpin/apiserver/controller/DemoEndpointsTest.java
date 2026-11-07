package com.ouctongpin.apiserver.controller;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** 演示闭环新增接口的契约级校验，不启动 Spring 上下文、不依赖数据库或网络。 */
class DemoEndpointsTest {

    @Test
    void wordsFollowContract() {
        Map<String, Object> body = new EmotionWordController().words();
        @SuppressWarnings("unchecked")
        List<Map<String, String>> words = (List<Map<String, String>>) body.get("words");
        assertEquals(6, words.size());
        for (Map<String, String> word : words) {
            assertTrue(word.containsKey("code"));
            assertTrue(word.containsKey("label"));
            assertTrue(word.containsKey("colorToken"));
        }
        @SuppressWarnings("unchecked")
        Map<String, Integer> scale = (Map<String, Integer>) body.get("intensityScale");
        assertEquals(1, scale.get("min"));
        assertEquals(5, scale.get("max"));
    }

    @Test
    void loginReturnsContractFieldsWithoutLeakingCode() {
        DemoAuthController.LoginRequest request = new DemoAuthController.LoginRequest();
        request.code = "synthetic-wx-code";
        Map<String, Object> body = new DemoAuthController().login(request);
        assertEquals(DemoAuthController.DEMO_TOKEN, body.get("token"));
        assertEquals(DemoAuthController.DEMO_USER_ID, body.get("userId"));
        assertFalse((Boolean) body.get("isNewUser"));
        assertFalse((Boolean) body.get("needStudentVerify"));
        assertEquals(4, body.size());
        assertFalse(body.toString().contains("synthetic-wx-code"));
    }

    @Test
    void missingOrBlankCodeIsRejected() {
        DemoAuthController controller = new DemoAuthController();
        assertThrows(ResponseStatusException.class, () -> controller.login(null));
        DemoAuthController.LoginRequest blank = new DemoAuthController.LoginRequest();
        blank.code = "  ";
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> controller.login(blank));
        assertEquals(HttpStatus.UNAUTHORIZED.value(), error.getStatusCode().value());
    }
}
