package com.ouctongpin.apiserver.privacy;

import com.ouctongpin.apiserver.treehole.scheduler.BurnTask;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.util.DigestUtils;

import java.nio.charset.StandardCharsets;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** Actual MyBatis, row locks and transactions; Redis is a controllable isolated test double. */
@SpringBootTest(classes = BurnTaskPrivacyTest.TestApplication.class, properties = {
        "spring.datasource.url=jdbc:h2:mem:w3-burn;MODE=MySQL;DB_CLOSE_DELAY=-1",
        "spring.datasource.driver-class-name=org.h2.Driver",
        "spring.datasource.username=sa", "spring.datasource.password=",
        "spring.sql.init.mode=never", "spring.main.banner-mode=off"
})
class BurnTaskPrivacyTest {
    @Configuration
    @EnableAutoConfiguration
    @MapperScan("com.ouctongpin.apiserver.treehole.mapper")
    @Import(BurnTask.class)
    static class TestApplication {}

    private static final String CONTENT = "synthetic expired privacy content";
    @Autowired BurnTask task;
    @Autowired JdbcTemplate jdbc;
    @MockBean StringRedisTemplate redis;
    private ZSetOperations<String, String> queue;

    @BeforeEach @SuppressWarnings("unchecked")
    void setup() {
        jdbc.execute("DROP TABLE IF EXISTS identity_guard");
        jdbc.execute("DROP TABLE IF EXISTS treehole_identity");
        jdbc.execute("DROP TABLE IF EXISTS treehole_archive");
        jdbc.execute("DROP TABLE IF EXISTS treehole_post");
        jdbc.execute("CREATE TABLE treehole_post (id BIGINT AUTO_INCREMENT PRIMARY KEY, "
                + "anonymous_id VARCHAR(64) NOT NULL, content TEXT, emotion_tag VARCHAR(16), "
                + "anonymous INT, is_burn_after_read INT, status INT, created_at TIMESTAMP, "
                + "expires_at TIMESTAMP, deleted INT)");
        jdbc.execute("CREATE TABLE treehole_identity (post_id BIGINT PRIMARY KEY, "
                + "user_id BIGINT NOT NULL, created_at TIMESTAMP, "
                + "FOREIGN KEY(post_id) REFERENCES treehole_post(id))");
        jdbc.execute("CREATE TABLE treehole_archive (id BIGINT AUTO_INCREMENT PRIMARY KEY, "
                + "post_id BIGINT, content_hash VARCHAR(64), created_at TIMESTAMP)");
        jdbc.update("INSERT INTO treehole_post(id, anonymous_id, content, emotion_tag, anonymous, "
                + "is_burn_after_read, status, deleted, expires_at) VALUES "
                + "(42, 'anon_v1_synthetic-private-alias', ?, 'CALM', 1, 1, 0, 0, '2000-01-01')", CONTENT);
        jdbc.update("INSERT INTO treehole_identity(post_id,user_id) VALUES (42,7)");
        queue = mock(ZSetOperations.class);
        when(redis.opsForZSet()).thenReturn(queue);
        when(queue.rangeByScore(eq("treehole:burn_queue"), anyDouble(), anyDouble()))
                .thenReturn(Set.of("42"));
        when(queue.remove("treehole:burn_queue", "42")).thenReturn(1L);
    }

    private int count(String table) {
        return jdbc.queryForObject("SELECT COUNT(*) FROM " + table, Integer.class);
    }

    private void assertBurned() {
        assertEquals(1, jdbc.queryForObject("SELECT status FROM treehole_post WHERE id=42", Integer.class));
        assertEquals("burned", jdbc.queryForObject("SELECT anonymous_id FROM treehole_post WHERE id=42", String.class));
        assertEquals("该内容已焚毁", jdbc.queryForObject("SELECT content FROM treehole_post WHERE id=42", String.class));
        assertEquals(0, count("treehole_identity"));
        assertEquals(1, count("treehole_archive"));
        assertEquals(DigestUtils.md5DigestAsHex(CONTENT.getBytes(StandardCharsets.UTF_8)),
                jdbc.queryForObject("SELECT content_hash FROM treehole_archive WHERE post_id=42", String.class));
    }

    @Test void burningAtomicallyRemovesIdentityAndLinkableAlias() {
        // Redis acknowledgement runs only after all durable privacy changes committed.
        doAnswer(invocation -> {
            assertBurned();
            return 1L;
        }).when(queue).remove("treehole:burn_queue", "42");
        task.scanAndBurn();
        assertBurned();
    }

    @Test void identityCleanupFailureRollsBackArchiveAndContentAndKeepsRetryEntry() {
        jdbc.execute("CREATE TABLE identity_guard (post_id BIGINT PRIMARY KEY, "
                + "FOREIGN KEY(post_id) REFERENCES treehole_identity(post_id))");
        jdbc.update("INSERT INTO identity_guard VALUES (42)");
        assertThrows(DataIntegrityViolationException.class, () -> task.scanAndBurn());
        assertEquals(CONTENT, jdbc.queryForObject("SELECT content FROM treehole_post WHERE id=42", String.class));
        assertEquals(0, jdbc.queryForObject("SELECT status FROM treehole_post WHERE id=42", Integer.class));
        assertEquals(1, count("treehole_identity"));
        assertEquals(0, count("treehole_archive"));
        verify(queue, never()).remove(anyString(), any());
    }

    @Test void redisAcknowledgementFailureCanRetryWithoutDuplicatingArchive() {
        when(queue.remove("treehole:burn_queue", "42"))
                .thenThrow(new IllegalStateException("synthetic retry"))
                .thenReturn(1L);
        assertThrows(IllegalStateException.class, () -> task.scanAndBurn());
        assertBurned();
        task.scanAndBurn();
        assertBurned();
        verify(queue, times(2)).remove("treehole:burn_queue", "42");
    }

    @Test void alreadyBurnedLegacyRecordLosesItsOldIdentityWithoutNewArchive() {
        jdbc.update("UPDATE treehole_post SET status=1, content='该内容已焚毁' WHERE id=42");
        task.scanAndBurn();
        assertEquals("burned", jdbc.queryForObject("SELECT anonymous_id FROM treehole_post WHERE id=42", String.class));
        assertEquals(0, count("treehole_identity"));
        assertEquals(0, count("treehole_archive"));
    }
}
