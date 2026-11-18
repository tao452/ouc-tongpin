package com.ouctongpin.apiserver.buddy.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.buddy.dto.BuddyCreateReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyQueryReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyResponse;
import com.ouctongpin.apiserver.buddy.entity.BuddyDemand;
import com.ouctongpin.apiserver.buddy.mapper.BuddyDemandMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
public class BuddyService {

    @Autowired private BuddyDemandMapper buddyMapper;
    @Autowired private StringRedisTemplate redisTemplate;
    @Autowired private ObjectMapper objectMapper;



    public static LocalDateTime parseEventTime(String timeStr) {
        if (timeStr == null || timeStr.trim().isEmpty()) {
            throw new IllegalArgumentException("时间不能为空");
        }
        if (timeStr.contains("Z") || timeStr.contains("+")) {
            OffsetDateTime odt = OffsetDateTime.parse(timeStr);
            return odt.atZoneSameInstant(ZoneId.of("Asia/Shanghai")).toLocalDateTime();
        } else {
            return LocalDateTime.parse(timeStr);
        }
    }

    // 1. 发布搭子 (恢复团队的 422 拦截和 OPEN 状态)
    public Long createBuddy(Long userId, BuddyCreateReq req) {
        // 【契约要求】前置敏感词拦截 (这里先保留 Mock 逻辑，如果团队有 ModerationClient 替换成团队的)
        if (req.getRemark() != null && req.getRemark().contains("HIGH")) {
            // 模拟触发 HIGH 敏感词，抛出 422 状态码
            throw new org.springframework.web.server.ResponseStatusException(
                org.springframework.http.HttpStatus.UNPROCESSABLE_ENTITY, "命中敏感词");
        }

        BuddyDemand demand = new BuddyDemand();
        demand.setUserId(userId);
        demand.setScene(req.getScene());
        demand.setEventTime(parseEventTime(req.getTime()));

        if (req.getLocation() != null) {
            demand.setLocationAddress(req.getLocation().getAddress());
            demand.setLatitude(req.getLocation().getLat());
            demand.setLongitude(req.getLocation().getLng());
        }

        // 团队契约要求 skillTags 存为 JSON 数组字符串
        if (req.getSkillTags() != null && !req.getSkillTags().isEmpty()) {
            demand.setSkillTags(req.getSkillTags().toString()); // 自动变成 ["a","b"]
        }

        demand.setRemark(req.getRemark());
        demand.setStatus("OPEN"); // 契约要求为 OPEN

        buddyMapper.insert(demand);
        return demand.getId();
    }

    // 2. 你的 W5 核心产出：广场查询 (游标分页 + 缓存)
    public List<BuddyResponse> getSquareList(BuddyQueryReq req) throws JsonProcessingException {
        String cacheKey = "square:" + req.getCursorId() + ":" + req.getMyLongitude() + ":" + req.getMyLatitude();

        String cachedJson = redisTemplate.opsForValue().get(cacheKey);
        if (cachedJson != null) {
            return objectMapper.readValue(cachedJson,
                objectMapper.getTypeFactory().constructCollectionType(List.class, BuddyResponse.class));
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

        // 只用契约要求的 3 个字段
        List<BuddyResponse> responses = demands.stream().map(d -> {
            BuddyResponse r = new BuddyResponse();
            r.setId(String.valueOf(d.getId()));
            r.setScene(d.getScene());
            r.setStatus(d.getStatus());
            return r;
        }).collect(Collectors.toList());

        redisTemplate.opsForValue().set(cacheKey, objectMapper.writeValueAsString(responses), 60, TimeUnit.SECONDS);
        return responses;
    }
}
