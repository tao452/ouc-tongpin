package com.ouctongpin.apiserver.user;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.auth.config.*;
import com.ouctongpin.apiserver.auth.controller.AuthController;
import com.ouctongpin.apiserver.auth.service.*;
import com.ouctongpin.apiserver.common.GlobalExceptionHandler;
import com.ouctongpin.apiserver.privacy.AnonymousIdGenerator;
import com.ouctongpin.apiserver.user.controller.UserProfileController;
import com.ouctongpin.apiserver.user.service.UserProfileService;
import com.ouctongpin.apiserver.moderation.ModerationClient;
import org.junit.jupiter.api.*;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.*;
import org.springframework.core.io.ClassPathResource;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.util.Map;
import java.util.Objects;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** Real security chain, signed JWTs, MyBatis and H2 transactions for PUT /api/user/profile. */
@SpringBootTest(classes = UserProfileHttpTest.TestApplication.class, properties = {
        "spring.datasource.url=jdbc:h2:mem:user-profile;MODE=MySQL;DB_CLOSE_DELAY=-1",
        "spring.datasource.driver-class-name=org.h2.Driver", "spring.datasource.username=sa",
        "spring.datasource.password=", "spring.sql.init.mode=never",
        "jwt.secret=user-profile-test-key-not-for-production-1234567890",
        "auth.wechat.mock-enabled=true", "spring.main.banner-mode=off"
})
@AutoConfigureMockMvc
class UserProfileHttpTest {
    @Configuration @EnableAutoConfiguration
    @MapperScan("com.ouctongpin.apiserver.**.mapper")
    @Import({SecurityConfig.class, JwtUtil.class, WeChatSessionClient.class, IdentityRegistration.class,
            AuthService.class, AuthController.class, UserProfileService.class, UserProfileController.class,
            GlobalExceptionHandler.class})
    static class TestApplication {
        @Bean AnonymousIdGenerator aliases() {
            return new AnonymousIdGenerator("user-profile-alias-test-key-not-for-production-123456789");
        }
    }

    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired ObjectMapper json;
    @MockBean StringRedisTemplate redis;
    @MockBean ModerationClient moderation;

    @BeforeEach void prepare() {
        jdbc.execute("DROP ALL OBJECTS");
        new ResourceDatabasePopulator(new ClassPathResource("auth-security-schema.sql"))
                .execute(Objects.requireNonNull(jdbc.getDataSource()));
        when(moderation.requireAllowed(anyString())).thenAnswer(invocation ->
                new ModerationClient.Result(true, invocation.getArgument(0), java.util.List.of()));
    }

    private JsonNode login(String code) throws Exception {
        return json.readTree(mvc.perform(post("/api/auth/login").contentType("application/json")
                .content(json.writeValueAsString(Map.of("code", code))))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString());
    }

    private ResultActions putProfile(String token, String body) throws Exception {
        return mvc.perform(put("/api/user/profile")
                .header("Authorization", "Bearer " + token)
                .contentType("application/json").content(body));
    }

    @Test void anonymousRequestIsRejected() throws Exception {
        putProfile("", "{}").andExpect(status().isUnauthorized());
    }

    @Test void profileAndTagsPersistAndEcho() throws Exception {
        JsonNode alice = login("alice-profile");
        String token = alice.get("token").asText();
        long userId = alice.get("userId").asLong();

        putProfile(token, json.writeValueAsString(Map.of(
                "nickname", "小明", "avatarUrl", "https://example.com/a.png", "bio", "你好",
                "interestTags", new String[]{"高数", "线代"},
                "skillTags", new String[]{"Java"})))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.nickname").value("小明"))
                .andExpect(jsonPath("$.interestTags[0]").value("高数"))
                .andExpect(jsonPath("$.skillTags[0]").value("Java"));

        assertEquals("小明", jdbc.queryForObject("SELECT nickname FROM users WHERE id=?", String.class, userId));
        assertEquals("你好", jdbc.queryForObject("SELECT bio FROM users WHERE id=?", String.class, userId));
        assertEquals(3, jdbc.queryForObject("SELECT COUNT(*) FROM user_tag WHERE user_id=?", Integer.class, userId));
        assertEquals(2, jdbc.queryForObject(
                "SELECT COUNT(*) FROM user_tag WHERE user_id=? AND tag_type='INTEREST'", Integer.class, userId));
    }

