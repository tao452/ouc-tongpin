package com.ouctongpin.apiserver.buddy.dto;

import lombok.Data;

/** 201 response of POST /api/match/needs. id is a string per the contract. */
@Data
public class BuddyResponse {
    private String id;
    private String scene;
    private String status;
}
