package com.ouctongpin.apiserver.team.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class JoinByCodeReq {
    @NotBlank(message = "邀请码不能为空")
    private String inviteCode;
}
