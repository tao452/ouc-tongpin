package com.ouctongpin.apiserver.common;

public class DesensitizeUtil {

    // 手机号脱敏：138****1234
    public static String phone(String p) {
        if (p == null || p.length() < 7) return p;
        return p.replaceAll("(\\d{3})\\d{4}(\\d{4})", "$1****$2");
    }

    // 学号/长字符串脱敏：只保留后 4 位
    public static String studentNo(String s) {
        if (s == null || s.length() <= 4) return s;
        return "***" + s.substring(s.length() - 4);
    }

    // openid脱敏：只保留前 6 位
    public static String openid(String o) {
        if (o == null || o.length() <= 6) return o;
        return o.substring(0, 6) + "***";
    }
}
