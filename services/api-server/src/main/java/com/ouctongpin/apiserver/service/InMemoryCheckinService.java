package com.ouctongpin.apiserver.service;

import com.ouctongpin.apiserver.model.Checkin;
import com.ouctongpin.apiserver.model.CheckinRequest;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 骨架阶段的内存实现，保证接口可独立启动与联调。
 * TODO(M5): 接入 JPA + MySQL 后替换为持久化实现，并补幂等/断签/连续天数真实逻辑。
 */
@Service
public class InMemoryCheckinService implements CheckinService {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd");
    // userId -> (date -> Checkin)
    private final Map<String, Map<LocalDate, Checkin>> store = new ConcurrentHashMap<>();

    @Override
    public Checkin checkin(String userId, CheckinRequest req) {
        LocalDate date = (req.checkinDate != null)
                ? LocalDate.parse(req.checkinDate, FMT)
                : LocalDate.now();
        Map<LocalDate, Checkin> userMap = store.computeIfAbsent(userId, k -> new ConcurrentHashMap<>());

        // 幂等：同一天已打卡直接返回已有记录，不新增
        Checkin existing = userMap.get(date);
        if (existing != null) {
            return existing;
        }

        Checkin c = new Checkin();
        c.id = userId + "-" + date;
        c.checkinDate = date.format(FMT);
        c.emotion = req.emotion;
        c.intensity = req.intensity;
        c.note = req.note;
        c.streakDays = computeStreak(userId, date);
        userMap.put(date, c);
        return c;
    }

    @Override
    public List<Checkin> list(String userId, String from, String to) {
        Map<LocalDate, Checkin> userMap = store.getOrDefault(userId, Map.of());
        LocalDate start = (from != null) ? LocalDate.parse(from, FMT) : LocalDate.MIN;
        LocalDate end = (to != null) ? LocalDate.parse(to, FMT) : LocalDate.MAX;
        List<Checkin> items = new ArrayList<>();
        for (Map.Entry<LocalDate, Checkin> e : userMap.entrySet()) {
            if (!e.getKey().isBefore(start) && !e.getKey().isAfter(end)) {
                items.add(e.getValue());
            }
        }
        items.sort(Comparator.comparing(c -> c.checkinDate));
        return items;
    }

    @Override
    public int streakDays(String userId) {
        Map<LocalDate, Checkin> userMap = store.getOrDefault(userId, Map.of());
        if (userMap.isEmpty()) return 0;
        int streak = 0;
        LocalDate d = LocalDate.now();
        // 今天没打卡则从昨天起算
        if (!userMap.containsKey(d)) d = d.minusDays(1);
        while (userMap.containsKey(d)) {
            streak++;
            d = d.minusDays(1);
        }
        return streak;
    }

    private int computeStreak(String userId, LocalDate today) {
        Map<LocalDate, Checkin> userMap = store.getOrDefault(userId, Map.of());
        int streak = 1;
        LocalDate d = today.minusDays(1);
        while (userMap.containsKey(d)) {
            streak++;
            d = d.minusDays(1);
        }
        return streak;
    }
}
