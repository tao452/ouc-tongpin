package com.ouctongpin.apiserver.treehole.scheduler;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.ouctongpin.apiserver.treehole.entity.TreeholeArchive;
import com.ouctongpin.apiserver.treehole.entity.TreeholePost;
import com.ouctongpin.apiserver.treehole.mapper.TreeholeArchiveMapper;
import com.ouctongpin.apiserver.treehole.mapper.TreeholePostMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.util.DigestUtils;

import java.nio.charset.StandardCharsets;
import java.util.Set;

@Component
public class BurnTask {
    @Autowired private StringRedisTemplate redisTemplate;
    @Autowired private TreeholePostMapper postMapper;
    @Autowired private TreeholeArchiveMapper archiveMapper;

    // 每 10 秒跑一次扫描
    @Scheduled(fixedRate = 10000)
    public void scanAndBurn() {
        long now = System.currentTimeMillis();
        // 从 Redis ZSet 获取 Score 小于等于当前时间的帖子 ID
        Set<String> ids = redisTemplate.opsForZSet().rangeByScore("treehole:burn_queue", 0, now);

        if (ids == null || ids.isEmpty()) return;

        for (String idStr : ids) {
            Long postId = Long.parseLong(idStr);
            TreeholePost post = postMapper.selectById(postId);

            if (post != null && post.getStatus() == 0) {
                // 1. 记录哈希留档
                String hash = DigestUtils.md5DigestAsHex(post.getContent().getBytes(StandardCharsets.UTF_8));
                TreeholeArchive archive = new TreeholeArchive();
                archive.setPostId(postId);
                archive.setContentHash(hash);
                archiveMapper.insert(archive);

                // 2. 软删除，清空内容
                post.setStatus(1); // 已焚毁
                post.setContent("该内容已焚毁");
                postMapper.updateById(post);
            }
            // 3. 从 Redis 移除
            redisTemplate.opsForZSet().remove("treehole:burn_queue", idStr);
        }
    }
}
