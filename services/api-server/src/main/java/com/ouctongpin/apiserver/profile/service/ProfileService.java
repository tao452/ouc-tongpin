package com.ouctongpin.apiserver.profile.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.checkin.entity.Checkin;
import com.ouctongpin.apiserver.checkin.mapper.CheckinMapper;
import com.ouctongpin.apiserver.checkin.service.CheckinService;
import com.ouctongpin.apiserver.profile.dto.WeeklyProfileResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.DayOfWeek;
import java.time.Duration;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** US-04 画像聚合：按自然周聚合打卡数据，Redis 缓存 10 分钟，无数据兜底。 */
@Service
public class ProfileService {

    static final ZoneId BEIJING = ZoneId.of("Asia/Shanghai");
    /** 缓存 10 分钟；打卡时主动清缓存，保证画像与打卡一致。 */
    static final Duration CACHE_TTL = Duration.ofMinutes(10);
    /** 与打卡契约一致的情绪枚举顺序，前端画图不用再排序。 */
    private static final List<String> EMOTION_ORDER =
        List.of("HAPPY", "CALM", "ANXIOUS", "LONELY", "IRRITABLE", "DOWN");

    @Autowired private CheckinMapper checkinMapper;
    @Autowired private CheckinService checkinService;
    @Autowired private StringRedisTemplate redisTemplate;
    @Autowired private ObjectMapper objectMapper;

    /** 周聚合入口。date 可选（默认按北京时间的今天定位所在周），周起点为周一。 */
    public WeeklyProfileResponse weekly(Long userId, LocalDate date) {
        LocalDate ref = (date != null) ? date : LocalDate.now(BEIJING);
        LocalDate weekStart = ref.with(DayOfWeek.MONDAY);
        String cacheKey = cacheKey(userId, weekStart);

        String cachedJson = redisTemplate.opsForValue().get(cacheKey);
        if (cachedJson != null) {
            try {
                return objectMapper.readValue(cachedJson, WeeklyProfileResponse.class);
            } catch (JsonProcessingException e) {
                // 缓存损坏不阻塞请求：删掉回源
                redisTemplate.delete(cacheKey);
            }
        }

        WeeklyProfileResponse resp = aggregate(userId, weekStart);
        // 无数据不缓存：该周第一针打卡打进来时能立刻看到画像变化
        if (resp.getTotalCheckins() > 0) {
            try {
                redisTemplate.opsForValue().set(cacheKey, objectMapper.writeValueAsString(resp), CACHE_TTL);
            } catch (JsonProcessingException e) {
                throw new IllegalStateException("画像缓存序列化失败", e);
            }
        }
        return resp;
    }

    /** 打卡写入后调用，保证“画像数据与打卡一致”。 */
    public void evictWeeklyCache(Long userId, LocalDate anyDateInWeek) {
        redisTemplate.delete(cacheKey(userId, anyDateInWeek.with(DayOfWeek.MONDAY)));
    }

    private String cacheKey(Long userId, LocalDate weekStart) {
        return "profile:weekly:" + userId + ":" + weekStart;
    }

    private WeeklyProfileResponse aggregate(Long userId, LocalDate weekStart) {
        LocalDate weekEnd = weekStart.plusDays(6);
        List<Checkin> items = checkinMapper.selectList(new LambdaQueryWrapper<Checkin>()
            .eq(Checkin::getUserId, userId)
            .ge(Checkin::getCheckinDate, weekStart)
            .le(Checkin::getCheckinDate, weekEnd)
            .orderByAsc(Checkin::getCheckinDate));

        WeeklyProfileResponse resp = new WeeklyProfileResponse();
        resp.setWeekStart(weekStart.toString());
        resp.setWeekEnd(weekEnd.toString());
        resp.setTotalCheckins(items.size());
        resp.setDaysCheckedIn((int) items.stream().map(Checkin::getCheckinDate).distinct().count());
        resp.setStreakDays(checkinService.streakDays(userId));

        if (items.isEmpty()) {
            // 无数据兜底：全 0 + 空分布，前端展示“本周还没有记录”
            resp.setAvgIntensity(0.0);
            EMOTION_ORDER.forEach(e -> resp.getEmotionCounts().put(e, 0));
            return resp;
        }

        double avg = items.stream()
            .filter(c -> c.getIntensity() != null)
            .mapToInt(Checkin::getIntensity)
            .average()
            .orElse(0.0);
        resp.setAvgIntensity(Math.round(avg * 10.0) / 10.0);

        Map<String, Integer> counts = new LinkedHashMap<>();
        EMOTION_ORDER.forEach(e -> counts.put(e, 0));
        items.forEach(c -> counts.merge(c.getEmotion(), 1, Integer::sum));
        resp.setEmotionCounts(counts);

        resp.setTrend(items.stream().map(c -> {
            WeeklyProfileResponse.DayPoint p = new WeeklyProfileResponse.DayPoint();
            p.setDate(c.getCheckinDate());
            p.setEmotion(c.getEmotion());
            p.setIntensity(c.getIntensity());
            return p;
        }).toList());
        return resp;
    }
}
