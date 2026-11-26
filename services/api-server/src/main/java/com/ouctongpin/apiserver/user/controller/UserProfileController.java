package com.ouctongpin.apiserver.user.controller;

import com.ouctongpin.apiserver.auth.config.CallerIdentity;
import com.ouctongpin.apiserver.user.dto.ProfileResponse;
import com.ouctongpin.apiserver.user.dto.ProfileUpdateReq;
import com.ouctongpin.apiserver.user.service.UserProfileService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.security.Principal;

/** Contract: PUT /api/user/profile -> 200 with the normalised profile. */
@RestController
@RequestMapping("/api/user")
public class UserProfileController {

    @Autowired private UserProfileService userProfileService;

    @PutMapping("/profile")
    public ProfileResponse update(@Valid @RequestBody ProfileUpdateReq req, Principal principal) {
        // Never trust a userId from the body/query; it is derived from the verified JWT.
        return userProfileService.update(CallerIdentity.require(principal), req);
    }
}
