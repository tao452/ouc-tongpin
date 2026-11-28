package com.ouctongpin.apiserver.buddy.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.buddy.dto.BuddyCreateReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyQueryReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyResponse;
import com.ouctongpin.apiserver.buddy.dto.SquareItemResponse;
import com.ouctongpin.apiserver.buddy.entity.BuddyDemand;
import com.ouctongpin.apiserver.buddy.mapper.BuddyDemandMapper;
import com.ouctongpin.apiserver.moderation.ModerationClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.Duration;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Set;
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
        // 新需求必须立即出现在广场：清掉分页/坐标组合的旧缓存，避免 60 秒内返回空列表。
        invalidateSquareCache();

        BuddyResponse response = new BuddyResponse();
        response.setId(String.valueOf(demand.getId()));
        response.setScene(demand.getScene());
        response.setStatus(demand.getStatus());
        return response;
    }

    /** 发布需求后清理广场的全部缓存键；缓存未建立时（如测试环境）直接跳过。 */
    private void invalidateSquareCache() {
        Set<String> keys = redisTemplate.keys("square:*");
        if (keys != null && !keys.isEmpty()) {
            redisTemplate.delete(keys);
        }
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

    public List<SquareItemResponse> getSquareList(BuddyQueryReq req) {
        // 缓存 key 必须包含所有影响结果的查询参数，否则不同 radius/size 会串用同一份结果。
        String cacheKey = "square:" + req.getCursorId() + ":" + req.getMyLongitude() + ":"
            + req.getMyLatitude() + ":" + req.getRadius() + ":" + req.getSize();

        String cachedJson = redisTemplate.opsForValue().get(cacheKey);
        if (cachedJson != null) {
            try {
                return objectMapper.readValue(cachedJson,
                    objectMapper.getTypeFactory().constructCollectionType(List.class, SquareItemResponse.class));
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

        List<SquareItemResponse> responses = demands.stream()
            .map(d -> toSquareItem(d, req))
            .collect(Collectors.toList());

        try {
            redisTemplate.opsForValue().set(cacheKey, objectMapper.writeValueAsString(responses),
                60, TimeUnit.SECONDS);
        } catch (JsonProcessingException e) {
            // 序列化失败不应影响本次查询结果，交由全局异常处理器兜底即可。
            throw new IllegalStateException("缓存序列化失败", e);
        }
        return responses;
    }

    /** Map persisted columns into the fields the mini-program card renders. */
    private SquareItemResponse toSquareItem(BuddyDemand d, BuddyQueryReq req) {
        SquareItemResponse r = new SquareItemResponse();
        String scene = d.getScene() == null ? "" : d.getScene();

        r.setId(String.valueOf(d.getId()));
        r.setScene(scene);
        r.setTitle(scene.isEmpty() ? "搭子需求" : scene);
        r.setDescription(d.getRemark() == null ? "" : d.getRemark());
        r.setCategory(inferCategory(scene));
        r.setTime(d.getEventTime() == null
            ? "时间待定"
            : d.getEventTime().format(DateTimeFormatter.ofPattern("MM-dd HH:mm")));
        r.setLocation(d.getLocationAddress() == null ? "地点待定" : d.getLocationAddress());
        r.setTags(parseTags(d.getSkillTags()));
        r.setDistance(distanceKm(req, d));
        r.setPublishTime(d.getCreatedAt() == null ? null : d.getCreatedAt().toString());
        r.setPublishText(relativeTime(d.getCreatedAt()));
        r.setStatus(d.getStatus());
        return r;
    }

    /** Category is derived from the free-text scene; the table has no category column. */
    private static String inferCategory(String scene) {
        if (scene.matches(".*(考研|学习|英语|编程|课程|考试|自习|算法|复习|高数|笔试).*")) {
            return "学习交流";
        }
        if (scene.matches(".*(运动|健身|羽毛球|休闲|桌游|摄影|散步|娱乐|游戏|兴趣).*")) {
            return "生活兴趣";
        }
        return "其他";
    }

    private List<String> parseTags(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            List<String> tags = objectMapper.readValue(json, new TypeReference<List<String>>() {});
            return tags == null ? List.of() : tags;
        } catch (JsonProcessingException e) {
            return List.of();
        }
    }

    /** Haversine distance in km; null when either coordinate is unavailable. */
    private static Double distanceKm(BuddyQueryReq req, BuddyDemand d) {
        if (req.getMyLongitude() == null || req.getMyLatitude() == null
            || d.getLongitude() == null || d.getLatitude() == null) {
            return null;
        }
        double lat1 = Math.toRadians(req.getMyLatitude().doubleValue());
        double lat2 = Math.toRadians(d.getLatitude().doubleValue());
        double dLat = lat2 - lat1;
        double dLon = Math.toRadians(
            d.getLongitude().doubleValue() - req.getMyLongitude().doubleValue());
        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
            + Math.cos(lat1) * Math.cos(lat2)
            * Math.sin(dLon / 2) * Math.sin(dLon / 2);
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return Math.round(6371.0 * c * 10) / 10.0;
    }

    private static String relativeTime(LocalDateTime createdAt) {
        if (createdAt == null) {
            return "发布时间未知";
        }
        long minutes = Duration.between(createdAt, LocalDateTime.now(BEIJING)).toMinutes();
        if (minutes < 1) return "刚刚发布";
        if (minutes < 60) return minutes + "分钟前";
        long hours = minutes / 60;
        if (hours < 24) return hours + "小时前";
        return (hours / 24) + "天前";
    }
}
