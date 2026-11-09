package com.ouctongpin.apiserver.treehole.controller;

import com.ouctongpin.apiserver.treehole.dto.PostCreateReq;
import com.ouctongpin.apiserver.treehole.dto.PostResponse;
import com.ouctongpin.apiserver.treehole.entity.TreeholePost;
import com.ouctongpin.apiserver.treehole.service.TreeholeService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/api/treehole")
public class TreeholeController {
    @Autowired private TreeholeService treeholeService;

    // 契约：POST /api/treehole/posts -> TreeholePost
    // TODO(W3): userId 临时写死 1L，待接入 JWT 拦截器后从 Authorization 解析
    @PostMapping("/posts")
    @ResponseStatus(HttpStatus.CREATED)
    public PostResponse create(@Valid @RequestBody PostCreateReq req) {
        return treeholeService.toResponse(treeholeService.createPost(1L, req));
    }

    // 契约：GET /api/treehole/posts?emotionTag&cursor -> { items, nextCursor }
    @GetMapping("/posts")
    public Map<String, Object> list(@RequestParam(required = false) String emotionTag,
                                    @RequestParam(required = false) String cursor) {
        return treeholeService.listPosts(emotionTag, cursor);
    }
}
