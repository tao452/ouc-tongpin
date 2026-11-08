package com.ouctongpin.apiserver.auth.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class LoginReq {
    @NotBlank(message = "code不能为空")
    private String code;
}
