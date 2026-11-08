package com.ouctongpin.apiserver.checkin.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.ouctongpin.apiserver.checkin.entity.Checkin;
import com.ouctongpin.apiserver.checkin.mapper.CheckinMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.List;

@Service
public class CheckinService {
    @Autowired private CheckinMapper checkinMapper;

    // 契约：POST /api/emotions/checkins -> Checkin（幂等：同日重复提交只记一次）
    public Checkin doCheckin(Long userId, String emotion, Integer intensity, String note, LocalDate date) {
        LocalDate d = (date != null) ? date : LocalDate.now();
        // 1. 先查是否已打卡
        Checkin exist = checkinMapper.selectOne(new LambdaQueryWrapper<Checkin>()
                .eq(Checkin::getUserId, userId)
                .eq(Checkin::getCheckinDate, d));
        if (exist != null) {
            exist.setStreakDays(calcStreak(userId, d));
            return exist; // 幂等返回
        }

        // 2. 没打卡则插入
        Checkin c = new Checkin();
        c.setUserId(userId);
        c.setEmotion(emotion);
        c.setIntensity(intensity);
        c.setNote(note);
        c.setCheckinDate(d);
        try {
            checkinMapper.insert(c);
        } catch (DuplicateKeyException e) {
            // 3. 并发兜底（数据库唯一约束生效）
            Checkin fallback = checkinMapper.selectOne(new LambdaQueryWrapper<Checkin>()
                    .eq(Checkin::getUserId, userId)
                    .eq(Checkin::getCheckinDate, d));
            if (fallback != null) {
                fallback.setStreakDays(calcStreak(userId, d));
                return fallback;
            }
        }
        c.setStreakDays(calcStreak(userId, d));
        return c;
    }

    // 契约：GET /api/emotions/checkins?from&to -> { items, streakDays, total }
    public List<Checkin> list(Long userId, String from, String to) {
        LocalDate start = (from != null) ? LocalDate.parse(from) : LocalDate.MIN;
        LocalDate end = (to != null) ? LocalDate.parse(to) : LocalDate.MAX;
        List<Checkin> items = checkinMapper.selectList(new LambdaQueryWrapper<Checkin>()
                .eq(Checkin::getUserId, userId)
                .ge(Checkin::getCheckinDate, start)
                .le(Checkin::getCheckinDate, end)
                .orderByAsc(Checkin::getCheckinDate));
        items.forEach(c -> c.setStreakDays(calcStreak(userId, c.getCheckinDate())));
        return items;
    }

    public int streakDays(Long userId) {
        return calcStreak(userId, LocalDate.now());
    }

    // 从 upTo 往前数连续打卡天数，断签归零
    private int calcStreak(Long userId, LocalDate upTo) {
        int streak = 0;
        LocalDate d = upTo;
        boolean todayHas = checkinMapper.selectCount(new LambdaQueryWrapper<Checkin>()
                .eq(Checkin::getUserId, userId)
                .eq(Checkin::getCheckinDate, d)) > 0;
        if (!todayHas) d = d.minusDays(1);
        while (checkinMapper.selectCount(new LambdaQueryWrapper<Checkin>()
                .eq(Checkin::getUserId, userId)
                .eq(Checkin::getCheckinDate, d)) > 0) {
            streak++;
            d = d.minusDays(1);
        }
        return streak;
    }
}
