package com.ouctongpin.apiserver.treehole.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class PostResponse {
    private Long id;
    private String content;
    private String emotionTag;
    private Boolean anonymous;
    private String authorMask;      // 匿名态=不可反推掩码(anonymousId)；实名态=昵称
    private LocalDateTime createdAt;
    private LocalDateTime expiresAt; // 24h 后焚毁时间
    private Integer hugCount;        // 抱抱数，暂置 0（每人每帖每日限 1 次，待 Redis 接入）
}
