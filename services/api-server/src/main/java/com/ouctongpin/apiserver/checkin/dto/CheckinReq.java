package com.ouctongpin.apiserver.checkin.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.time.LocalDate;

@Data
public class CheckinReq {
    @NotNull(message = "emotion 不能为空")
    private String emotion;     // HAPPY/CALM/ANXIOUS/LONELY/IRRITABLE/DOWN

    @NotNull(message = "intensity 不能为空")
    private Integer intensity;  // 1-5

    private String note;        // 可选备注，≤100

    private LocalDate checkinDate; // 可选，默认当天
}
