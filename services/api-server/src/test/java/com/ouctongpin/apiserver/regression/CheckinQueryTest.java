package com.ouctongpin.apiserver.regression;

import com.ouctongpin.apiserver.checkin.entity.Checkin;
import com.ouctongpin.apiserver.checkin.mapper.CheckinMapper;
import com.ouctongpin.apiserver.checkin.service.CheckinService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class CheckinQueryTest {
    private final CheckinMapper mapper = mock(CheckinMapper.class);
    private final CheckinService service = new CheckinService();

    CheckinQueryTest() {
        ReflectionTestUtils.setField(service, "checkinMapper", mapper);
    }

    @ParameterizedTest
    @ValueSource(strings = {"invalid", "", "2031-02-30"})
    void invalidDateNeverReachesDatabase(String from) {
        assertEquals(400, assertThrows(ResponseStatusException.class,
                () -> service.list(1L, from, null)).getStatusCode().value());
        verifyNoInteractions(mapper);
    }

    @Test void reversedRangeNeverReachesDatabase() {
        assertEquals(400, assertThrows(ResponseStatusException.class,
                () -> service.list(1L, "2031-02-01", "2031-01-01")).getStatusCode().value());
        verifyNoInteractions(mapper);
    }

    @Test void concurrentDuplicateReturnsAlreadyPersistedRecord() {
        Checkin existing = new Checkin();
        existing.setId(7L);
        when(mapper.selectOne(any())).thenReturn(null, existing);
        when(mapper.insert(any(Checkin.class))).thenThrow(new DuplicateKeyException("synthetic"));
        when(mapper.selectCount(any())).thenReturn(0L);
        assertSame(existing, service.doCheckin(1L, "CALM", 3, null, LocalDate.of(2031, 1, 1)));
    }

    @Test void failedInsertCannotReturnAnUnsavedSuccess() {
        when(mapper.insert(any(Checkin.class))).thenThrow(new DuplicateKeyException("synthetic"));
        assertThrows(DuplicateKeyException.class,
                () -> service.doCheckin(1L, "CALM", 3, null, LocalDate.of(2031, 1, 1)));
    }
}
