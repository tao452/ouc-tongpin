package com.ouctongpin.apiserver.user.service;

import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class UserProfileServiceTest {

    @Test
    void normaliseTagsTrimsDropsBlanksAndDeduplicates() {
        List<String> result = UserProfileService.normaliseTags(
                Arrays.asList("  高数  ", "高数", "", "   ", "线代"));
        assertEquals(Arrays.asList("高数", "线代"), result);
    }

    @Test
    void normaliseTagsCapsAtEight() {
        List<String> raw = Arrays.asList("t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10");
        List<String> result = UserProfileService.normaliseTags(raw);
        assertEquals(8, result.size());
        assertTrue(result.contains("t8"));
        assertTrue(!result.contains("t9"));
    }

    @Test
    void normaliseTagsHandlesNullAndEmpty() {
        assertTrue(UserProfileService.normaliseTags(null).isEmpty());
        assertTrue(UserProfileService.normaliseTags(List.of()).isEmpty());
    }
}
