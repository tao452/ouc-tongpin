package com.ouctongpin.apiserver.checkin.controller;

import com.ouctongpin.apiserver.checkin.dto.CheckinReq;
import com.ouctongpin.apiserver.checkin.entity.Checkin;
import com.ouctongpin.apiserver.checkin.service.CheckinService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/emotions")
public class CheckinController {
    @Autowired private CheckinService checkinService;

    // 契约：POST /api/emotions/checkins
    // TODO(W3): userId 临时写死 1L，待接入 JWT 拦截器后从 Authorization 解析
    @PostMapping("/checkins")
    public Checkin create(@Valid @RequestBody CheckinReq req) {
        return checkinService.doCheckin(1L, req.getEmotion(), req.getIntensity(), req.getNote(), req.getCheckinDate());
    }

    // 契约：GET /api/emotions/checkins?from&to
    @GetMapping("/checkins")
    public Map<String, Object> list(@RequestParam(required = false) String from,
                                    @RequestParam(required = false) String to) {
        List<Checkin> items = checkinService.list(1L, from, to);
        Map<String, Object> m = new HashMap<>();
        m.put("items", items);
        m.put("streakDays", checkinService.streakDays(1L));
        m.put("total", items.size());
        return m;
    }
}
