package com.ouctongpin.apiserver.model;

/**
 * 打卡记录（对应契约 components.schemas.Checkin）
 * 骨架阶段用 public 字段便于直接序列化；接入 JPA 后改为实体类 + getter。
 */
public class Checkin {
    public String id;
    public String checkinDate;   // YYYY-MM-DD
    public String emotion;       // HAPPY/CALM/ANXIOUS/LONELY/IRRITABLE/DOWN
    public int intensity;        // 1-5
    public String note;          // 备注，可空
    public int streakDays;       // 连续打卡天数
}
