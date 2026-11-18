package com.ouctongpin.apiserver.auth.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.time.LocalDateTime;

@Data
@JsonIgnoreProperties({"userId", "openid", "studentNo", "phone"})
@TableName("auth")
public class Auth {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long userId;
    private String openid;
    private String studentNo;
    private String phone;
    private LocalDateTime createdAt;

    @Override public String toString() { return "Auth[private]"; }
}
