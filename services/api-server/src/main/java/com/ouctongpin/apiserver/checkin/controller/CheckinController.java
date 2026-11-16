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
import java.security.Principal;
import com.ouctongpin.apiserver.auth.config.CallerIdentity;

@RestController
@RequestMapping("/api/emotions")
public class CheckinController {
    @Autowired private CheckinService checkinService;

    // 契约：POST /api/emotions/checkins
    @PostMapping("/checkins")
    public Checkin create(@Valid @RequestBody CheckinReq req, Principal principal) {
        return checkinService.doCheckin(CallerIdentity.require(principal), req.getEmotion(),
                req.getIntensity(), req.getNote(), req.getCheckinDate());
    }

    // 契约：GET /api/emotions/checkins?from&to
    @GetMapping("/checkins")
    public Map<String, Object> list(@RequestParam(required = false) String from,
                                    @RequestParam(required = false) String to, Principal principal) {
        long userId = CallerIdentity.require(principal);
        List<Checkin> items = checkinService.list(userId, from, to);
        Map<String, Object> m = new HashMap<>();
        m.put("items", items);
        m.put("streakDays", checkinService.streakDays(userId));
        m.put("total", items.size());
        return m;
    }
}
