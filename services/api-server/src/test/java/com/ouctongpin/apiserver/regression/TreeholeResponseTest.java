package com.ouctongpin.apiserver.regression;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.auth.entity.User;
import com.ouctongpin.apiserver.auth.mapper.UserMapper;
import com.ouctongpin.apiserver.moderation.ModerationClient;
import com.ouctongpin.apiserver.privacy.AnonymousIdGenerator;
import com.ouctongpin.apiserver.treehole.dto.PostCreateReq;
import com.ouctongpin.apiserver.treehole.entity.TreeholePost;
import com.ouctongpin.apiserver.treehole.mapper.TreeholePostMapper;
import com.ouctongpin.apiserver.treehole.service.TreeholeService;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.Duration;
import java.time.Instant;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class TreeholeResponseTest {
    private final TreeholeService service = new TreeholeService();
    private final UserMapper users = mock(UserMapper.class);

    TreeholeResponseTest() {
        ReflectionTestUtils.setField(service, "userMapper", users);
    }

    @Test void anonymousResponseDoesNotSerializeInternalIdentityOrDatabaseFlags() throws Exception {
        TreeholePost post = new TreeholePost();
        post.setId(11L);
        post.setUserId(987654L);
        post.setAnonymous(1);
        post.setAnonymousId(new AnonymousIdGenerator("synthetic-test-secret-at-least-32-bytes")
                .generate("987654", "treehole"));
        post.setContent("synthetic content");
        var response = service.toResponse(post);
        var json = new ObjectMapper().findAndRegisterModules().valueToTree(response);
        assertTrue(response.getAnonymous());
        assertTrue(response.getAuthorMask().startsWith("anon_v1_"));
        assertFalse(json.has("userId"));
        assertFalse(json.has("anonymousId"));
        assertFalse(json.has("deleted"));
        assertFalse(json.toString().contains("987654"));
        verifyNoInteractions(users);
    }

    @Test void namedResponseUsesNicknameOnly() {
        User user = new User();
        user.setNickname("Synthetic Nickname");
        when(users.selectById(1L)).thenReturn(user);
        TreeholePost post = new TreeholePost();
        post.setUserId(1L);
        post.setAnonymous(0);
        assertEquals("Synthetic Nickname", service.toResponse(post).getAuthorMask());
    }

    @Test @SuppressWarnings("unchecked")
    void burnQueueUsesTheActualTwentyFourHourDeadline() {
        TreeholePostMapper posts = mock(TreeholePostMapper.class);
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ZSetOperations<String, String> queue = mock(ZSetOperations.class);
        when(redis.opsForZSet()).thenReturn(queue);
        ReflectionTestUtils.setField(service, "postMapper", posts);
        ReflectionTestUtils.setField(service, "redisTemplate", redis);
        ReflectionTestUtils.setField(service, "moderationClient", mock(ModerationClient.class));
        ReflectionTestUtils.setField(service, "anonymousIds",
                new AnonymousIdGenerator("synthetic-test-secret-at-least-32-bytes"));
        PostCreateReq request = new PostCreateReq();
        request.setContent("synthetic content");
        request.setEmotionTag("CALM");
        Instant before = Instant.now();
        TreeholePost post = service.createPost(1L, request);
        assertEquals(Duration.ofHours(24), Duration.between(post.getCreatedAt(), post.getExpiresAt()));
        var score = org.mockito.ArgumentCaptor.forClass(Double.class);
        verify(queue).add(eq("treehole:burn_queue"), anyString(), score.capture());
        double delta = score.getValue() - before.toEpochMilli();
        assertTrue(delta >= 86_400_000 && delta < 86_410_000);
    }
}
