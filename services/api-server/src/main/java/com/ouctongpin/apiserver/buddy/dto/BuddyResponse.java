package com.ouctongpin.apiserver.buddy.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class BuddyResponse {
    private Long id;
    private String title;
    private String description;
    private String scene;
    private LocalDateTime eventTime;
    private String locationName;
    private String skillTags;
    private LocalDateTime createdAt;
}
