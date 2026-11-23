package com.ouctongpin.apiserver.buddy.dto;

import jakarta.validation.Validation;
import org.junit.jupiter.api.Test;
import java.math.BigDecimal;
import static org.junit.jupiter.api.Assertions.*;

class BuddyQueryReqTest {
    @Test
    void closedCoordinateIntervalsAndOptionalLocation() {
        try (var factory = Validation.buildDefaultValidatorFactory()) {
            var validator = factory.getValidator();
            var req = new BuddyQueryReq();
            assertTrue(validator.validate(req).isEmpty());
            for (String[] point : new String[][]{{"-90", "-180"}, {"90", "180"}}) {
                req.setMyLatitude(new BigDecimal(point[0]));
                req.setMyLongitude(new BigDecimal(point[1]));
                assertTrue(validator.validate(req).isEmpty());
            }
            for (String[] point : new String[][]{
                {"-90.000001", "0"}, {"90.000001", "0"},
                {"0", "-180.000001"}, {"0", "180.000001"}}) {
                req.setMyLatitude(new BigDecimal(point[0]));
                req.setMyLongitude(new BigDecimal(point[1]));
                assertFalse(validator.validate(req).isEmpty());
            }
            req.setRadius(null);
            req.setSize(null);
            assertTrue(validator.validate(req).stream()
                .anyMatch(v -> v.getPropertyPath().toString().equals("radius")));
        }
    }
}
