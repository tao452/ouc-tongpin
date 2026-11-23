package com.ouctongpin.apiserver.buddy.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import java.math.BigDecimal;

@Data
public class BuddyQueryReq {
    @Min(value = 0, message = "cursorId 不能为负数")
    private Long cursorId = 0L;
    @DecimalMin(value = "-180", message = "经度不能小于 -180")
    @DecimalMax(value = "180", message = "经度不能大于 180")
    private BigDecimal myLongitude;
    @DecimalMin(value = "-90", message = "纬度不能小于 -90")
    @DecimalMax(value = "90", message = "纬度不能大于 90")
    private BigDecimal myLatitude;
    @NotNull
    @Min(value = 1, message = "radius 必须大于 0")
    @Max(value = 50000, message = "radius 不能超过 50000 米")
    private Integer radius = 5000;
    @NotNull
    @Min(value = 1, message = "size 必须大于 0")
    @Max(value = 50, message = "size 不能超过 50")
    private Integer size = 10;
}
