package com.ouctongpin.apiserver.buddy.dto;

import lombok.Data;
import java.math.BigDecimal;

@Data
public class BuddyQueryReq {
    private Long cursorId = 0L;
    private BigDecimal myLongitude;
    private BigDecimal myLatitude;
    private Integer radius = 5000;
    private Integer size = 10;
}
