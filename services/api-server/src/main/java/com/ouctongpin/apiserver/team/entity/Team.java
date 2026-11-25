package com.ouctongpin.apiserver.team.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("team")
public class Team {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String name;
    private String notice;           // 组队公告，仅组长可改
    @JsonIgnore
    private Long ownerUserId;
    @JsonIgnore
    private String inviteCode;       // 撤销后置 NULL
    @JsonIgnore
    private LocalDateTime inviteExpiresAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    @JsonIgnore
    private Integer deleted;
}
