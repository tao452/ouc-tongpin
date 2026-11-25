package com.ouctongpin.apiserver.team.service;

import com.ouctongpin.apiserver.auth.mapper.UserMapper;
import com.ouctongpin.apiserver.team.dto.JoinByCodeReq;
import com.ouctongpin.apiserver.team.dto.TeamCreateReq;
import com.ouctongpin.apiserver.team.dto.TeamResponse;
import com.ouctongpin.apiserver.team.entity.Team;
import com.ouctongpin.apiserver.team.entity.TeamMember;
import com.ouctongpin.apiserver.team.mapper.TeamMapper;
import com.ouctongpin.apiserver.team.mapper.TeamMemberMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class TeamServiceTest {
    @Mock private TeamMapper teamMapper;
    @Mock private TeamMemberMapper memberMapper;
    @Mock private UserMapper userMapper;
    @InjectMocks private TeamService service;

    private static final ZoneOffset BEIJING = ZoneOffset.ofHours(8);

    @Test
    void createTeamMakesCreatorOwnerWithSevenDayInvite() {
        when(memberMapper.selectOne(any())).thenReturn(null);
        when(memberMapper.selectList(any())).thenReturn(
            List.of(member(1L, 1L, 1L, "OWNER", LocalDateTime.now(BEIJING))));
        doAnswer(inv -> {
            Team t = inv.getArgument(0);
            t.setId(1L);
            return 1;
        }).when(teamMapper).insert(any(Team.class));

        TeamCreateReq req = new TeamCreateReq();
        req.setName("晨跑搭子");
        req.setNotice("周六早七点");

        TeamResponse resp = service.createTeam(1L, req);

        assertEquals(Boolean.TRUE, resp.getInTeam());
        assertEquals(Boolean.TRUE, resp.getIsOwner());
        assertEquals("1", resp.getId());
        assertNotNull(resp.getInviteCode());
        assertEquals(8, resp.getInviteCode().length());
        assertTrue(resp.getInviteExpiresAt().isAfter(LocalDateTime.now(BEIJING).plusDays(6)));

        ArgumentCaptor<TeamMember> owner = ArgumentCaptor.forClass(TeamMember.class);
        verify(memberMapper).insert(owner.capture());
        assertEquals("OWNER", owner.getValue().getRole());
        assertEquals(1L, owner.getValue().getUserId());
    }

    @Test
    void joinRejectsExpiredInvite() {
        when(memberMapper.selectOne(any())).thenReturn(null);
        Team team = team(10L);
        team.setInviteCode("ABC23456");
        team.setInviteExpiresAt(LocalDateTime.now(BEIJING).minusDays(1));
        when(teamMapper.selectOne(any())).thenReturn(team);

        ResponseStatusException ex = assertThrows(ResponseStatusException.class,
            () -> service.joinByCode(2L, joinReq("ABC23456")));
        assertEquals(HttpStatus.BAD_REQUEST.value(), ex.getStatusCode().value());
    }

    @Test
    void joinRejectsRevokedInvite() {
        when(memberMapper.selectOne(any())).thenReturn(null);
        when(teamMapper.selectOne(any())).thenReturn(null);

        ResponseStatusException ex = assertThrows(ResponseStatusException.class,
            () -> service.joinByCode(2L, joinReq("ABC23456")));
        assertEquals(HttpStatus.BAD_REQUEST.value(), ex.getStatusCode().value());
    }

    @Test
    void joinRejectsFullTeam() {
        when(memberMapper.selectOne(any())).thenReturn(null);
        Team team = team(10L);
        team.setInviteCode("ABC23456");
        team.setInviteExpiresAt(LocalDateTime.now(BEIJING).plusDays(1));
        when(teamMapper.selectOne(any())).thenReturn(team);
        when(memberMapper.selectCount(any())).thenReturn(6L);

        ResponseStatusException ex = assertThrows(ResponseStatusException.class,
            () -> service.joinByCode(2L, joinReq("ABC23456")));
        assertEquals(HttpStatus.CONFLICT.value(), ex.getStatusCode().value());
    }

    @Test
    void quitTransfersOwnerToEarliestRemainingMember() {
        LocalDateTime base = LocalDateTime.now(BEIJING).minusDays(2);
        TeamMember owner = member(1L, 10L, 1L, "OWNER", base);
        TeamMember later = member(3L, 10L, 3L, "MEMBER", base.plusDays(2));
        TeamMember earliest = member(2L, 10L, 2L, "MEMBER", base.plusDays(1));
        Team team = team(10L);
        team.setOwnerUserId(1L);

        when(memberMapper.selectOne(any())).thenReturn(owner);
        when(teamMapper.selectById(10L)).thenReturn(team);
        when(memberMapper.selectList(any())).thenReturn(List.of(later, earliest));

        service.quit(1L);

        assertEquals("OWNER", earliest.getRole());
        assertEquals(2L, team.getOwnerUserId());
        assertEquals(Integer.valueOf(1), owner.getDeleted());
        verify(memberMapper).updateById(earliest);
        verify(teamMapper).updateById(team);
    }

    @Test
    void myTeamReturnsEmptyWhenUserHasNoTeam() {
        when(memberMapper.selectOne(any())).thenReturn(null);

        TeamResponse resp = service.myTeam(1L);

        assertEquals(Boolean.FALSE, resp.getInTeam());
        verifyNoInteractions(teamMapper);
    }

    private Team team(long id) {
        Team t = new Team();
        t.setId(id);
        t.setName("测试队伍");
        t.setDeleted(0);
        return t;
    }

    private TeamMember member(long id, long teamId, long userId, String role, LocalDateTime joinedAt) {
        TeamMember m = new TeamMember();
        m.setId(id);
        m.setTeamId(teamId);
        m.setUserId(userId);
        m.setRole(role);
        m.setJoinedAt(joinedAt);
        m.setDeleted(0);
        return m;
    }

    private JoinByCodeReq joinReq(String code) {
        JoinByCodeReq req = new JoinByCodeReq();
        req.setInviteCode(code);
        return req;
    }
}
