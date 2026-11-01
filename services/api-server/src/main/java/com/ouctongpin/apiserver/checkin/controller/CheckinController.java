package com.ouctongpin.apiserver.checkin.controller;

import com.ouctongpin.apiserver.checkin.entity.Checkin;
import com.ouctongpin.apiserver.checkin.service.CheckinService;
import com.ouctongpin.apiserver.common.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/checkin")
public class CheckinController {
    @Autowired private CheckinService checkinService;

    // 为了测试方便，先传 userId，等 W3 写了拦截器再从 Token 里取
    @PostMapping("/do")
    public Result<Checkin> doCheckin(@RequestParam Long userId, @RequestParam Long emotionWordId) {
        return Result.ok(checkinService.doCheckin(userId, emotionWordId));
    }
}
