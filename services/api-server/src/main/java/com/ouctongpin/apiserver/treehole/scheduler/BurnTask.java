package com.ouctongpin.apiserver.treehole.scheduler;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.ouctongpin.apiserver.treehole.entity.TreeholeArchive;
import com.ouctongpin.apiserver.treehole.entity.TreeholePost;
import com.ouctongpin.apiserver.treehole.mapper.TreeholeArchiveMapper;
import com.ouctongpin.apiserver.treehole.mapper.TreeholeIdentityMapper;
import com.ouctongpin.apiserver.treehole.mapper.TreeholePostMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.util.DigestUtils;

import java.nio.charset.StandardCharsets;
import java.util.Set;

@Component
public class BurnTask {
    @Autowired private StringRedisTemplate redisTemplate;
    @Autowired private TreeholePostMapper postMapper;
    @Autowired private TreeholeIdentityMapper identityMapper;
    @Autowired private TreeholeArchiveMapper archiveMapper;
    @Autowired private TransactionTemplate transactions;

    // 每 10 秒跑一次扫描
    @Scheduled(fixedRate = 10000)
    public void scanAndBurn() {
        long now = System.currentTimeMillis();
        // 从 Redis ZSet 获取 Score 小于等于当前时间的帖子 ID
        Set<String> ids = redisTemplate.opsForZSet().rangeByScore("treehole:burn_queue", 0, now);

        if (ids == null || ids.isEmpty()) return;

        for (String idStr : ids) {
            Long postId = Long.parseLong(idStr);
            // Each post commits independently. Do not remove its retry entry before DB commit.
            transactions.executeWithoutResult(status -> burnPost(postId));
            redisTemplate.opsForZSet().remove("treehole:burn_queue", idStr);
        }
    }

    private void burnPost(Long postId) {
        // Row lock prevents two workers from archiving the same post concurrently.
        TreeholePost post = postMapper.selectOne(new LambdaQueryWrapper<TreeholePost>()
                .eq(TreeholePost::getId, postId).last("FOR UPDATE"));
        if (post == null) return;
        if (Integer.valueOf(0).equals(post.getStatus())) {
            String hash = DigestUtils.md5DigestAsHex(post.getContent().getBytes(StandardCharsets.UTF_8));
            TreeholeArchive archive = new TreeholeArchive();
            archive.setPostId(postId);
            archive.setContentHash(hash);
            if (archiveMapper.insert(archive) != 1) {
                throw new IllegalStateException("Burn archive could not be persisted");
            }
            post.setStatus(1);
            post.setContent("该内容已焚毁");
        }
        if (Integer.valueOf(1).equals(post.getStatus())) {
            // A burned record retains no link to its former author, including its HMAC alias.
            identityMapper.deleteById(postId);
            post.setAnonymousId("burned");
            if (postMapper.updateById(post) != 1) {
                throw new IllegalStateException("Burned content could not be updated");
            }
        }
    }
}
