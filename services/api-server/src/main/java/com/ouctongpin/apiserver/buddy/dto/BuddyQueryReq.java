package com.ouctongpin.apiserver.buddy.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;
import java.math.BigDecimal;

@Data
public class BuddyQueryReq {
    @Min(value = 0, message = "cursorId 不能为负数")
    private Long cursorId = 0L;
    private BigDecimal myLongitude;
    private BigDecimal myLatitude;
    @Min(value = 1, message = "radius 必须大于 0")
    @Max(value = 50000, message = "radius 不能超过 50000 米")
    private Integer radius = 5000;
    @Min(value = 1, message = "size 必须大于 0")
    @Max(value = 50, message = "size 不能超过 50")
    private Integer size = 10;
}
