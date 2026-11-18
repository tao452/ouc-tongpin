package com.ouctongpin.apiserver.buddy.dto;

import lombok.Data;

@Data
public class BuddyResponse {
    private String id;
    private String scene;
    private String status; // 必须是 "OPEN"
}
