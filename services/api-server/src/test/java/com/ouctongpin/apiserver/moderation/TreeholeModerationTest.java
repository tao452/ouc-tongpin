package com.ouctongpin.apiserver.moderation;

import com.ouctongpin.apiserver.treehole.dto.PostCreateReq;
import com.ouctongpin.apiserver.treehole.entity.TreeholePost;
import com.ouctongpin.apiserver.treehole.mapper.TreeholePostMapper;
import com.ouctongpin.apiserver.treehole.service.TreeholeService;
import com.ouctongpin.apiserver.privacy.AnonymousIdGenerator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class TreeholeModerationTest {
    @Mock private ModerationClient moderation;
    @Mock private TreeholePostMapper posts;
    @Mock private StringRedisTemplate redis;
    @Mock private ZSetOperations<String, String> burnQueue;
    @Mock private AnonymousIdGenerator anonymousIds;
    @InjectMocks private TreeholeService service;

    private PostCreateReq request(String content) {
        PostCreateReq request = new PostCreateReq();
        request.setContent(content);
        request.setEmotionTag("CALM");
        request.setAnonymous(true);
        return request;
    }

    @ParameterizedTest
    @ValueSource(ints = {422, 503})
    void blockedOrUnavailableNeverTouchesDatabaseOrRedis(int status) {
        when(moderation.requireAllowed("synthetic content")).thenThrow(
                new ResponseStatusException(HttpStatus.valueOf(status), "safe reason"));
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.createPost(1L, request("synthetic content")));
        assertEquals(status, error.getStatusCode().value());
        verifyNoInteractions(posts, redis, burnQueue);
    }

    @ParameterizedTest
    @ValueSource(strings = {"NONE", "LOW", "MEDIUM"})
    void allowedContentIsCheckedBeforePersistence(String level) {
        List<ModerationClient.Hit> hits = level.equals("NONE") ? List.of() : List.of(
                new ModerationClient.Hit("synthetic term", ModerationClient.Level.valueOf(level)));
        when(moderation.requireAllowed("synthetic content")).thenReturn(
                new ModerationClient.Result(true, "syntheticcontent", hits));
        when(posts.insert(any(TreeholePost.class))).thenAnswer(invocation -> {
            ((TreeholePost) invocation.getArgument(0)).setId(123L);
            return 1;
        });
        when(redis.opsForZSet()).thenReturn(burnQueue);
        when(anonymousIds.generate("1", "treehole")).thenReturn("anon_v1_synthetic");
        TreeholePost post = service.createPost(1L, request("synthetic content"));
        assertEquals("synthetic content", post.getContent());
        var order = inOrder(moderation, posts, redis, burnQueue);
        order.verify(moderation).requireAllowed("synthetic content");
        order.verify(posts).insert(post);
        order.verify(redis).opsForZSet();
        order.verify(burnQueue).add(eq("treehole:burn_queue"), eq("123"), anyDouble());
    }

    @Test void invalidContentDoesNotReachPersistence() {
        when(moderation.requireAllowed(" ")).thenThrow(
                new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid content"));
        assertThrows(ResponseStatusException.class, () -> service.createPost(1L, request(" ")));
        verifyNoInteractions(posts, redis, burnQueue);
    }
}
