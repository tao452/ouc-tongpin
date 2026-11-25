package com.ouctongpin.apiserver.team.controller;

import com.ouctongpin.apiserver.auth.config.CallerIdentity;
import com.ouctongpin.apiserver.common.Result;
import com.ouctongpin.apiserver.team.dto.JoinByCodeReq;
import com.ouctongpin.apiserver.team.dto.TeamCreateReq;
import com.ouctongpin.apiserver.team.dto.TeamResponse;
import com.ouctongpin.apiserver.team.service.TeamService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.security.Principal;
import java.util.Map;

/** US-17 组队空间。异常统一交给 GlobalExceptionHandler 兜底。 */
@RestController
@RequestMapping("/api/teams")
public class TeamController {

    @Autowired private TeamService teamService;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public TeamResponse create(@Valid @RequestBody TeamCreateReq req, Principal principal) {
        return teamService.createTeam(CallerIdentity.require(principal), req);
    }

    @PostMapping("/join")
    public TeamResponse join(@Valid @RequestBody JoinByCodeReq req, Principal principal) {
        return teamService.joinByCode(CallerIdentity.require(principal), req);
    }

    @GetMapping("/mine")
    public Result<TeamResponse> mine(Principal principal) {
        return Result.ok(teamService.myTeam(CallerIdentity.require(principal)));
    }

    @PutMapping("/mine/notice")
    public Result<TeamResponse> updateNotice(@RequestBody Map<String, String> body, Principal principal) {
        String notice = body.getOrDefault("notice", "");
        return Result.ok(teamService.updateNotice(CallerIdentity.require(principal), notice));
    }

    @DeleteMapping("/mine/invite")
    public Result<TeamResponse> revokeInvite(Principal principal) {
        return Result.ok(teamService.revokeInvite(CallerIdentity.require(principal)));
    }

    @DeleteMapping("/mine/members/me")
    public Result<Void> quit(Principal principal) {
        teamService.quit(CallerIdentity.require(principal));
        return Result.ok(null);
    }
}
