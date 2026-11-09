package com.ouctongpin.apiserver.checkin.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDate;

@Data
public class CheckinReq {
    @NotNull(message = "emotion 不能为空")
    @Pattern(regexp = "HAPPY|CALM|ANXIOUS|LONELY|IRRITABLE|DOWN", message = "emotion 不合法")
    private String emotion;     // HAPPY/CALM/ANXIOUS/LONELY/IRRITABLE/DOWN

    @NotNull(message = "intensity 不能为空")
    @Min(value = 1, message = "intensity 必须在 1–5 之间")
    @Max(value = 5, message = "intensity 必须在 1–5 之间")
    private Integer intensity;  // 1-5

    @Size(max = 100, message = "note 不能超过 100 字符")
    private String note;        // 可选备注，≤100

    private LocalDate checkinDate; // 可选，默认当天
}
