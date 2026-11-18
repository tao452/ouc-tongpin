package com.ouctongpin.apiserver.buddy.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.buddy.dto.BuddyCreateReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyQueryReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyResponse;
import com.ouctongpin.apiserver.buddy.entity.BuddyDemand;
import com.ouctongpin.apiserver.buddy.mapper.BuddyDemandMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeParseException;
import java.util.Arrays;
import java.util.Collections;
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
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "时间格式错误，请提供 ISO-8601 格式");
        }
        try {
            // 匹配带时区的时间
            if (timeStr.contains("Z") || timeStr.contains("+") || timeStr.matches(".*-\\d{2}:\\d{2}$")) {
                OffsetDateTime odt = OffsetDateTime.parse(timeStr);
                // 统一转为北京时间
                return odt.atZoneSameInstant(ZoneId.of("Asia/Shanghai")).toLocalDateTime();
            } else {
                // 匹配本地时间
                return LocalDateTime.parse(timeStr);
            }
        } catch (DateTimeParseException e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "时间格式错误，请提供 ISO-8601 格式");
        }
    }

    public Long createBuddy(Long userId, BuddyCreateReq req) {
        // 前置敏感词拦截
        if (req.getRemark() != null && (req.getRemark().contains("违规") || req.getScene().contains("违规"))) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "审核拒绝：内容包含敏感词");
        }

        BuddyDemand demand = new BuddyDemand();
        demand.setUserId(userId);
        demand.setScene(req.getScene());

        // 调用测试过的时间解析方法
        demand.setEventTime(parseEventTime(req.getTime()));

        if (req.getLocation() != null) {
            demand.setLocationAddress(req.getLocation().getAddress());
            demand.setLatitude(req.getLocation().getLat());
            demand.setLongitude(req.getLocation().getLng());
        }

        if (req.getSkillTags() != null && !req.getSkillTags().isEmpty()) {
            demand.setSkillTags(String.join(",", req.getSkillTags()));
        }

        demand.setRemark(req.getRemark());
        demand.setStatus("OPEN");

        buddyMapper.insert(demand);
        return demand.getId();
    }

    public Page<BuddyResponse> listBuddies(int pageNum, int pageSize, String scene) {
        Page<BuddyDemand> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<BuddyDemand> wrapper = new LambdaQueryWrapper<>();

        wrapper.eq(BuddyDemand::getDeleted, 0).eq(BuddyDemand::getStatus, "OPEN");

        if (scene != null && !scene.isEmpty()) {
            wrapper.eq(BuddyDemand::getScene, scene);
        }
        wrapper.orderByDesc(BuddyDemand::getCreatedAt);
        buddyMapper.selectPage(page, wrapper);

        Page<BuddyResponse> resPage = new Page<>(page.getCurrent(), page.getSize(), page.getTotal());
        List<BuddyResponse> records = page.getRecords().stream()
            .map(this::convertToResponse)
            .collect(Collectors.toList());
        resPage.setRecords(records);
        return resPage;
    }

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

        List<BuddyResponse> responses = demands.stream()
            .map(this::convertToResponse)
            .collect(Collectors.toList());

        redisTemplate.opsForValue().set(cacheKey, objectMapper.writeValueAsString(responses), 60, TimeUnit.SECONDS);
        return responses;
    }

    private BuddyResponse convertToResponse(BuddyDemand d) {
        BuddyResponse r = new BuddyResponse();
        r.setId(String.valueOf(d.getId()));
        r.setScene(d.getScene());
        r.setStatus(d.getStatus());

        r.setTitle(d.getScene() + "搭子");
        r.setDescription(d.getRemark());
        r.setEventTime(d.getEventTime());
        r.setLocationName(d.getLocationAddress());

        if (d.getSkillTags() != null && !d.getSkillTags().isEmpty()) {
            r.setSkillTags(Arrays.asList(d.getSkillTags().split(",")));
        } else {
            r.setSkillTags(Collections.emptyList());
        }

        r.setCreatedAt(d.getCreatedAt());
        return r;
    }
}
