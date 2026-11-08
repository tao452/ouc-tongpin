package com.ouctongpin.apiserver.auth.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("auth")
public class Auth {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long userId;
    private String openid;
    private String studentNo;
    private String phone;
    private LocalDateTime createdAt;
}