    @Test void ownershipComesOnlyFromTokenEvenWhenBodyCarriesUserId() throws Exception {
        JsonNode alice = login("alice-owner"), bob = login("bob-owner");
        long bobId = bob.get("userId").asLong();

        putProfile(alice.get("token").asText(), json.writeValueAsString(Map.of(
                "nickname", "alice", "userId", bobId, "interestTags", new String[]{"x"})))
                .andExpect(status().isOk());

        // Bob's profile was untouched; the write landed on Alice's row.
        assertEquals(null, jdbc.queryForObject("SELECT bio FROM users WHERE id=?", String.class, bobId));
        assertEquals(0, jdbc.queryForObject("SELECT COUNT(*) FROM user_tag WHERE user_id=?", Integer.class, bobId));
        assertEquals(1, jdbc.queryForObject(
                "SELECT COUNT(*) FROM user_tag WHERE user_id=?", Integer.class, alice.get("userId").asLong()));
    }

    @Test void oversizedFieldsAreRejectedWithoutWriting() throws Exception {
        JsonNode user = login("alice-bounds");
        long userId = user.get("userId").asLong();
        String nicknameBefore = jdbc.queryForObject("SELECT nickname FROM users WHERE id=?", String.class, userId);

        putProfile(user.get("token").asText(), json.writeValueAsString(Map.of(
                "nickname", "字".repeat(21))))
                .andExpect(status().isBadRequest());
        putProfile(user.get("token").asText(), json.writeValueAsString(Map.of(
                "nickname", "ok", "bio", "x".repeat(101))))
                .andExpect(status().isBadRequest());
        putProfile(user.get("token").asText(), json.writeValueAsString(Map.of(
                "nickname", "ok", "interestTags", java.util.Collections.nCopies(9, "t"))))
                .andExpect(status().isBadRequest());
        putProfile(user.get("token").asText(), json.writeValueAsString(Map.of(
                "nickname", "ok", "skillTags", new String[]{"标签".repeat(7)})))
                .andExpect(status().isBadRequest());

        // Rejected requests must not change the persisted profile (login created a default nickname).
        assertEquals(nicknameBefore, jdbc.queryForObject("SELECT nickname FROM users WHERE id=?", String.class, userId));
        assertEquals(0, jdbc.queryForObject("SELECT COUNT(*) FROM user_tag WHERE user_id=?", Integer.class, userId));
    }

    @Test void replacingTagsDoesNotAccumulate() throws Exception {
        JsonNode user = login("alice-replace");
        long userId = user.get("userId").asLong();
        String token = user.get("token").asText();

        putProfile(token, json.writeValueAsString(Map.of("nickname", "a",
                "interestTags", new String[]{"A", "B", "C"}))).andExpect(status().isOk());
        putProfile(token, json.writeValueAsString(Map.of("nickname", "a",
                "interestTags", new String[]{"A", "D"}))).andExpect(status().isOk());

        assertEquals(2, jdbc.queryForObject(
                "SELECT COUNT(*) FROM user_tag WHERE user_id=? AND tag_type='INTEREST'", Integer.class, userId));
        assertFalse(Boolean.TRUE.equals(jdbc.queryForObject(
                "SELECT COUNT(*) > 0 FROM user_tag WHERE user_id=? AND tag_name='B'", Boolean.class, userId)));
    }

    @Test void blockedTagIsNotPersisted() throws Exception {
        JsonNode user = login("alice-blocked");
        String token = user.get("token").asText();
        long userId = user.get("userId").asLong();

        when(moderation.requireAllowed("违规词")).thenThrow(
                new org.springframework.web.server.ResponseStatusException(
                        org.springframework.http.HttpStatus.UNPROCESSABLE_ENTITY, "Content blocked"));

        putProfile(token, json.writeValueAsString(Map.of(
                "nickname", "ok", "interestTags", new String[]{"违规词"})))
                .andExpect(status().isUnprocessableEntity());

        assertEquals(0, jdbc.queryForObject(
                "SELECT COUNT(*) FROM user_tag WHERE user_id=?", Integer.class, userId));
        assertEquals(null, jdbc.queryForObject("SELECT bio FROM users WHERE id=?", String.class, userId));
    }
}
