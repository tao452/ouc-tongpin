package com.ouctongpin.apiserver.user.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.ouctongpin.apiserver.user.dto.ProfileResponse;
import com.ouctongpin.apiserver.user.dto.ProfileUpdateReq;
import com.ouctongpin.apiserver.user.entity.UserProfile;
import com.ouctongpin.apiserver.user.entity.UserTag;
import com.ouctongpin.apiserver.user.mapper.UserProfileMapper;
import com.ouctongpin.apiserver.user.mapper.UserTagMapper;
import com.ouctongpin.apiserver.moderation.ModerationClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;

/** US-35 PUT /api/user/profile. Ownership is caller identity from the verified JWT only. */
@Service
public class UserProfileService {

    static final String INTEREST = "INTEREST";
    static final String SKILL = "SKILL";

    @Autowired private UserProfileMapper profiles;
    @Autowired private UserTagMapper tags;
    @Autowired private ModerationClient moderationClient;

    /** One transaction: profile columns and tag rows must succeed or roll back together. */
    @Transactional
    public ProfileResponse update(Long userId, ProfileUpdateReq req) {
        String nickname = trim(req.getNickname());
        String bio = trimToNull(req.getBio());
        List<String> interests = normaliseTags(req.getInterestTags());
        List<String> skills = normaliseTags(req.getSkillTags());

        // Check before any write; a blocked hit (422) or unavailable service (503)
        // aborts the whole transaction, so no profile/tag row is persisted.
        requireAllowed(nickname);
        requireAllowed(bio);
        for (String tag : interests) requireAllowed(tag);
        for (String tag : skills) requireAllowed(tag);

        UserProfile profile = new UserProfile();
        profile.setId(userId);
        profile.setNickname(nickname);
        profile.setAvatar(trimToNull(req.getAvatarUrl()));
        profile.setBio(bio);
        profile.setUpdatedAt(LocalDateTime.now(ZoneOffset.ofHours(8)));
        profiles.updateById(profile);

        tags.delete(new LambdaQueryWrapper<UserTag>().eq(UserTag::getUserId, userId));
        insertTags(userId, INTEREST, interests);
        insertTags(userId, SKILL, skills);

        ProfileResponse response = new ProfileResponse();
        response.setNickname(profile.getNickname());
        response.setAvatarUrl(profile.getAvatar());
        response.setBio(profile.getBio());
        response.setInterestTags(interests);
        response.setSkillTags(skills);
        return response;
    }

    private void requireAllowed(String value) {
        if (value != null && !value.isBlank()) moderationClient.requireAllowed(value);
    }

    private void insertTags(Long userId, String type, List<String> values) {
        for (String value : values) {
            UserTag tag = new UserTag();
            tag.setUserId(userId);
            tag.setTagType(type);
            tag.setTagName(value);
            tag.setCreatedAt(LocalDateTime.now(ZoneOffset.ofHours(8)));
            tags.insert(tag);
        }
    }

    /** Trim, drop blanks, de-duplicate (case-sensitive, matching the miniprogram), cap 8. */
    static List<String> normaliseTags(List<String> raw) {
        if (raw == null || raw.isEmpty()) return new ArrayList<>();
        LinkedHashSet<String> seen = new LinkedHashSet<>();
        for (String item : raw) {
            String value = item == null ? "" : item.trim();
            if (!value.isEmpty()) seen.add(value);
            if (seen.size() >= 8) break;
        }
        return new ArrayList<>(seen);
    }

    private static String trim(String value) {
        return value == null ? "" : value.trim();
    }

    private static String trimToNull(String value) {
        if (value == null) return null;
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
