package com.ouctongpin.apiserver.team.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class TeamCreateReq {
    @NotBlank(message = "组队名称不能为空")
    @Size(max = 32, message = "组队名称最多 32 字")
    private String name;

    @Size(max = 200, message = "公告最多 200 字")
    private String notice;
}
