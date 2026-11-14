package com.ouctongpin.apiserver.buddy.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ouctongpin.apiserver.buddy.dto.BuddyCreateReq;
import com.ouctongpin.apiserver.buddy.dto.BuddyResponse;
import com.ouctongpin.apiserver.buddy.entity.BuddyDemand;
import com.ouctongpin.apiserver.buddy.mapper.BuddyDemandMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class BuddyService {
    @Autowired private BuddyDemandMapper buddyMapper;

    // 发布搭子
    public Long createBuddy(Long userId, BuddyCreateReq req) {
        BuddyDemand demand = new BuddyDemand();
        demand.setUserId(userId);
        demand.setTitle(req.getTitle());
        demand.setDescription(req.getDescription());
        demand.setScene(req.getScene());
        demand.setEventTime(req.getEventTime());
        demand.setLocationName(req.getLocationName());
        demand.setLongitude(req.getLongitude());
        demand.setLatitude(req.getLatitude());
        demand.setSkillTags(req.getSkillTags());
        demand.setStatus(0);
        buddyMapper.insert(demand);
        return demand.getId();
    }

    // 获取搭子列表（分页）
    public Page<BuddyResponse> listBuddies(int pageNum, int pageSize, String scene) {
        Page<BuddyDemand> page = new Page<>(pageNum, pageSize);

        LambdaQueryWrapper<BuddyDemand> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(BuddyDemand::getDeleted, 0)
            .eq(BuddyDemand::getStatus, 0);

        // 如果传了场景，就按场景过滤
        if (scene != null && !scene.isEmpty()) {
            wrapper.eq(BuddyDemand::getScene, scene);
        }

        // 按照发布时间倒序排列
        wrapper.orderByDesc(BuddyDemand::getCreatedAt);

        buddyMapper.selectPage(page, wrapper);

        // 转换成不含真实 userId 的 DTO
        Page<BuddyResponse> resPage = new Page<>(page.getCurrent(), page.getSize(), page.getTotal());
        List<BuddyResponse> records = page.getRecords().stream().map(d -> {
            BuddyResponse r = new BuddyResponse();
            r.setId(d.getId());
            r.setTitle(d.getTitle());
            r.setDescription(d.getDescription());
            r.setScene(d.getScene());
            r.setEventTime(d.getEventTime());
            r.setLocationName(d.getLocationName());
            r.setSkillTags(d.getSkillTags());
            r.setCreatedAt(d.getCreatedAt());
            return r;
        }).collect(Collectors.toList());
        resPage.setRecords(records);

        return resPage;
    }
}
