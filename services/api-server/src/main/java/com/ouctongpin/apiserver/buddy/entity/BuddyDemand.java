package com.ouctongpin.apiserver.buddy.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/** Persisted match need, see infra/db/init/01-schema.sql (buddy_demand). */
@Data
@TableName("buddy_demand")
public class BuddyDemand {
    @TableId(type = IdType.AUTO)
    private Long id;
    /** Internal identity only; never returned to the client. */
    private Long userId;
    private String scene;
    /** Normalised to Asia/Shanghai local date-time before insert. */
    private LocalDateTime eventTime;
    private String locationAddress;
    private BigDecimal latitude;
    private BigDecimal longitude;
    /** JSON array string, e.g. ["高数","线代"]; null when no tags were supplied. */
    private String skillTags;
    private String remark;
    /** "OPEN" by default, matches the contract response. */
    private String status;
    private LocalDateTime createdAt;
    private Integer deleted;
}
