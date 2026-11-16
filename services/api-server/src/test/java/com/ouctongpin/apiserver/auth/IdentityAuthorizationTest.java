package com.ouctongpin.apiserver.auth;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.auth.config.*;
import com.ouctongpin.apiserver.auth.controller.AuthController;
import com.ouctongpin.apiserver.auth.service.*;
import com.ouctongpin.apiserver.checkin.controller.CheckinController;
import com.ouctongpin.apiserver.checkin.service.CheckinService;
import com.ouctongpin.apiserver.treehole.controller.TreeholeController;
import com.ouctongpin.apiserver.treehole.service.TreeholeService;
import com.ouctongpin.apiserver.buddy.controller.BuddyController;
import com.ouctongpin.apiserver.buddy.service.BuddyService;
import com.ouctongpin.apiserver.common.GlobalExceptionHandler;
import com.ouctongpin.apiserver.privacy.AnonymousIdGenerator;
import com.ouctongpin.apiserver.moderation.ModerationClient;
import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.*;
import org.springframework.core.io.ClassPathResource;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.springframework.test.web.servlet.MockMvc;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** Real security chain, signed JWTs, MyBatis and transactions; synthetic accounts in H2. */
@SpringBootTest(classes = IdentityAuthorizationTest.TestApplication.class, properties = {
        "spring.datasource.url=jdbc:h2:mem:identity-security;MODE=MySQL;DB_CLOSE_DELAY=-1",
        "spring.datasource.driver-class-name=org.h2.Driver", "spring.datasource.username=sa",
        "spring.datasource.password=", "spring.sql.init.mode=never",
        "jwt.secret=identity-security-test-key-not-for-production-123456789",
        "auth.wechat.mock-enabled=true", "spring.main.banner-mode=off"
})
@AutoConfigureMockMvc
class IdentityAuthorizationTest {
    private static final String KEY = "identity-security-test-key-not-for-production-123456789";
    @Configuration @EnableAutoConfiguration
    @MapperScan("com.ouctongpin.apiserver.**.mapper")
    @Import({SecurityConfig.class, JwtUtil.class, WeChatSessionClient.class, IdentityRegistration.class,
            AuthService.class, AuthController.class, CheckinService.class, CheckinController.class,
            TreeholeService.class, TreeholeController.class, BuddyService.class, BuddyController.class,
            GlobalExceptionHandler.class})
    static class TestApplication {
        @Bean AnonymousIdGenerator aliases() {
            return new AnonymousIdGenerator("identity-alias-test-key-not-for-production-123456789");
        }
    }
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired ObjectMapper json;
    @Autowired JwtUtil jwt;
    @Autowired IdentityRegistration registration;
    @MockBean ModerationClient moderation;
    @MockBean StringRedisTemplate redis;

    @BeforeEach @SuppressWarnings("unchecked") void prepare() {
        jdbc.execute("DROP ALL OBJECTS");
        new ResourceDatabasePopulator(new ClassPathResource("auth-security-schema.sql"))
                .execute(Objects.requireNonNull(jdbc.getDataSource()));
        ZSetOperations<String, String> queue = mock(ZSetOperations.class);
        when(redis.opsForZSet()).thenReturn(queue);
        when(queue.add(anyString(), anyString(), anyDouble())).thenReturn(true);
    }

    private JsonNode login(String code) throws Exception {
        return json.readTree(mvc.perform(post("/api/auth/login").contentType("application/json")
                .content(json.writeValueAsString(Map.of("code", code))))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString());
    }
    private JsonNode checkin(JsonNode caller, String note) throws Exception {
        return json.readTree(mvc.perform(post("/api/emotions/checkins")
                .header("Authorization", "Bearer " + caller.get("token").asText())
                .contentType("application/json").content(json.writeValueAsString(Map.of(
                        "emotion", "CALM", "intensity", 3, "note", note,
                        "checkinDate", "2040-01-01", "userId", 999999))))
                .andExpect(status().isOk()).andExpect(jsonPath("$.userId").doesNotExist())
                .andReturn().getResponse().getContentAsString());
    }

    @Test void unauthenticatedRequestsCannotReadOrWrite() throws Exception {
        mvc.perform(get("/api/emotions/checkins")).andExpect(status().isUnauthorized());
        for (String path : List.of("/api/emotions/checkins", "/api/treehole/posts", "/api/match/needs")) {
            mvc.perform(post(path).contentType("application/json").content("{}"))
                    .andExpect(status().isUnauthorized());
        }
        assertEquals(0, jdbc.queryForObject("SELECT COUNT(*) FROM checkin", Integer.class));
    }

