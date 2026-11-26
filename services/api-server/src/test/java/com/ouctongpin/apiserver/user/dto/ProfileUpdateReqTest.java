package com.ouctongpin.apiserver.user.dto;

import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ProfileUpdateReqTest {
    private final Validator validator;

    ProfileUpdateReqTest() {
        try (ValidatorFactory factory = Validation.buildDefaultValidatorFactory()) {
            validator = factory.getValidator();
        }
    }

    private ProfileUpdateReq valid() {
        ProfileUpdateReq req = new ProfileUpdateReq();
        req.setNickname("小明");
        req.setBio("hi");
        req.setInterestTags(Arrays.asList("高数", "线代"));
        req.setSkillTags(Collections.singletonList("Java"));
        return req;
    }

    @Test
    void validRequestHasNoViolations() {
        assertTrue(validator.validate(valid()).isEmpty());
    }

    @Test
    void blankNicknameIsRejected() {
        ProfileUpdateReq req = valid();
        req.setNickname("   ");
        assertFalse(validator.validate(req).isEmpty());
    }

    @Test
    void nicknameLongerThanTwentyIsRejected() {
        ProfileUpdateReq req = valid();
        req.setNickname("字".repeat(21));
        assertFalse(validator.validate(req).isEmpty());
    }

    @Test
    void bioLongerThanOneHundredIsRejected() {
        ProfileUpdateReq req = valid();
        req.setBio("x".repeat(101));
        assertFalse(validator.validate(req).isEmpty());
    }

    @Test
    void moreThanEightTagsAreRejected() {
        ProfileUpdateReq req = valid();
        req.setInterestTags(Collections.nCopies(9, "t"));
        assertFalse(validator.validate(req).isEmpty());
    }

    @Test
    void tagLongerThanTwelveIsRejected() {
        ProfileUpdateReq req = valid();
        req.setInterestTags(List.of("标签".repeat(7)));
        assertEquals(1, validator.validate(req).stream()
                .filter(v -> v.getPropertyPath().toString().contains("interestTags")).count());
    }

    @Test
    void requestHasNoUserIdField() {
        // Ownership is derived from the verified token; no client-supplied identity field exists.
        boolean hasUserId = Arrays.stream(ProfileUpdateReq.class.getDeclaredFields())
                .anyMatch(f -> f.getName().equalsIgnoreCase("userId"));
        assertFalse(hasUserId);
    }
}
