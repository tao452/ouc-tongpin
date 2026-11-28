package com.ouctongpin.apiserver.buddy.dto;

import lombok.Data;

import java.util.List;

/**
 * US-11 square list item. Built only from persisted buddy_demand columns;
 * fields absent from the table (e.g. participant count) use explicit neutral values.
 */
@Data
public class SquareItemResponse {
    private String id;
    private String title;
    private String description;
    private String category;
    private String scene;
    private String time;
    private String location;
    /** Distance in km; null when the caller did not supply coordinates. */
    private Double distance;
    private List<String> tags;
    /** The table has no participant column; only the publisher is known. */
    private Integer peopleCount = 1;
    private String publishTime;
    private String publishText;
    private String status;
}
