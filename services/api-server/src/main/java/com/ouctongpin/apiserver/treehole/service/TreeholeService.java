package com.ouctongpin.apiserver.treehole.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ouctongpin.apiserver.treehole.dto.PostCreateReq;
import com.ouctongpin.apiserver.treehole.dto.PostResponse;
import com.ouctongpin.apiserver.treehole.entity.TreeholePost;
import com.ouctongpin.apiserver.treehole.mapper.TreeholePostMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class TreeholeService {
    @Autowired private TreeholePostMapper postMapper;
    @Autowired private StringRedisTemplate redisTemplate;

    // 发帖
    public Long createPost(Long userId, PostCreateReq req) {
        // 1. 模拟 M6 敏感词前置调用
        if (req.getContent().contains("违规词")) {
            throw new RuntimeException("内容包含敏感词，拒绝发布");
        }

        TreeholePost post = new TreeholePost();
        post.setUserId(userId);
        // 生成一个简单的匿名马甲（真实业务中应该根据 userId 做哈希加盐）
        post.setAnonymousId("匿名用户_" + (userId % 1000));
        post.setContent(req.getContent());
        post.setIsBurnAfterRead(req.getIsBurnAfterRead() != null && req.getIsBurnAfterRead() ? 1 : 0);
        post.setStatus(0);
        postMapper.insert(post);

        // 2. 如果是阅后即焚，存入 Redis ZSet
        if (post.getIsBurnAfterRead() == 1) {
            // 假设 10 分钟后焚毁（这里为了方便测试，设为 60 秒）
            long burnTime = System.currentTimeMillis() + 60 * 1000;
            redisTemplate.opsForZSet().add("treehole:burn_queue", String.valueOf(post.getId()), burnTime);
        }

        return post.getId();
    }

    // 分页查列表
    public Page<PostResponse> listPosts(int pageNum, int pageSize) {
        Page<TreeholePost> page = new Page<>(pageNum, pageSize);
        // 只查未焚毁且未删除的
        LambdaQueryWrapper<TreeholePost> wrapper = new LambdaQueryWrapper<TreeholePost>()
            .eq(TreeholePost::getStatus, 0)
            .eq(TreeholePost::getDeleted, 0)
            .orderByDesc(TreeholePost::getCreatedAt);

        postMapper.selectPage(page, wrapper);

        // 把 Entity 转换成不含 userId 的 DTO
        Page<PostResponse> resPage = new Page<>(page.getCurrent(), page.getSize(), page.getTotal());
        List<PostResponse> records = page.getRecords().stream().map(p -> {
            PostResponse r = new PostResponse();
            r.setId(p.getId());
            r.setAnonymousId(p.getAnonymousId());
            r.setContent(p.getContent());
            r.setCreatedAt(p.getCreatedAt());
            return r;
        }).collect(Collectors.toList());
        resPage.setRecords(records);

        return resPage;
    }
}
