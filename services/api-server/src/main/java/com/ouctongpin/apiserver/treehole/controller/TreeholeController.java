package com.ouctongpin.apiserver.treehole.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ouctongpin.apiserver.common.Result;
import com.ouctongpin.apiserver.treehole.dto.PostCreateReq;
import com.ouctongpin.apiserver.treehole.dto.PostResponse;
import com.ouctongpin.apiserver.treehole.service.TreeholeService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/treehole")
public class TreeholeController {
    @Autowired private TreeholeService treeholeService;

    @PostMapping("/create")
    public Result<Long> create(@Valid @RequestBody PostCreateReq req) {
        // 为了测试方便，先写死 userId = 1
        return Result.ok(treeholeService.createPost(1L, req));
    }

    @GetMapping("/list")
    public Result<Page<PostResponse>> list(
        @RequestParam(defaultValue = "1") int pageNum,
        @RequestParam(defaultValue = "10") int pageSize) {
        return Result.ok(treeholeService.listPosts(pageNum, pageSize));
    }
}
