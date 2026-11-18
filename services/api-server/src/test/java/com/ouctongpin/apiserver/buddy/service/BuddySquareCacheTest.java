package com.ouctongpin.apiserver.buddy.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.buddy.dto.BuddyQueryReq;
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
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/** US-11 square query: cache must be scoped by every query-affecting parameter. */
@ExtendWith(MockitoExtension.class)
class BuddySquareCacheTest {
    @Mock private BuddyDemandMapper buddyMapper;
    @Mock private ModerationClient moderationClient;
    @Mock private StringRedisTemplate redisTemplate;
    @Mock private ValueOperations<String, String> valueOps;
    @Spy private ObjectMapper objectMapper = new ObjectMapper();
    @InjectMocks private BuddyService service;

    private BuddyQueryReq query(int radius, int size) {
        BuddyQueryReq req = new BuddyQueryReq();
        req.setCursorId(0L);
        req.setMyLongitude(new BigDecimal("120.4"));
        req.setMyLatitude(new BigDecimal("36.16"));
        req.setRadius(radius);
        req.setSize(size);
        return req;
    }

    /** Run two queries and return the two cache keys they used. */
    private List<String> cacheKeysFor(BuddyQueryReq first, BuddyQueryReq second) {
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(buddyMapper.selectList(any())).thenReturn(List.<BuddyDemand>of());
        service.getSquareList(first);
        service.getSquareList(second);
        ArgumentCaptor<String> keys = ArgumentCaptor.forClass(String.class);
        verify(valueOps, times(2)).set(keys.capture(), anyString(), anyLong(), any());
        return keys.getAllValues();
    }

    @Test
    void differentRadiusUsesDifferentCacheKey() {
        List<String> keys = cacheKeysFor(query(5000, 10), query(1000, 10));
        assertEquals(2, keys.size());
        assertNotEquals(keys.get(0), keys.get(1));
    }

    @Test
    void differentSizeUsesDifferentCacheKey() {
        List<String> keys = cacheKeysFor(query(5000, 10), query(5000, 20));
        assertEquals(2, keys.size());
        assertNotEquals(keys.get(0), keys.get(1));
    }

    @Test
    void sameQueryReusesCacheKey() {
        List<String> keys = cacheKeysFor(query(5000, 10), query(5000, 10));
        assertEquals(keys.get(0), keys.get(1));
    }
}
