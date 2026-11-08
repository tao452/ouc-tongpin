package com.ouctongpin.apiserver.treehole.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class PostResponse {
    private Long id;
    private String anonymousId;
    private String content;
    private LocalDateTime createdAt;
}
