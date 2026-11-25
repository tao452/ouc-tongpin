package com.ouctongpin.apiserver.team.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 组队空间统一返回体。未加入任何组队时 inTeam=false，其余字段为 null。
 * 契约：ID 全部转 String，时间字段 ISO-8601。
 */
@Data
public class TeamResponse {
    private Boolean inTeam;
    private String id;
    private String name;
    private String notice;
    private Boolean isOwner;
    private String inviteCode;          // 撤销后为 null
    private LocalDateTime inviteExpiresAt;
    private List<Member> members;

    @Data
    public static class Member {
        private String userId;
        private String nickname;
        private String role;            // OWNER / MEMBER
        private LocalDateTime joinedAt;
    }
}
