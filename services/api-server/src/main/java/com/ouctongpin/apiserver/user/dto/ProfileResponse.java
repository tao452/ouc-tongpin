package com.ouctongpin.apiserver.user.dto;

import lombok.Data;

import java.util.List;

/** Response of PUT /api/user/profile: echoes the normalised stored profile. */
@Data
public class ProfileResponse {
    private String nickname;
    private String avatarUrl;
    private String bio;
    private List<String> interestTags;
    private List<String> skillTags;
}
