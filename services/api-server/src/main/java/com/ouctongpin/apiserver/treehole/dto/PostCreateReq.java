package com.ouctongpin.apiserver.treehole.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class PostCreateReq {
    @NotBlank(message = "内容不能为空")
    private String content;

    // 是否阅后即焚
    private Boolean isBurnAfterRead;
}
