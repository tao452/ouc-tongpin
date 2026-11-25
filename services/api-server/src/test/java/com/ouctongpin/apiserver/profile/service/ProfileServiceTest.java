package com.ouctongpin.apiserver.profile.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.ouctongpin.apiserver.checkin.entity.Checkin;
import com.ouctongpin.apiserver.checkin.mapper.CheckinMapper;
import com.ouctongpin.apiserver.profile.dto.WeeklyProfileResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.Duration;
import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ProfileServiceTest {
    @Mock private CheckinMapper checkinMapper;
    @Mock private StringRedisTemplate redisTemplate;
    @Mock private ValueOperations<String, String> valueOperations;

    @InjectMocks private ProfileService service;

    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper().registerModule(new JavaTimeModule());
        ReflectionTestUtils.setField(service, "objectMapper", objectMapper);
    }

    @Test
    void noDataReturnsZeroFallbackAndIsNotCached() {
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(checkinMapper.selectList(any())).thenReturn(List.of());

        WeeklyProfileResponse resp = service.weekly(1L, LocalDate.of(2026, 11, 22));

        assertEquals("2026-11-16", resp.getWeekStart());
        assertEquals("2026-11-22", resp.getWeekEnd());
        assertEquals(0, resp.getTotalCheckins());
        assertEquals(0.0, resp.getAvgIntensity());
        assertEquals(6, resp.getEmotionCounts().size());
        verify(valueOperations, never()).set(anyString(), anyString(), any(Duration.class));
    }

    @Test
    void sundayDateAggregatesIntoMondayBasedWeekAndCachesTenMinutes() {
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        Checkin mon = checkin(LocalDate.of(2026, 11, 16), "HAPPY", 3);
        Checkin sun = checkin(LocalDate.of(2026, 11, 22), "CALM", 5);
        when(checkinMapper.selectList(any())).thenReturn(List.of(mon, sun));

        WeeklyProfileResponse resp = service.weekly(1L, LocalDate.of(2026, 11, 22));

        assertEquals(2, resp.getTotalCheckins());
        assertEquals(2, resp.getDaysCheckedIn());
        assertEquals(4.0, resp.getAvgIntensity());
        assertEquals(1, resp.getEmotionCounts().get("HAPPY"));
        assertEquals(1, resp.getEmotionCounts().get("CALM"));

        ArgumentCaptor<String> key = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<Duration> ttl = ArgumentCaptor.forClass(Duration.class);
        verify(valueOperations).set(key.capture(), anyString(), ttl.capture());
        assertEquals("profile:weekly:1:2026-11-16", key.getValue());
        assertEquals(Duration.ofMinutes(10), ttl.getValue());
    }

    @Test
    void cacheHitSkipsDatabase() throws Exception {
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        WeeklyProfileResponse cached = new WeeklyProfileResponse();
        cached.setWeekStart("2026-11-16");
        cached.setTotalCheckins(9);
        when(valueOperations.get("profile:weekly:1:2026-11-16"))
            .thenReturn(objectMapper.writeValueAsString(cached));

        WeeklyProfileResponse resp = service.weekly(1L, LocalDate.of(2026, 11, 18));

        assertEquals(9, resp.getTotalCheckins());
        verifyNoInteractions(checkinMapper);
    }

    @Test
    void evictUsesMondayKeyForAnyDateInWeek() {
        service.evictWeeklyCache(1L, LocalDate.of(2026, 11, 22));
        verify(redisTemplate).delete("profile:weekly:1:2026-11-16");
    }

    private Checkin checkin(LocalDate date, String emotion, int intensity) {
        Checkin c = new Checkin();
        c.setCheckinDate(date);
        c.setEmotion(emotion);
        c.setIntensity(intensity);
        return c;
    }
}
