package com.ouctongpin.apiserver.team.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("team_member")
public class TeamMember {
    @TableId(type = IdType.AUTO)
    private Long id;
    @JsonIgnore
    private Long teamId;
    @JsonIgnore
    private Long userId;
    private String role;             // OWNER / MEMBER
    private LocalDateTime joinedAt;
    @JsonIgnore
    private Integer deleted;
}
