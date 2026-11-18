package com.ouctongpin.apiserver.buddy.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.buddy.dto.BuddyCreateReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyResponse;
import com.ouctongpin.apiserver.buddy.entity.BuddyDemand;
import com.ouctongpin.apiserver.buddy.mapper.BuddyDemandMapper;
import com.ouctongpin.apiserver.moderation.ModerationClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.format.DateTimeParseException;
import java.util.List;

/** US-10 publishing. Listing/filtering/sorting is V1.0 #12 and intentionally absent. */
@Service
public class BuddyService {

    static final ZoneId BEIJING = ZoneId.of("Asia/Shanghai");
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Autowired private BuddyDemandMapper buddyMapper;
    @Autowired private ModerationClient moderationClient;

    public BuddyResponse createNeed(Long userId, BuddyCreateReq req) {
        // Audit before any database write. HIGH hits -> 422, unavailable dependency -> 503.
        // Same rule as TreeholeService.createPost(); never silently allow an unchecked write.
        String text = req.getScene() + " " + (req.getRemark() == null ? "" : req.getRemark());
        moderationClient.requireAllowed(text);

        BuddyDemand demand = new BuddyDemand();
        demand.setUserId(userId);
        demand.setScene(req.getScene());
        demand.setEventTime(parseEventTime(req.getTime()));
        demand.setLocationAddress(req.getLocation().getAddress());
        demand.setLatitude(req.getLocation().getLat());
        demand.setLongitude(req.getLocation().getLng());
        demand.setSkillTags(toJson(req.getSkillTags()));
        demand.setRemark(req.getRemark());
        demand.setStatus("OPEN");
        demand.setCreatedAt(LocalDateTime.now(ZoneOffset.ofHours(8)));
        demand.setDeleted(0);
        buddyMapper.insert(demand);

        BuddyResponse response = new BuddyResponse();
        response.setId(String.valueOf(demand.getId()));
        response.setScene(demand.getScene());
        response.setStatus(demand.getStatus());
        return response;
    }

    /** Accepts UTC ("...Z"), offset ("...+08:00") and local ISO date-time, stores Beijing time. */
    static LocalDateTime parseEventTime(String raw) {
        try {
            if (raw.endsWith("Z") || raw.matches(".*[+-]\\d{2}:\\d{2}$")) {
                return OffsetDateTime.parse(raw).atZoneSameInstant(BEIJING).toLocalDateTime();
            }
            return LocalDateTime.parse(raw);
        } catch (DateTimeParseException e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "time 必须是 ISO-8601 时间");
        }
    }

    private static String toJson(List<String> tags) {
        if (tags == null || tags.isEmpty()) {
            return null;
        }
        try {
            return MAPPER.writeValueAsString(tags);
        } catch (JsonProcessingException e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "skillTags 格式不合法");
        }
    }
}
