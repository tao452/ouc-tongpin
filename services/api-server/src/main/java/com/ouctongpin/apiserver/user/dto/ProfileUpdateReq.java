package com.ouctongpin.apiserver.user.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

/**
 * Request body of PUT /api/user/profile (US-35).
 * Bounds mirror apps/miniprogram/utils/profile.js LIMITS and the contract description:
 * nickname <= 20, bio <= 100, at most 8 tags, each tag <= 12 chars.
 * avatarUrl maps to the existing users.avatar column; no new storage is introduced for it.
 * There is deliberately no userId field: ownership comes only from the verified token.
 */
@Data
public class ProfileUpdateReq {

    @NotBlank(message = "昵称不能为空")
    @Size(max = 20, message = "昵称不能超过 20 字")
    private String nickname;

    @Size(max = 512, message = "头像地址不能超过 512 字符")
    private String avatarUrl;

    @Size(max = 100, message = "简介不能超过 100 字")
    private String bio;

    @Valid
    @Size(max = 8, message = "兴趣标签最多 8 个")
    private List<@NotBlank(message = "兴趣标签不能为空") @Size(max = 12, message = "兴趣标签单个不能超过 12 字") String> interestTags;

    @Valid
    @Size(max = 8, message = "技能标签最多 8 个")
    private List<@NotBlank(message = "技能标签不能为空") @Size(max = 12, message = "技能标签单个不能超过 12 字") String> skillTags;
}
