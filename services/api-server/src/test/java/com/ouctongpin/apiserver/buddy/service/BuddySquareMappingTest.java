package com.ouctongpin.apiserver.buddy.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.buddy.dto.BuddyCreateReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyQueryReq;
import com.ouctongpin.apiserver.buddy.dto.SquareItemResponse;
import com.ouctongpin.apiserver.buddy.entity.BuddyDemand;
import com.ouctongpin.apiserver.buddy.mapper.BuddyDemandMapper;
import com.ouctongpin.apiserver.moderation.ModerationClient;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/** US-11: square rows must carry renderable card fields and honour the cursor. */
@ExtendWith(MockitoExtension.class)
class BuddySquareMappingTest {
    @Mock private BuddyDemandMapper buddyMapper;
    @Mock private ModerationClient moderationClient;
    @Mock private StringRedisTemplate redisTemplate;
    @Mock private ValueOperations<String, String> valueOps;
    @Spy private ObjectMapper objectMapper = new ObjectMapper();
    @InjectMocks private BuddyService service;

    private BuddyQueryReq req(String longitude, String latitude) {
        BuddyQueryReq req = new BuddyQueryReq();
        req.setCursorId(0L);
        req.setMyLongitude(longitude == null ? null : new BigDecimal(longitude));
        req.setMyLatitude(latitude == null ? null : new BigDecimal(latitude));
        req.setRadius(5000);
        req.setSize(10);
        return req;
    }

    private BuddyDemand demand() {
        BuddyDemand d = new BuddyDemand();
        d.setId(42L);
        d.setScene("考研学习");
        d.setRemark("一起复习高数");
        d.setEventTime(LocalDateTime.of(2026, 11, 28, 10, 0));
        d.setLocationAddress("图书馆");
        d.setLatitude(new BigDecimal("36.160000"));
        d.setLongitude(new BigDecimal("120.400000"));
        d.setSkillTags("[\"高数\",\"互相监督\"]");
        d.setStatus("OPEN");
        d.setCreatedAt(LocalDateTime.now(ZoneOffset.ofHours(8)).minusHours(2));
        return d;
    }

    @Test
    void mapsPersistedColumnsIntoCardFields() {
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(buddyMapper.selectList(any())).thenReturn(List.of(demand()));

        List<SquareItemResponse> result = service.getSquareList(req("120.4", "36.16"));

        assertEquals(1, result.size());
        SquareItemResponse item = result.get(0);
        assertEquals("42", item.getId());
        assertEquals("考研学习", item.getTitle());
        assertEquals("学习交流", item.getCategory());
        assertEquals("图书馆", item.getLocation());
        assertEquals("11-28 10:00", item.getTime());
        assertEquals(List.of("高数", "互相监督"), item.getTags());
        assertEquals(1, item.getPeopleCount());
        assertNotNull(item.getDistance());
        assertTrue(item.getPublishText().contains("小时前"));
    }

    @Test
    void distanceIsNullWhenCallerSendsNoCoordinates() {
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(buddyMapper.selectList(any())).thenReturn(List.of(demand()));

        SquareItemResponse item = service.getSquareList(req(null, null)).get(0);

        assertNull(item.getDistance());
    }

    @Test
    void cursorGreaterThanZeroFiltersByEarlierId() {
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(buddyMapper.selectList(any())).thenReturn(List.of());
        BuddyQueryReq req = req(null, null);
        req.setCursorId(17L);

        service.getSquareList(req);

        @SuppressWarnings("rawtypes")
        ArgumentCaptor<LambdaQueryWrapper> captor = ArgumentCaptor.forClass(LambdaQueryWrapper.class);
        verify(buddyMapper).selectList(captor.capture());
        String sql = captor.getValue().getSqlSegment();
        assertTrue(sql.contains("id < #"), "expected cursor predicate, got: " + sql);
    }

    @Test
    void publishingInvalidatesSquareCache() {
        Set<String> oldKeys = Set.of("square:0:null:null:5000:10");
        when(redisTemplate.keys("square:*")).thenReturn(oldKeys);

        BuddyCreateReq req = new BuddyCreateReq();
        req.setScene("考研学习");
        req.setTime("2026-11-29T10:00:00+08:00");
        BuddyCreateReq.Location location = new BuddyCreateReq.Location();
        location.setAddress("图书馆");
        location.setLat(new BigDecimal("36.16"));
        location.setLng(new BigDecimal("120.40"));
        req.setLocation(location);
        when(buddyMapper.insert(any(BuddyDemand.class))).thenReturn(1);

        service.createNeed(1L, req);

        verify(redisTemplate).delete(oldKeys);
    }
}
