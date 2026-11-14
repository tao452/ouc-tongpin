package com.ouctongpin.apiserver.buddy.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class BuddyCreateReq {
    @NotBlank(message = "标题不能为空")
    private String title;

    private String description;

    @NotBlank(message = "场景不能为空")
    private String scene;

    @NotNull(message = "时间不能为空")
    private LocalDateTime eventTime;

    private String locationName;
    private BigDecimal longitude;
    private BigDecimal latitude;
    private String skillTags;
}
