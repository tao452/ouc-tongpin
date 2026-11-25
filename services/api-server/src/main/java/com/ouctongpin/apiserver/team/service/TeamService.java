package com.ouctongpin.apiserver.team.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.ouctongpin.apiserver.auth.mapper.UserMapper;
import com.ouctongpin.apiserver.team.dto.JoinByCodeReq;
import com.ouctongpin.apiserver.team.dto.TeamCreateReq;
import com.ouctongpin.apiserver.team.dto.TeamResponse;
import com.ouctongpin.apiserver.team.entity.Team;
import com.ouctongpin.apiserver.team.entity.TeamMember;
import com.ouctongpin.apiserver.team.mapper.TeamMapper;
import com.ouctongpin.apiserver.team.mapper.TeamMemberMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.security.SecureRandom;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/** US-17 组队空间：创建、邀请码加入（7 天有效 + 撤销）、公告、成员、退出。 */
@Service
public class TeamService {

    /** 组队人数上限，改这里即可调整。 */
    static final int MAX_MEMBERS = 6;
    static final int INVITE_VALID_DAYS = 7;
    private static final String CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // 去掉易混淆的 0/O/1/I
    private static final SecureRandom RANDOM = new SecureRandom();

    @Autowired private TeamMapper teamMapper;
    @Autowired private TeamMemberMapper memberMapper;
    @Autowired private UserMapper userMapper;

