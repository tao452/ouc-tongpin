package com.ouctongpin.apiserver.buddy.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("buddy_demand")
public class BuddyDemand {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long userId;
    private String title;
    private String description;
    private String scene;
    private LocalDateTime eventTime;
    private String locationName;
    private BigDecimal longitude;
    private BigDecimal latitude;
    private String skillTags;
    private Integer status;
    private LocalDateTime createdAt;
    private Integer deleted;
}
