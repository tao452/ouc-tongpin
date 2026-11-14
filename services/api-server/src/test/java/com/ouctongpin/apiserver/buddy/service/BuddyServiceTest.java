package com.ouctongpin.apiserver.buddy.service;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BuddyServiceTest {

    @Test
    void parsesUtcIsoFromMiniprogramIntoBeijingTime() {
        // new Date("2026-11-15T10:00:00+08:00").toISOString() === 02:00:00.000Z
        assertEquals(
            LocalDateTime.of(2026, 11, 15, 10, 0, 0),
            BuddyService.parseEventTime("2026-11-15T02:00:00.000Z"));
    }

    @Test
    void keepsExplicitOffset() {
        assertEquals(
            LocalDateTime.of(2026, 11, 15, 10, 0, 0),
            BuddyService.parseEventTime("2026-11-15T10:00:00+08:00"));
    }

    @Test
    void acceptsLocalIsoDateTimeWithoutOffset() {
        assertEquals(
            LocalDateTime.of(2026, 11, 15, 10, 0, 0),
            BuddyService.parseEventTime("2026-11-15T10:00:00"));
    }

    @Test
    void rejectsMalformedTimeWithBadRequest() {
        ResponseStatusException error = assertThrows(
            ResponseStatusException.class,
            () -> BuddyService.parseEventTime("not-a-time"));
        assertEquals(HttpStatus.BAD_REQUEST.value(), error.getStatusCode().value());
        assertTrue(error.getReason().contains("ISO-8601"));
    }
}
