package com.ouctongpin.apiserver.user.entity;

import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * The profile columns of the existing users table (US-35).
 * Kept separate from auth.entity.User so profile writes stay in the user module;
 * both map to the same table. Fields here are exactly the ones PUT /api/user/profile owns.
 */
@Data
@TableName("users")
public class UserProfile {
    @TableId
    private Long id;
    private String nickname;
    /** Contract field avatarUrl is stored in the existing avatar column. */
    private String avatar;
    private String bio;
    private LocalDateTime updatedAt;
}
