package com.ouctongpin.apiserver.buddy.controller;

import com.ouctongpin.apiserver.buddy.dto.BuddyCreateReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyResponse;
import com.ouctongpin.apiserver.buddy.service.BuddyService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

/** Contract: POST /api/match/needs -> 201 { id: string, scene, status: "OPEN" }. */
@RestController
@RequestMapping("/api/match")
public class BuddyController {

    @Autowired private BuddyService buddyService;

    // TODO(W4): userId is pinned to 1L for the classroom demo; resolve it from
    // Authorization once the JWT interceptor lands. Do not describe this as real auth.
    @PostMapping("/needs")
    @ResponseStatus(HttpStatus.CREATED)
    public BuddyResponse create(@Valid @RequestBody BuddyCreateReq req) {
        return buddyService.createNeed(1L, req);
    }

    // No GET here: listing/filtering/sorting is V1.0 #12 and has no contract path.
}