    @Test void ownershipComesOnlyFromVerifiedToken() throws Exception {
        JsonNode alice = login("alice"), bob = login("bob");
        assertEquals(alice.get("userId").asLong(), jwt.verify(alice.get("token").asText()));
        JsonNode a = checkin(alice, "private-a"), b = checkin(bob, "private-b");
        assertNotEquals(a.get("id"), b.get("id"));
        assertEquals(alice.get("userId").asLong(), jwt.verify(alice.get("token").asText()));
        mvc.perform(get("/api/emotions/checkins").param("userId", bob.get("userId").asText())
                .header("Authorization", "Bearer " + alice.get("token").asText()))
                .andExpect(status().isOk()).andExpect(jsonPath("$.total").value(1))
                .andExpect(jsonPath("$.items[0].note").value("private-a"))
                .andExpect(jsonPath("$.items[0].userId").doesNotExist());
        assertEquals(2, jdbc.queryForObject("SELECT COUNT(DISTINCT user_id) FROM checkin", Integer.class));
        assertTrue(jdbc.queryForList("SELECT openid FROM auth", String.class).stream()
                .allMatch(value -> value.matches("anon_v1_[A-Za-z0-9_-]{43}")));
    }

    @Test void anonymousIdentityUsesCallerAndNeverReturnsPrivateMapping() throws Exception {
        JsonNode alice = login("alice");
        var result = mvc.perform(post("/api/treehole/posts")
                .header("Authorization", "Bearer " + alice.get("token").asText())
                .contentType("application/json").content("{\"content\":\"synthetic\","
                        + "\"emotionTag\":\"CALM\",\"anonymous\":true,\"userId\":999999}"))
                .andExpect(status().isCreated()).andExpect(jsonPath("$.userId").doesNotExist())
                .andExpect(jsonPath("$.openid").doesNotExist()).andReturn();
        long id = json.readTree(result.getResponse().getContentAsString()).get("id").asLong();
        assertEquals(alice.get("userId").asLong(), jdbc.queryForObject(
                "SELECT user_id FROM treehole_identity WHERE post_id=?", Long.class, id));
    }

    @ParameterizedTest @ValueSource(strings = {
            "expired", "forged", "audience", "issuer", "subject", "no-expiry", "algorithm", "compressed"})
    void rejectsInvalidTokensWithoutEcho(String fault) throws Exception {
        JsonNode user = login("alice");
        JwtBuilder builder = Jwts.builder().setSubject(user.get("userId").asText())
                .setIssuer("ouc-tongpin").setAudience("ouc-miniprogram")
                .setIssuedAt(new Date()).setExpiration(new Date(System.currentTimeMillis() + 60_000));
        if (fault.equals("expired")) builder.setExpiration(new Date(1));
        if (fault.equals("audience")) builder.setAudience("another-app");
        if (fault.equals("issuer")) builder.setIssuer("another-issuer");
        if (fault.equals("subject")) builder.setSubject("9999999999999999999");
        if (fault.equals("no-expiry")) builder.setExpiration(null);
        if (fault.equals("compressed")) builder.compressWith(CompressionCodecs.DEFLATE);
        String key = fault.equals("forged") ? "different-identity-test-key-12345678901234567890" : KEY;
        String token = builder.signWith(Keys.hmacShaKeyFor(key.getBytes(StandardCharsets.UTF_8)),
                fault.equals("algorithm") ? SignatureAlgorithm.HS384 : SignatureAlgorithm.HS256).compact();
        String response = mvc.perform(get("/api/emotions/checkins")
                .header("Authorization", "Bearer " + token)).andExpect(status().isUnauthorized())
                .andReturn().getResponse().getContentAsString();
        assertFalse(response.contains(token));
    }

    @Test void disabledIdentityAndForgedAdminClaimsAreRejected() throws Exception {
        JsonNode user = login("alice");
        String elevated = Jwts.builder().setSubject(user.get("userId").asText())
                .setIssuer("ouc-tongpin").setAudience("ouc-miniprogram")
                .setIssuedAt(new Date()).setExpiration(new Date(System.currentTimeMillis() + 60000))
                .claim("roles", List.of("ADMIN")).signWith(
                        Keys.hmacShaKeyFor(KEY.getBytes(StandardCharsets.UTF_8)), SignatureAlgorithm.HS256)
                .compact();
        mvc.perform(get("/api/admin/identities").header("Authorization", "Bearer "
                + elevated)).andExpect(status().isForbidden());
        jdbc.update("UPDATE users SET deleted=1 WHERE id=?", user.get("userId").asLong());
        mvc.perform(get("/api/emotions/checkins").header("Authorization", "Bearer "
                + user.get("token").asText())).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/auth/login").contentType("application/json")
                .content("{\"code\":\"alice\"}")).andExpect(status().isUnauthorized());
    }

    @Test void concurrentIdentityCreationHasOneMappingAndNoOrphanUsers() throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(4);
        try {
            List<Future<JsonNode>> results = new ArrayList<>();
            for (int n = 0; n < 4; n++) results.add(pool.submit(() -> login("same-concurrent-code")));
            Set<String> ids = new HashSet<>();
            for (Future<JsonNode> result : results) ids.add(result.get(10, TimeUnit.SECONDS).get("userId").asText());
            assertEquals(1, ids.size());
            assertEquals(1, jdbc.queryForObject("SELECT COUNT(*) FROM users", Integer.class));
            assertEquals(1, jdbc.queryForObject("SELECT COUNT(*) FROM auth", Integer.class));
        } finally { pool.shutdownNow(); }
    }
}
