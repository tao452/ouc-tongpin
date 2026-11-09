package com.ouctongpin.apiserver.treehole.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ouctongpin.apiserver.treehole.dto.PostCreateReq;
import com.ouctongpin.apiserver.treehole.dto.PostResponse;
import com.ouctongpin.apiserver.treehole.entity.TreeholePost;
import com.ouctongpin.apiserver.treehole.mapper.TreeholePostMapper;
import com.ouctongpin.apiserver.moderation.ModerationClient;
import com.ouctongpin.apiserver.privacy.AnonymousIdGenerator;
import com.ouctongpin.apiserver.auth.mapper.UserMapper;
import com.ouctongpin.apiserver.auth.entity.User;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class TreeholeService {
    @Autowired private TreeholePostMapper postMapper;
    @Autowired private StringRedisTemplate redisTemplate;
    @Autowired private ModerationClient moderationClient;
    @Autowired private AnonymousIdGenerator anonymousIds;
    @Autowired private UserMapper userMapper;

    // 发布（契约：POST /api/treehole/posts）
    public TreeholePost createPost(Long userId, PostCreateReq req) {
        // Audit before any database or Redis write; HIGH and dependency failures abort publication.
        moderationClient.requireAllowed(req.getContent());

        TreeholePost post = new TreeholePost();
        post.setUserId(userId);
        post.setContent(req.getContent());
        post.setEmotionTag(req.getEmotionTag());
        post.setAnonymous(req.getAnonymous() != null && req.getAnonymous() ? 1 : 0);
        post.setAnonymousId(anonymousIds.generate(String.valueOf(userId), "treehole"));
        post.setIsBurnAfterRead(1);   // US-07：默认 24h 焚毁
        post.setStatus(0);
        LocalDateTime created = LocalDateTime.now(ZoneOffset.ofHours(8));
        post.setCreatedAt(created);
        post.setExpiresAt(created.plusHours(24));
        post.setDeleted(0);
        postMapper.insert(post);

        // 2. 加入 Redis ZSet 延时焚毁队列（24h 后触发）
        long burnTime = post.getExpiresAt().toInstant(ZoneOffset.of("+8")).toEpochMilli();
        redisTemplate.opsForZSet().add("treehole:burn_queue", String.valueOf(post.getId()), burnTime);

        return post;
    }

    public PostResponse toResponse(TreeholePost post) {
        PostResponse response = new PostResponse();
        response.setId(post.getId());
        response.setContent(post.getContent());
        response.setEmotionTag(post.getEmotionTag());
        boolean anonymous = Integer.valueOf(1).equals(post.getAnonymous());
        response.setAnonymous(anonymous);
        String mask = post.getAnonymousId();
        if (!anonymous) {
            User user = userMapper.selectById(post.getUserId());
            mask = user == null || user.getNickname() == null ? "用户" : user.getNickname();
        }
        response.setAuthorMask(mask);
        response.setCreatedAt(post.getCreatedAt());
        response.setExpiresAt(post.getExpiresAt());
        response.setHugCount(0);
        return response;
    }

    // 列表（契约：GET /api/treehole/posts?emotionTag&cursor）
    public Map<String, Object> listPosts(String emotionTag, String cursor) {
        int pageNum = 1;
        if (cursor != null && !cursor.isBlank()) {
            try { pageNum = Integer.parseInt(cursor); } catch (NumberFormatException ignored) {}
        }
        int pageSize = 10;

        Page<TreeholePost> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<TreeholePost> wrapper = new LambdaQueryWrapper<TreeholePost>()
                .eq(TreeholePost::getStatus, 0)
                .eq(TreeholePost::getDeleted, 0)
                .gt(TreeholePost::getExpiresAt, LocalDateTime.now(ZoneOffset.ofHours(8)))
                .eq(emotionTag != null && !emotionTag.isBlank(), TreeholePost::getEmotionTag, emotionTag)
                .orderByDesc(TreeholePost::getCreatedAt)
                .orderByDesc(TreeholePost::getId);
        postMapper.selectPage(page, wrapper);

        List<PostResponse> records = page.getRecords().stream()
                .map(this::toResponse).collect(Collectors.toList());

        Map<String, Object> res = new HashMap<>();
        res.put("items", records);
        res.put("nextCursor", page.hasNext() ? String.valueOf(pageNum + 1) : null);
        return res;
    }
}
