package com.ouctongpin.apiserver.buddy.controller;

import com.ouctongpin.apiserver.buddy.dto.BuddyCreateReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyQueryReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyResponse;
import com.ouctongpin.apiserver.buddy.service.BuddyService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/match/needs")
public class BuddyController {

    @Autowired private BuddyService buddyService;

    // 1. 发布搭子 (恢复 201 状态码)
    @PostMapping
    public ResponseEntity<BuddyResponse> create(
        @Valid @RequestBody BuddyCreateReq req,

        @RequestAttribute(value = "userId", required = false) Long userId) {

        // 如果团队有 CallerIdentity.require(principal)，请加在这里
        Long currentUserId = (userId != null) ? userId : 1L; // 临时兜底

        Long newId = buddyService.createBuddy(currentUserId, req);

        BuddyResponse res = new BuddyResponse();
        res.setId(String.valueOf(newId));
        res.setScene(req.getScene());
        res.setStatus("OPEN");

        // 【契约要求】必须返回 201 CREATED
        return ResponseEntity.status(HttpStatus.CREATED).body(res);
    }

    // 2. 广场查询接口 (你写的 W5)
    @PostMapping("/square")
    public ResponseEntity<List<BuddyResponse>> getSquareList(@RequestBody BuddyQueryReq req) {
        try {
            return ResponseEntity.ok(buddyService.getSquareList(req));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }
}