    @Transactional
    public TeamResponse createTeam(Long userId, TeamCreateReq req) {
        if (findMyMembership(userId) != null) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "你已在一个组队中，请先退出");
        }

        Team team = new Team();
        team.setName(req.getName());
        team.setNotice(req.getNotice());
        team.setOwnerUserId(userId);
        team.setInviteCode(generateCode());
        LocalDateTime now = LocalDateTime.now(ZoneOffset.ofHours(8));
        team.setInviteExpiresAt(now.plusDays(INVITE_VALID_DAYS));
        team.setCreatedAt(now);
        team.setUpdatedAt(now);
        team.setDeleted(0);
        teamMapper.insert(team);

        TeamMember owner = new TeamMember();
        owner.setTeamId(team.getId());
        owner.setUserId(userId);
        owner.setRole("OWNER");
        owner.setJoinedAt(now);
        owner.setDeleted(0);
        memberMapper.insert(owner);

        return toResponse(team, userId);
    }

    /** 邀请码加入。过期 / 撤销 / 已满 / 重复加入都给出明确错误。 */
    @Transactional
    public TeamResponse joinByCode(Long userId, JoinByCodeReq req) {
        if (findMyMembership(userId) != null) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "你已在一个组队中，请先退出");
        }

        Team team = teamMapper.selectOne(new LambdaQueryWrapper<Team>()
            .eq(Team::getInviteCode, req.getInviteCode().trim())
            .eq(Team::getDeleted, 0));
        if (team == null || team.getInviteExpiresAt() == null
            || team.getInviteExpiresAt().isBefore(LocalDateTime.now(ZoneOffset.ofHours(8)))) {
            // 撤销后 invite_code 为 NULL，与“码不存在”一样按无效处理，避免暴露撤销状态。
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "邀请码无效或已过期");
        }

        Long memberCount = memberMapper.selectCount(new LambdaQueryWrapper<TeamMember>()
            .eq(TeamMember::getTeamId, team.getId())
            .eq(TeamMember::getDeleted, 0));
        if (memberCount >= MAX_MEMBERS) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "组队人数已满");
        }

        TeamMember member = new TeamMember();
        member.setTeamId(team.getId());
        member.setUserId(userId);
        member.setRole("MEMBER");
        member.setJoinedAt(LocalDateTime.now(ZoneOffset.ofHours(8)));
        member.setDeleted(0);
        memberMapper.insert(member);

        return toResponse(team, userId);
    }

    /** 未加入任何组队时返回 inTeam=false 的空对象（前端兜底，不报错）。 */
    public TeamResponse myTeam(Long userId) {
        TeamMember mine = findMyMembership(userId);
        if (mine == null) {
            TeamResponse empty = new TeamResponse();
            empty.setInTeam(false);
            return empty;
        }
        Team team = teamMapper.selectById(mine.getTeamId());
        return toResponse(team, userId);
    }

    /** 更新公告，仅组长。 */
    @Transactional
    public TeamResponse updateNotice(Long userId, String notice) {
        TeamMember mine = requireMembership(userId);
        if (!"OWNER".equals(mine.getRole())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "只有组长可以修改公告");
        }
        Team team = teamMapper.selectById(mine.getTeamId());
        team.setNotice(notice);
        team.setUpdatedAt(LocalDateTime.now(ZoneOffset.ofHours(8)));
        teamMapper.updateById(team);
        return toResponse(team, userId);
    }

    /** 撤销邀请码：invite_code 置 NULL，旧码立刻全部失效；仅组长。 */
    @Transactional
    public TeamResponse revokeInvite(Long userId) {
        TeamMember mine = requireMembership(userId);
        if (!"OWNER".equals(mine.getRole())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "只有组长可以撤销邀请码");
        }
        Team team = teamMapper.selectById(mine.getTeamId());
        team.setInviteCode(null);
        team.setInviteExpiresAt(null);
        team.setUpdatedAt(LocalDateTime.now(ZoneOffset.ofHours(8)));
        teamMapper.updateById(team);
        return toResponse(team, userId);
    }

    /**
     * 退出组队。组长退出时：还有其他成员则转让给最早加入的人，只剩自己则解散。
     */
    @Transactional
    public void quit(Long userId) {
        TeamMember mine = requireMembership(userId);
        Team team = teamMapper.selectById(mine.getTeamId());

        List<TeamMember> others = memberMapper.selectList(new LambdaQueryWrapper<TeamMember>()
            .eq(TeamMember::getTeamId, team.getId())
            .eq(TeamMember::getDeleted, 0)
            .ne(TeamMember::getUserId, userId));
        if ("OWNER".equals(mine.getRole())) {
            if (others.isEmpty()) {
                // 最后一人退出 => 解散，软删除
                team.setDeleted(1);
                team.setUpdatedAt(LocalDateTime.now(ZoneOffset.ofHours(8)));
                teamMapper.updateById(team);
            } else {
                TeamMember nextOwner = others.stream()
                    .min(Comparator.comparing(TeamMember::getJoinedAt)
                        .thenComparing(TeamMember::getId))
                    .orElseThrow();
                nextOwner.setRole("OWNER");
                memberMapper.updateById(nextOwner);
                team.setOwnerUserId(nextOwner.getUserId());
                team.setUpdatedAt(LocalDateTime.now(ZoneOffset.ofHours(8)));
                teamMapper.updateById(team);
            }
        }
        mine.setDeleted(1);
        memberMapper.updateById(mine);
    }

    // ---------- 内部方法 ----------

    private TeamMember findMyMembership(Long userId) {
        return memberMapper.selectOne(new LambdaQueryWrapper<TeamMember>()
            .eq(TeamMember::getUserId, userId)
            .eq(TeamMember::getDeleted, 0)
            .last("LIMIT 1"));
    }

    private TeamMember requireMembership(Long userId) {
        TeamMember mine = findMyMembership(userId);
        if (mine == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "你还没有加入任何组队");
        }
        return mine;
    }

    private String generateCode() {
        StringBuilder sb = new StringBuilder(8);
        for (int i = 0; i < 8; i++) {
            sb.append(CODE_CHARS.charAt(RANDOM.nextInt(CODE_CHARS.length())));
        }
        return sb.toString();
    }

    private TeamResponse toResponse(Team team, Long viewerId) {
        TeamResponse resp = new TeamResponse();
        resp.setInTeam(true);
        resp.setId(String.valueOf(team.getId()));
        resp.setName(team.getName());
        resp.setNotice(team.getNotice());
        resp.setInviteCode(team.getInviteCode());
        resp.setInviteExpiresAt(team.getInviteExpiresAt());

        List<TeamMember> members = memberMapper.selectList(new LambdaQueryWrapper<TeamMember>()
            .eq(TeamMember::getTeamId, team.getId())
            .eq(TeamMember::getDeleted, 0)
            .orderByAsc(TeamMember::getJoinedAt));
        resp.setIsOwner(members.stream()
            .anyMatch(m -> m.getUserId().equals(viewerId) && "OWNER".equals(m.getRole())));

        // 成员昵称批量查一次，避免 N+1
        Set<Long> userIds = members.stream().map(TeamMember::getUserId).collect(Collectors.toSet());
        Map<Long, String> nicknames = new java.util.HashMap<>();
        if (!userIds.isEmpty()) {
            userMapper.selectBatchIds(userIds).forEach(u ->
                nicknames.put(u.getId(), u.getNickname() == null ? "用户" + u.getId() : u.getNickname()));
        }

        resp.setMembers(members.stream().map(m -> {
            TeamResponse.Member item = new TeamResponse.Member();
            item.setUserId(String.valueOf(m.getUserId()));
            item.setNickname(nicknames.getOrDefault(m.getUserId(), "用户" + m.getUserId()));
            item.setRole(m.getRole());
            item.setJoinedAt(m.getJoinedAt());
            return item;
        }).collect(Collectors.toList()));
        return resp;
    }
}
