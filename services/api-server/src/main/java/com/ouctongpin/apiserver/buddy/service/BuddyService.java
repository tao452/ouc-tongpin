package com.ouctongpin.apiserver.buddy.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.buddy.dto.BuddyCreateReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyQueryReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyResponse;
import com.ouctongpin.apiserver.buddy.entity.BuddyDemand;
import com.ouctongpin.apiserver.buddy.mapper.BuddyDemandMapper;
import com.ouctongpin.apiserver.moderation.ModerationClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/** US-10 publishing. Listing/filtering/sorting is V1.0 #12 and intentionally absent. */
@Service
public class BuddyService {

    static final ZoneId BEIJING = ZoneId.of("Asia/Shanghai");
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Autowired private BuddyDemandMapper buddyMapper;
    @Autowired private ModerationClient moderationClient;

    // 👇 新增 Redis 和 ObjectMapper 注入，供广场查询使用
    @Autowired private StringRedisTemplate redisTemplate;
    @Autowired private ObjectMapper objectMapper;

    public BuddyResponse createNeed(Long userId, BuddyCreateReq req) {
        // Audit before any database write. HIGH hits -> 422, unavailable dependency -> 503.
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

    public List<BuddyResponse> getSquareList(BuddyQueryReq req) {
        // 缓存 key 必须包含所有影响结果的查询参数，否则不同 radius/size 会串用同一份结果。
        String cacheKey = "square:" + req.getCursorId() + ":" + req.getMyLongitude() + ":"
            + req.getMyLatitude() + ":" + req.getRadius() + ":" + req.getSize();

        String cachedJson = redisTemplate.opsForValue().get(cacheKey);
        if (cachedJson != null) {
            try {
                return objectMapper.readValue(cachedJson,
                    objectMapper.getTypeFactory().constructCollectionType(List.class, BuddyResponse.class));
            } catch (JsonProcessingException e) {
                // 缓存内容损坏时忽略缓存、回源查询，不让脏缓存影响结果。
                redisTemplate.delete(cacheKey);
            }
        }

        LambdaQueryWrapper<BuddyDemand> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(BuddyDemand::getStatus, "OPEN");

        if (req.getCursorId() != null && req.getCursorId() > 0) {
            wrapper.lt(BuddyDemand::getId, req.getCursorId());
        }

        if (req.getMyLongitude() != null && req.getMyLatitude() != null) {
            wrapper.apply("ST_Distance_Sphere(point(longitude, latitude), point({0}, {1})) <= {2}",
                req.getMyLongitude(), req.getMyLatitude(), req.getRadius());
        }

        wrapper.orderByDesc(BuddyDemand::getId).last("LIMIT " + req.getSize());
        List<BuddyDemand> demands = buddyMapper.selectList(wrapper);

        List<BuddyResponse> responses = demands.stream().map(d -> {
            BuddyResponse r = new BuddyResponse();
            r.setId(String.valueOf(d.getId()));
            r.setScene(d.getScene());
            r.setStatus(d.getStatus());
            return r;
        }).collect(Collectors.toList());

        try {
            redisTemplate.opsForValue().set(cacheKey, objectMapper.writeValueAsString(responses),
                60, TimeUnit.SECONDS);
        } catch (JsonProcessingException e) {
            // 序列化失败不应影响本次查询结果，交由全局异常处理器兜底即可。
            throw new IllegalStateException("缓存序列化失败", e);
        }
        return responses;
    }
}
