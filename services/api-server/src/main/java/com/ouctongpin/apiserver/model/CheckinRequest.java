package com.ouctongpin.apiserver.model;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

/** 提交打卡请求（对应 POST /api/emotions/checkins 请求体） */
public class CheckinRequest {
    @NotNull
    public String emotion;

    @NotNull
    @Min(1)
    @Max(5)
    public int intensity;

    public String note;          // 可选，<=100 字（接入后校验）

    public String checkinDate;   // 可选，YYYY-MM-DD，不传按服务端当天
}
