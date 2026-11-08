package com.ouctongpin.apiserver.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * 情绪词表，契约见 packages/contract/openapi.yaml 的 GET /api/emotions/words。
 *
 * 6 个情绪词 + 1–5 级强度量表，供前端下拉 / 选择使用，避免前端硬编码。
 * 词表目前是静态常量；后续若由运营后台配置，替换数据来源即可，接口形状不变。
 */
@RestController
@RequestMapping("/api/emotions")
public class EmotionWordController {

    static final List<Map<String, String>> WORDS = List.of(
            Map.of("code", "HAPPY", "label", "开心", "colorToken", "emotion.happy"),
            Map.of("code", "CALM", "label", "平静", "colorToken", "emotion.calm"),
            Map.of("code", "ANXIOUS", "label", "焦虑", "colorToken", "emotion.anxious"),
            Map.of("code", "LONELY", "label", "孤独", "colorToken", "emotion.lonely"),
            Map.of("code", "IRRITABLE", "label", "烦躁", "colorToken", "emotion.irritable"),
            Map.of("code", "DOWN", "label", "低落", "colorToken", "emotion.down")
    );

    @GetMapping("/words")
    public Map<String, Object> words() {
        return Map.of(
                "words", WORDS,
                "intensityScale", Map.of("min", 1, "max", 5)
        );
    }
}
