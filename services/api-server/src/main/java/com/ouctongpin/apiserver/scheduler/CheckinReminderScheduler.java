package com.ouctongpin.apiserver.scheduler;

import com.ouctongpin.apiserver.service.CheckinService;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * US-02 打卡提醒定时任务骨架。
 *
 * 当前为占位实现：每天 21:00 触发，应扫描"今日未打卡"的用户并推送微信订阅消息。
 * TODO(M5/后端):
 *   1. 注入用户仓储，取出全部用户
 *   2. 用 CheckinService.streakDays / 当日记录判断未打卡
 *   3. 调微信订阅消息 API（需小程序 access_token + 模板 ID）推送
 *   4. 失败重试与频控
 */
@Component
public class CheckinReminderScheduler {

    private final CheckinService checkinService;

    public CheckinReminderScheduler(CheckinService checkinService) {
        this.checkinService = checkinService;
    }

    @Scheduled(cron = "0 0 21 * * ?")
    public void remind() {
        // TODO: 遍历用户 -> 若今日未打卡 -> 发送订阅消息
        // int streak = checkinService.streakDays(userId);
    }
}
