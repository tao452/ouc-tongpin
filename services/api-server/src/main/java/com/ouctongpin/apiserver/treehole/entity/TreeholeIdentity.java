package com.ouctongpin.apiserver.treehole.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonIgnoreType;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;

import java.time.LocalDateTime;

/** Private identity mapping; never include this entity in public responses or logs. */
@Data
@JsonIgnoreType
@JsonIgnoreProperties({"postId", "userId", "createdAt"})
@TableName("treehole_identity")
public class TreeholeIdentity {
    @TableId(type = IdType.INPUT)
    private Long postId;
    private Long userId;
    private LocalDateTime createdAt;

    @Override
    public String toString() {
        return "TreeholeIdentity[REDACTED]";
    }
}
