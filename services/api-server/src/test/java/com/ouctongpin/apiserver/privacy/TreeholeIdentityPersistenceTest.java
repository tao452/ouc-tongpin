package com.ouctongpin.apiserver.privacy;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.moderation.ModerationClient;
import com.ouctongpin.apiserver.treehole.dto.PostCreateReq;
import com.ouctongpin.apiserver.treehole.entity.TreeholeIdentity;
import com.ouctongpin.apiserver.treehole.service.TreeholeService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.jdbc.core.JdbcTemplate;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** Real MyBatis/JDBC writes and Spring transactions; synthetic data, isolated in-memory DB. */
@SpringBootTest(classes = TreeholeIdentityPersistenceTest.TestApplication.class, properties = {
        "spring.datasource.url=jdbc:h2:mem:w3-privacy;MODE=MySQL;DB_CLOSE_DELAY=-1",
        "spring.datasource.driver-class-name=org.h2.Driver",
        "spring.datasource.username=sa", "spring.datasource.password=",
        "spring.sql.init.mode=never", "spring.main.banner-mode=off"
})
class TreeholeIdentityPersistenceTest {
    @Configuration
    @EnableAutoConfiguration
    @MapperScan({"com.ouctongpin.apiserver.treehole.mapper", "com.ouctongpin.apiserver.auth.mapper"})
    @Import(TreeholeService.class)
    static class TestApplication {
        @Bean AnonymousIdGenerator anonymousIds() {
            return new AnonymousIdGenerator("w3-synthetic-private-secret-at-least-32-bytes");
        }
    }

    @Autowired TreeholeService service;
    @Autowired JdbcTemplate jdbc;
    @MockBean ModerationClient moderation;
    @MockBean StringRedisTemplate redis;
    private ZSetOperations<String, String> queue;

    @BeforeEach @SuppressWarnings("unchecked")
    void setup() {
        jdbc.execute("DROP TABLE IF EXISTS treehole_identity");
        jdbc.execute("DROP TABLE IF EXISTS treehole_post");
        jdbc.execute("DROP TABLE IF EXISTS users");
        jdbc.execute("CREATE TABLE treehole_post (id BIGINT AUTO_INCREMENT PRIMARY KEY, "
                + "anonymous_id VARCHAR(64) NOT NULL, content TEXT, emotion_tag VARCHAR(16), "
                + "anonymous INT, is_burn_after_read INT, status INT, created_at TIMESTAMP, "
                + "expires_at TIMESTAMP, deleted INT)");
        jdbc.execute("CREATE TABLE treehole_identity (post_id BIGINT PRIMARY KEY, "
                + "user_id BIGINT NOT NULL CHECK (user_id > 0), created_at TIMESTAMP, "
                + "FOREIGN KEY(post_id) REFERENCES treehole_post(id))");
        jdbc.execute("CREATE TABLE users (id BIGINT PRIMARY KEY, nickname VARCHAR(64), avatar VARCHAR(512), "
                + "created_at TIMESTAMP, updated_at TIMESTAMP, deleted INT)");
        jdbc.update("INSERT INTO users(id, nickname, deleted) VALUES (7, 'Synthetic Nickname', 0)");
        queue = mock(ZSetOperations.class);
        when(redis.opsForZSet()).thenReturn(queue);
        when(queue.add(anyString(), anyString(), anyDouble())).thenReturn(true);
    }

    private PostCreateReq request(boolean anonymous) {
        PostCreateReq request = new PostCreateReq();
        request.setContent("synthetic privacy content");
        request.setEmotionTag("CALM");
        request.setAnonymous(anonymous);
        return request;
    }

    @Test void contentHasOnlyAliasAndIdentityLivesInSeparateTable() throws Exception {
        var post = service.createPost(7L, request(true));
        assertEquals(0, jdbc.queryForObject("SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                + "WHERE TABLE_NAME='TREEHOLE_POST' AND COLUMN_NAME='USER_ID'", Integer.class));
        assertEquals(7L, jdbc.queryForObject("SELECT user_id FROM treehole_identity WHERE post_id=?",
                Long.class, post.getId()));
        assertTrue(jdbc.queryForObject("SELECT anonymous_id FROM treehole_post WHERE id=?",
                String.class, post.getId()).matches("anon_v1_[A-Za-z0-9_-]{43}"));
        var json = new ObjectMapper().findAndRegisterModules().valueToTree(service.toResponse(post));
        for (String name : new String[]{"userId", "anonymousId", "openid", "studentNo", "phone"}) {
            assertFalse(json.has(name));
        }
        var second = service.createPost(7L, request(true));
        assertEquals(post.getAnonymousId(), second.getAnonymousId());
        assertEquals(2, jdbc.queryForObject("SELECT COUNT(*) FROM treehole_identity", Integer.class));
    }

    @Test void namedResponseResolvesNicknameThroughPrivateMapping() {
        var post = service.createPost(7L, request(false));
        assertEquals("Synthetic Nickname", service.toResponse(post).getAuthorMask());
        jdbc.update("DELETE FROM treehole_identity WHERE post_id=?", post.getId());
        assertEquals("用户", service.toResponse(post).getAuthorMask());
    }

    @Test void mappingFailureRollsBackContentBeforeRedisWrite() {
        jdbc.execute("ALTER TABLE treehole_identity ADD CONSTRAINT reject_synthetic_user CHECK (user_id <> 7)");
        assertThrows(DataIntegrityViolationException.class, () -> service.createPost(7L, request(true)));
        assertEquals(0, jdbc.queryForObject("SELECT COUNT(*) FROM treehole_post", Integer.class));
        assertEquals(0, jdbc.queryForObject("SELECT COUNT(*) FROM treehole_identity", Integer.class));
        verifyNoInteractions(queue);
    }

    @Test void redisFailureRollsBackContentAndPrivateIdentity() {
        when(queue.add(anyString(), anyString(), anyDouble())).thenThrow(new IllegalStateException("synthetic offline"));
        assertThrows(IllegalStateException.class, () -> service.createPost(7L, request(true)));
        assertEquals(0, jdbc.queryForObject("SELECT COUNT(*) FROM treehole_post", Integer.class));
        assertEquals(0, jdbc.queryForObject("SELECT COUNT(*) FROM treehole_identity", Integer.class));
    }

    @Test void privateMappingCannotBeSerializedOrLoggedByItsGeneratedAccessors() throws Exception {
        TreeholeIdentity identity = new TreeholeIdentity();
        identity.setUserId(987654321L);
        identity.setPostId(12345L);
        assertEquals("{}", new ObjectMapper().writeValueAsString(identity));
        assertEquals("TreeholeIdentity[REDACTED]", identity.toString());
    }
}
