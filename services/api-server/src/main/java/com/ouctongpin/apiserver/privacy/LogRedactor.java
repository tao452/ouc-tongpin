package com.ouctongpin.apiserver.privacy;

import java.util.regex.Pattern;
import java.util.regex.Matcher;

/** Defense in depth for logs; callers must still avoid logging request bodies or credentials. */
public final class LogRedactor {
    private static final String KEYS = "authorization|(?:access|refresh)_?token|token|password|"
            + "(?:client_?)?secret|anon_id_secret|api_?key|open_?id|session_?key|"
            + "student_?(?:id|no|number)|学号|手机号|身份证";
    private static final String KEY_PREFIX = "(?<![\\p{L}\\p{N}_])[\"']?(?:" + KEYS
            + ")[\"']?\\s*[:=]\\s*";
    private static final Pattern QUOTED_START = Pattern.compile("(?i)(" + KEY_PREFIX + ")([\"'])");
    private static final Pattern BARE = Pattern.compile(
            "(?i)(" + KEY_PREFIX + ")(?:(?:Bearer|Basic)\\s+)?[^\\s,;}&\\\"']+");
    private static final Pattern AUTH = Pattern.compile(
            "(?i)(?<![\\p{L}\\p{N}_])(Bearer|Basic)\\s+[A-Za-z0-9._~+/-]+=*");
    private static final Pattern NUMBER = Pattern.compile("(?<![0-9])[0-9]{8,20}[xX]?(?![0-9])");
    private static final Pattern EMAIL = Pattern.compile("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}");

    private LogRedactor() {}

    public static String redact(String input) {
        if (input == null) return null;
        String result = redactQuoted(input);
        result = BARE.matcher(result).replaceAll("$1[REDACTED]");
        result = AUTH.matcher(result).replaceAll("$1 [REDACTED]");
        result = NUMBER.matcher(result).replaceAll("[REDACTED]");
        return EMAIL.matcher(result).replaceAll("[REDACTED]");
    }

    /** Scan values iteratively: a repeated regex group can overflow the stack on long log values. */
    private static String redactQuoted(String input) {
        Matcher start = QUOTED_START.matcher(input);
        StringBuilder result = new StringBuilder(input.length());
        int cursor = 0;
        while (cursor < input.length() && start.find(cursor)) {
            char quote = start.group(2).charAt(0);
            int end = start.end();
            while (end < input.length()) {
                char current = input.charAt(end);
                if (current == quote) break;
                if (current == '\\' && end + 1 < input.length()) end++;
                end++;
            }
            result.append(input, cursor, start.start()).append(start.group(1))
                    .append(quote).append("[REDACTED]");
            if (end < input.length()) {
                result.append(quote);
                cursor = end + 1;
            } else {
                // An unterminated quoted value must not leak its remainder.
                cursor = input.length();
            }
        }
        return result.append(input, cursor, input.length()).toString();
    }
}
