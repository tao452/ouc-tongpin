package com.ouctongpin.apiserver.service;

import com.ouctongpin.apiserver.model.Checkin;
import com.ouctongpin.apiserver.model.CheckinRequest;

import java.util.List;

public interface CheckinService {
    /** 提交/幂等返回当日打卡 */
    Checkin checkin(String userId, CheckinRequest req);

    /** 区间内的打卡记录（from/to 为 YYYY-MM-DD，可空） */
    List<Checkin> list(String userId, String from, String to);

    /** 连续打卡天数（断签归零） */
    int streakDays(String userId);
}
