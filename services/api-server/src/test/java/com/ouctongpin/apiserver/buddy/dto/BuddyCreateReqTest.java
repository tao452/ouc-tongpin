package com.ouctongpin.apiserver.buddy.dto;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BuddyCreateReqTest {

    private static Validator validator;

    @BeforeAll
    static void setUpValidator() {
        validator = Validation.buildDefaultValidatorFactory().getValidator();
    }

    private static BuddyCreateReq valid() {
        BuddyCreateReq req = new BuddyCreateReq();
        req.setScene("自习");
        req.setTime("2026-11-15T02:00:00.000Z");
        BuddyCreateReq.Location location = new BuddyCreateReq.Location();
        location.setAddress("图书馆");
        req.setLocation(location);
        req.setSkillTags(List.of("高数"));
        req.setRemark("一起复习");
        return req;
    }

    private static Set<String> messages(BuddyCreateReq req) {
        return validator.validate(req).stream()
            .map(ConstraintViolation::getMessage)
            .collect(java.util.stream.Collectors.toSet());
    }

    @Test
    void validContractPayloadHasNoViolations() {
        assertEquals(Set.of(), messages(valid()));
    }

    @Test
    void rejectsSixSkillTags() {
        BuddyCreateReq req = valid();
        req.setSkillTags(List.of("1", "2", "3", "4", "5", "6"));
        assertTrue(messages(req).contains("技能标签最多 5 个"));
    }

    @Test
    void rejectsRemarkOverTwoHundredCharacters() {
        BuddyCreateReq req = valid();
        req.setRemark("一".repeat(201));
        assertTrue(messages(req).contains("补充说明不能超过 200 字符"));
    }

    @Test
    void acceptsRemarkAtBoundary() {
        BuddyCreateReq req = valid();
        req.setRemark("一".repeat(200));
        assertEquals(Set.of(), messages(req));
    }

    @Test
    void requiresSceneTimeAndLocation() {
        BuddyCreateReq req = valid();
        req.setScene("");
        req.setTime(null);
        req.setLocation(null);
        Set<String> errors = messages(req);
        assertTrue(errors.contains("场景不能为空"));
        assertTrue(errors.contains("时间不能为空"));
        assertTrue(errors.contains("地点不能为空"));
    }

    @Test
    void validatesNestedLocationAddress() {
        BuddyCreateReq req = valid();
        req.getLocation().setAddress("");
        assertTrue(messages(req).contains("地点地址不能为空"));
    }
}
