package com.ouctongpin.apiserver.privacy;

import java.util.regex.Pattern;

/** Defense in depth for logs; callers must still avoid logging request bodies or credentials. */
public final class LogRedactor {
    private static final String KEYS = "authorization|token|password|secret|openid|session_key|"
            + "student_?id|studentNumber|学号|手机号|身份证";
    private static final Pattern QUOTED = Pattern.compile(
            "(?is)([\"']?(?:" + KEYS + ")[\"']?\\s*[:=]\\s*)([\"'])(.*?)\\2");
    private static final Pattern BARE = Pattern.compile(
            "(?i)((?:" + KEYS + ")\\s*[:=]\\s*)(?:(?:Bearer|Basic)\\s+)?[^\\s,;}&\\\"']+");
    private static final Pattern AUTH = Pattern.compile("(?i)(Bearer|Basic)\\s+[A-Za-z0-9._~+/-]+=*");
    private static final Pattern NUMBER = Pattern.compile("(?<![0-9])[0-9]{8,20}[xX]?(?![0-9])");
    private static final Pattern EMAIL = Pattern.compile("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}");

    private LogRedactor() {}

    public static String redact(String input) {
        if (input == null) return null;
        String result = QUOTED.matcher(input).replaceAll("$1$2[REDACTED]$2");
        result = BARE.matcher(result).replaceAll("$1[REDACTED]");
        result = AUTH.matcher(result).replaceAll("$1 [REDACTED]");
        result = NUMBER.matcher(result).replaceAll("[REDACTED]");
        return EMAIL.matcher(result).replaceAll("[REDACTED]");
    }
}
