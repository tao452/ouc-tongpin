package com.ouctongpin.apiserver.buddy.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;
import org.hibernate.validator.constraints.CodePointLength;

import java.math.BigDecimal;
import java.util.List;

/**
 * Request body of POST /api/match/needs (US-10).
 * Field names and bounds come from packages/contract/openapi.yaml:249-287.
 * Do not add fields that are not in the contract: the miniprogram publish page already
 * serialises exactly scene / time / location / skillTags / remark.
 */
@Data
public class BuddyCreateReq {

    @NotBlank(message = "场景不能为空")
    @Size(max = 64, message = "场景不能超过 64 字符")
    private String scene;

    /** ISO-8601. The miniprogram sends toISOString() (UTC, trailing Z); accept local too. */
    @NotBlank(message = "时间不能为空")
    private String time;

    @NotNull(message = "地点不能为空")
    @Valid
    private Location location;

    @Size(max = 5, message = "技能标签最多 5 个")
    private List<String> skillTags;

    @CodePointLength(max = 200, message = "补充说明不能超过 200 字符")
    private String remark;

    @Data
    public static class Location {
        @NotBlank(message = "地点地址不能为空")
        @Size(max = 255, message = "地点地址不能超过 255 字符")
        private String address;

        @DecimalMin(value = "-90", message = "纬度不能小于 -90")
        @DecimalMax(value = "90", message = "纬度不能大于 90")
        private BigDecimal lat;
        @DecimalMin(value = "-180", message = "经度不能小于 -180")
        @DecimalMax(value = "180", message = "经度不能大于 180")
        private BigDecimal lng;
    }
}
