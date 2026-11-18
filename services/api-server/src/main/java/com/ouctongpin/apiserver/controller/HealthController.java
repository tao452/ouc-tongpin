package com.ouctongpin.apiserver.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.Map;

/** Process readiness; Compose separately waits for authenticated database/cache checks. */
@RestController
public class HealthController {
    @GetMapping("/internal/health")
    public Map<String, String> health() {
        return Map.of("status", "ok");
    }
}
