package com.ouctongpin.apiserver.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class LoginReq {
    @NotBlank(message = "code不能为空")
    @Size(max = 128, message = "code过长")
    private String code;
}
