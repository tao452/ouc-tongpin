package com.ouctongpin.apiserver.user.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** US-35 tag row, see infra/db/init/01-schema.sql (user_tag). */
@Data
@TableName("user_tag")
public class UserTag {
    @TableId(type = IdType.AUTO)
    private Long id;
    /** Internal identity only; never accepted from the request body. */
    private Long userId;
    /** "INTEREST" or "SKILL". */
    private String tagType;
    private String tagName;
    private LocalDateTime createdAt;
}
