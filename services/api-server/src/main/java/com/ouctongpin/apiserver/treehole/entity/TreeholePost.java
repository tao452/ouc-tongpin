package com.ouctongpin.apiserver.treehole.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("treehole_post")
public class TreeholePost {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long userId; // 真实用户，绝不返回给前端
    private String anonymousId; // 匿名马甲
    private String content;
    private Integer isBurnAfterRead; // 0否 1是
    private Integer status; // 0正常 1已焚毁
    private LocalDateTime createdAt;
    private Integer deleted;
}
