package com.ouctongpin.apiserver.treehole.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ouctongpin.apiserver.treehole.dto.PostCreateReq;
import com.ouctongpin.apiserver.treehole.dto.PostResponse;
import com.ouctongpin.apiserver.treehole.entity.TreeholePost;
import com.ouctongpin.apiserver.treehole.mapper.TreeholePostMapper;
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

    // 发布（契约：POST /api/treehole/posts）
    public TreeholePost createPost(Long userId, PostCreateReq req) {
        // 1. 模拟 M6 敏感词前置调用（真实应调用 /api/moderation/check）
        if (req.getContent().contains("违规词")) {
            throw new RuntimeException("内容包含敏感词，拒绝发布");
        }

        TreeholePost post = new TreeholePost();
        post.setUserId(userId);
        post.setContent(req.getContent());
        post.setEmotionTag(req.getEmotionTag());
        post.setAnonymous(req.getAnonymous() != null && req.getAnonymous() ? 1 : 0);
        // 匿名态下生成不可反推马甲（真实业务应对 userId 做哈希加盐）
        post.setAnonymousId("匿名用户_" + (userId % 1000));
        post.setIsBurnAfterRead(1);   // US-07：默认 24h 焚毁
        post.setStatus(0);
        post.setExpiresAt(LocalDateTime.now().plusHours(24));
        post.setDeleted(0);
        postMapper.insert(post);

        // 2. 加入 Redis ZSet 延时焚毁队列（24h 后触发）
        long burnTime = post.getExpiresAt().toInstant(ZoneOffset.of("+8")).toEpochMilli();
        redisTemplate.opsForZSet().add("treehole:burn_queue", String.valueOf(post.getId()), burnTime);

        return post;
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
                .eq(emotionTag != null && !emotionTag.isBlank(), TreeholePost::getEmotionTag, emotionTag)
                .orderByDesc(TreeholePost::getCreatedAt);
        postMapper.selectPage(page, wrapper);

        List<PostResponse> records = page.getRecords().stream().map(p -> {
            PostResponse r = new PostResponse();
            r.setId(p.getId());
            r.setContent(p.getContent());
            r.setEmotionTag(p.getEmotionTag());
            r.setAnonymous(p.getAnonymous() == 1);
            r.setAuthorMask(p.getAnonymousId());
            r.setCreatedAt(p.getCreatedAt());
            r.setExpiresAt(p.getExpiresAt());
            r.setHugCount(0);
            return r;
        }).collect(Collectors.toList());

        Map<String, Object> res = new HashMap<>();
        res.put("items", records);
        res.put("nextCursor", page.hasNext() ? String.valueOf(pageNum + 1) : null);
        return res;
    }
}
