package com.ouctongpin.apiserver.buddy.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ouctongpin.apiserver.buddy.dto.BuddyCreateReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyQueryReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyResponse;
import com.ouctongpin.apiserver.buddy.service.BuddyService;
import com.ouctongpin.apiserver.common.Result;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/match/needs")
public class BuddyController {

    @Autowired private BuddyService buddyService;

    @PostMapping
    public Result<BuddyResponse> create(@Valid @RequestBody BuddyCreateReq req) {
        Long newId = buddyService.createBuddy(1L, req);

        BuddyResponse res = new BuddyResponse();
        res.setId(String.valueOf(newId));
        res.setScene(req.getScene());
        res.setStatus("0");

        return Result.ok(res);
    }

    @GetMapping("/list")
    public Result<Page<BuddyResponse>> list(
        @RequestParam(defaultValue = "1") int pageNum,
        @RequestParam(defaultValue = "10") int pageSize,
        @RequestParam(required = false) String scene) {
        return Result.ok(buddyService.listBuddies(pageNum, pageSize, scene));
    }

    @PostMapping("/square")
    public Result<List<BuddyResponse>> getSquareList(@RequestBody BuddyQueryReq req) {
        try {
            return Result.ok(buddyService.getSquareList(req));
        } catch (Exception e) {
            return Result.fail(500, "获取广场列表失败: " + e.getMessage());
        }
    }
}
