package com.ouctongpin.apiserver.buddy.dto;

import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class BuddyResponse {
    private String id;          // 满足契约要求
    private String scene;       // 满足契约要求
    private String status;      // 满足契约要求

    // 下面这些是列表和广场查询需要的展示字段
    private String title;
    private String description;
    private LocalDateTime eventTime;
    private String locationName;
    private List<String> skillTags;
    private LocalDateTime createdAt;
}
