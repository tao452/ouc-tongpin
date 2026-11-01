package com.ouctongpin.apiserver.checkin.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.ouctongpin.apiserver.checkin.entity.Checkin;
import com.ouctongpin.apiserver.checkin.mapper.CheckinMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import java.time.LocalDate;

@Service
public class CheckinService {
    @Autowired private CheckinMapper checkinMapper;

    public Checkin doCheckin(Long userId, Long emotionWordId) {
        LocalDate today = LocalDate.now();
        // 1. 先查是否已打卡
        Checkin exist = checkinMapper.selectOne(new LambdaQueryWrapper<Checkin>()
            .eq(Checkin::getUserId, userId)
            .eq(Checkin::getCheckinDate, today));
        if (exist != null) return exist; // 幂等返回

        // 2. 没打卡则插入
        Checkin c = new Checkin();
        c.setUserId(userId);
        c.setEmotionWordId(emotionWordId);
        c.setCheckinDate(today);
        try {
            checkinMapper.insert(c);
        } catch (DuplicateKeyException e) {
            // 3. 并发兜底（数据库唯一约束生效）
            return checkinMapper.selectOne(new LambdaQueryWrapper<Checkin>()
                .eq(Checkin::getUserId, userId)
                .eq(Checkin::getCheckinDate, today));
        }
        return c;
    }
}
