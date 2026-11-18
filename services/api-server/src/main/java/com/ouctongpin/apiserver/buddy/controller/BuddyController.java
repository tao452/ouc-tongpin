package com.ouctongpin.apiserver.buddy.controller;

import com.ouctongpin.apiserver.buddy.dto.BuddyCreateReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyResponse;
import com.ouctongpin.apiserver.buddy.service.BuddyService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import java.security.Principal;
import com.ouctongpin.apiserver.auth.config.CallerIdentity;

/** Contract: POST /api/match/needs -> 201 { id: string, scene, status: "OPEN" }. */
@RestController
@RequestMapping("/api/match")
public class BuddyController {

    @Autowired private BuddyService buddyService;

    @PostMapping("/needs")
    @ResponseStatus(HttpStatus.CREATED)
    public BuddyResponse create(@Valid @RequestBody BuddyCreateReq req, Principal principal) {
        return buddyService.createNeed(CallerIdentity.require(principal), req);
    }

    // No GET here: listing/filtering/sorting is V1.0 #12 and has no contract path.
}
