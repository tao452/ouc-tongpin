package com.ouctongpin.apiserver.profile.dto;

import lombok.Data;

import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** US-04 画像周聚合。本周无任何打卡时各项为 0 / 空集合，不报错（无数据兜底）。 */
@Data
public class WeeklyProfileResponse {
    private String weekStart;            // ISO 日期，周一
    private String weekEnd;              // ISO 日期，周日
    private int daysCheckedIn;           // 本周打卡天数（去重）
    private int totalCheckins;           // 本周打卡条数
    private Double avgIntensity;         // 平均强度 1~5，无数据为 0.0
    private int streakDays;              // 截至本周的连续打卡天数
    private Map<String, Integer> emotionCounts = new LinkedHashMap<>(); // 情绪分布
    private List<DayPoint> trend = List.of();  // 逐日曲线

    @Data
    public static class DayPoint {
        private LocalDate date;
        private String emotion;
        private Integer intensity;
    }
}
