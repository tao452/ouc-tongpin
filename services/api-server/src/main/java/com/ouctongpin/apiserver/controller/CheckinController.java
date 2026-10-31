package com.ouctongpin.apiserver.controller;

import com.ouctongpin.apiserver.model.Checkin;
import com.ouctongpin.apiserver.model.CheckinRequest;
import com.ouctongpin.apiserver.service.CheckinService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * 情绪打卡接口（US-01/02/03），严格对照 packages/contract/openapi.yaml：
 *   POST /api/emotions/checkins  -> 提交（幂等）
 *   GET  /api/emotions/checkins  -> { items, streakDays, total }
 *
 * 当前 userId 写死为 "demoUser"，待接入 JWT 后从 Authorization 解析。
 */
@RestController
@RequestMapping("/api/emotions")
public class CheckinController {

    private final CheckinService checkinService;

    public CheckinController(CheckinService checkinService) {
        this.checkinService = checkinService;
    }

    @PostMapping("/checkins")
    public Checkin create(@RequestBody @Valid CheckinRequest req) {
        return checkinService.checkin("demoUser", req);
    }

    @GetMapping("/checkins")
    public Map<String, Object> list(@RequestParam(required = false) String from,
                                    @RequestParam(required = false) String to) {
        List<Checkin> items = checkinService.list("demoUser", from, to);
        return Map.of(
                "items", items,
                "streakDays", checkinService.streakDays("demoUser"),
                "total", items.size()
        );
    }
}
