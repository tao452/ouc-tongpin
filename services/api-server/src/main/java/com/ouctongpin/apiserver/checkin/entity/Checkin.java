package com.ouctongpin.apiserver.checkin.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("checkin")
public class Checkin {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long userId;
    private String emotion;          // HAPPY/CALM/ANXIOUS/LONELY/IRRITABLE/DOWN（对应契约枚举）
    private Integer intensity;       // 1-5
    private String note;             // 可选备注，≤100
    private LocalDate checkinDate;
    @TableField(exist = false)
    private Integer streakDays;      // 计算字段，不落库
    private LocalDateTime createdAt;
}
