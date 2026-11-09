package com.ouctongpin.apiserver.treehole.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

@Data
public class PostCreateReq {
    @NotBlank(message = "内容不能为空")
    @Size(max = 500, message = "内容不能超过 500 字符")
    private String content;            // ≤500

    @NotNull(message = "emotionTag 不能为空")
    @Pattern(regexp = "HAPPY|CALM|ANXIOUS|LONELY|IRRITABLE|DOWN", message = "emotionTag 不合法")
    private String emotionTag;         // HAPPY/CALM/ANXIOUS/LONELY/IRRITABLE/DOWN

    private Boolean anonymous = true;  // 一键切换匿名/实名，默认匿名
}
