package com.ouctongpin.apiserver.treehole.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("treehole_post")
public class TreeholePost {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long userId;             // 真实用户，绝不返回给前端
    private String anonymousId;      // 匿名马甲（不可反推）
    private String content;
    private String emotionTag;       // HAPPY/CALM/...
    private Integer anonymous;       // 0 实名 / 1 匿名
    private Integer isBurnAfterRead; // 0 否 1 是
    private Integer status;           // 0 正常 1 已焚毁
    private LocalDateTime createdAt;
    private LocalDateTime expiresAt;  // 24h 焚毁时间
    private Integer deleted;
}
