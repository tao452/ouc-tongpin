package com.ouctongpin.apiserver.buddy.dto;

import lombok.Data;
import java.math.BigDecimal;

@Data
public class BuddyQueryReq {
    // 游标：上一次查询的最后一条记录的 id，第一次查传 0 或 null
    private Long cursorId = 0L;

    // 用户当前经纬度
    private BigDecimal myLongitude;
    private BigDecimal myLatitude;

    // 范围（米），默认 5000 米
    private Integer radius = 5000;

    // 每页数量
    private Integer size = 10;
}
