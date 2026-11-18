package com.ouctongpin.apiserver.buddy.controller;

import com.ouctongpin.apiserver.auth.config.CallerIdentity;
import com.ouctongpin.apiserver.buddy.dto.BuddyCreateReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyQueryReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyResponse;
import com.ouctongpin.apiserver.buddy.service.BuddyService;
import com.ouctongpin.apiserver.common.Result;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.security.Principal;
import java.util.List;

/** Contract: POST /api/match/needs -> 201 { id: string, scene, status: "OPEN" }. */
@RestController
@RequestMapping("/api/match")
public class BuddyController {

    @Autowired private BuddyService buddyService;

    // 1. 团队原本的发布接口 (严格 201 契约)
    @PostMapping("/needs")
    @ResponseStatus(HttpStatus.CREATED)
    public BuddyResponse create(@Valid @RequestBody BuddyCreateReq req, Principal principal) {
        return buddyService.createNeed(CallerIdentity.require(principal), req);
    }

    // 2. 广场查询接口 (US-11). 异常交给 GlobalExceptionHandler 统一兜底，
    //    不把内部异常明细回显给客户端。
    @PostMapping("/needs/square")
    public Result<List<BuddyResponse>> getSquareList(@Valid @RequestBody BuddyQueryReq req) {
        return Result.ok(buddyService.getSquareList(req));
    }
}
