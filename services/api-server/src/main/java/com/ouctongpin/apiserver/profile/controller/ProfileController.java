package com.ouctongpin.apiserver.profile.controller;

import com.ouctongpin.apiserver.auth.config.CallerIdentity;
import com.ouctongpin.apiserver.common.Result;
import com.ouctongpin.apiserver.profile.dto.WeeklyProfileResponse;
import com.ouctongpin.apiserver.profile.service.ProfileService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.security.Principal;
import java.time.LocalDate;

/** US-04 画像聚合接口。date 可选（YYYY-MM-DD），用于定位目标周，默认本周。 */
@RestController
@RequestMapping("/api/user/profile")
public class ProfileController {

    @Autowired private ProfileService profileService;

    @GetMapping("/weekly")
    public Result<WeeklyProfileResponse> weekly(
        @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date,
        Principal principal) {
        return Result.ok(profileService.weekly(CallerIdentity.require(principal), date));
    }
}
