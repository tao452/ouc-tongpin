package com.ouctongpin.apiserver.buddy.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ouctongpin.apiserver.buddy.dto.BuddyCreateReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyResponse;
import com.ouctongpin.apiserver.buddy.service.BuddyService;
import com.ouctongpin.apiserver.common.Result;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/buddy")
public class BuddyController {
    @Autowired private BuddyService buddyService;

    @PostMapping("/create")
    public Result<Long> create(@Valid @RequestBody BuddyCreateReq req) {
        // 同样先写死 userId=1 方便测试
        return Result.ok(buddyService.createBuddy(1L, req));
    }

    @GetMapping("/list")
    public Result<Page<BuddyResponse>> list(
        @RequestParam(defaultValue = "1") int pageNum,
        @RequestParam(defaultValue = "10") int pageSize,
        @RequestParam(required = false) String scene) {
        return Result.ok(buddyService.listBuddies(pageNum, pageSize, scene));
    }
}
