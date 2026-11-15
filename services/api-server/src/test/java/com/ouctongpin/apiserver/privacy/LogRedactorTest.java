package com.ouctongpin.apiserver.privacy;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.LoggerContext;
import ch.qos.logback.classic.PatternLayout;
import ch.qos.logback.classic.spi.LoggingEvent;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static org.junit.jupiter.api.Assertions.*;

class LogRedactorTest {
    @ParameterizedTest
    @ValueSource(strings = {"phone=13800000000", "学号=202600000001", "studentId=abc-test",
            "身份证=11000020000101000X", "user=test@example.com", "Authorization: Bearer abc.def.ghi",
            "{\"password\":\"test password with spaces\"}", "token=abcxyz&ok=true",
            "{\"studentId\": \"202600000001\"}", "Bearer abc.def.ghi",
            "Authorization: Basic dGVzdDpwYXNz", "Basic dGVzdDpwYXNz",
            "password=\"test password\nwith spaces\"",
            "refresh_token=abcxyz", "accessToken=abcxyz", "student_no=abc-test",
            "sessionKey=abcxyz", "open_id=abcxyz", "api_key=abcxyz", "client_secret=abcxyz",
            "{\"student_no\":1234567}", "{\"password\":\"test password\\\"with spaces\"}"})
    void removesSensitiveValues(String input) {
        String output = LogRedactor.redact(input);
        assertNotEquals(input, output);
        assertTrue(output.contains("[REDACTED]"));
        for (String value : new String[]{"13800000000", "202600000001", "abc.def.ghi",
                "11000020000101000X", "test@example.com", "test password", "abcxyz", "abc-test",
                "dGVzdDpwYXNz", "with spaces", "1234567"}) {
            assertFalse(output.contains(value), output);
        }
    }

    @Test void preservesUsefulDiagnostics() {
        assertNull(LogRedactor.redact(null));
        assertEquals("status=500 duration=30ms", LogRedactor.redact("status=500 duration=30ms"));
        assertEquals("notsecret=public notstudentId=example", LogRedactor.redact(
                "notsecret=public notstudentId=example"));
    }

    @Test void actualLogbackPatternRedactsExceptionsAndArguments() {
        LoggerContext context = new LoggerContext();
        PatternLayout layout = new PatternLayout();
        layout.setContext(context);
        layout.getInstanceConverterMap().put("redact", RedactingCompositeConverter.class.getName());
        layout.setPattern("%redact(%msg%n%ex)");
        layout.start();
        LoggingEvent event = new LoggingEvent("test", context.getLogger("test"), Level.ERROR,
                "phone={}", new IllegalArgumentException("studentId=202600000001"),
                new Object[]{"13800000000"});
        String rendered = layout.doLayout(event);
        assertTrue(rendered.contains("IllegalArgumentException"), rendered);
        assertFalse(rendered.contains("13800000000"), rendered);
        assertFalse(rendered.contains("202600000001"), rendered);
        context.stop();
    }

    @Test void formattedJsonAndExceptionCredentialsAreRedactedTogether() {
        LoggerContext context = new LoggerContext();
        PatternLayout layout = new PatternLayout();
        layout.setContext(context);
        layout.getInstanceConverterMap().put("redact", RedactingCompositeConverter.class.getName());
        layout.setPattern("%redact(%msg%n%ex)");
        layout.start();
        LoggingEvent event = new LoggingEvent("test", context.getLogger("test"), Level.ERROR,
                "request={}", new IllegalArgumentException("refresh_token=synthetic-refresh-private"),
                new Object[]{"{\"student_no\":\"synthetic-student-private\","
                        + "\"apiKey\":\"synthetic-api-private\"}"});
        String rendered = layout.doLayout(event);
        assertTrue(rendered.contains("IllegalArgumentException"));
        assertFalse(rendered.contains("synthetic-refresh-private"));
        assertFalse(rendered.contains("synthetic-student-private"));
        assertFalse(rendered.contains("synthetic-api-private"));
        context.stop();
    }

    @ParameterizedTest
    @ValueSource(ints = {5000, 20000})
    void longQuotedAndUnterminatedValuesDoNotOverflowTheStack(int length) {
        String value = "q".repeat(length);
        assertEquals("password=\"[REDACTED]\" status=500", LogRedactor.redact(
                "password=\"" + value + "\" status=500"));
        assertEquals("{\"client_secret\":\"[REDACTED]\"}", LogRedactor.redact(
                "{\"client_secret\":\"" + value + "\\\"" + value + "\"}"));
        assertEquals("password=\"[REDACTED]", LogRedactor.redact("password=\"" + value));
    }

    @Test void actualLogbackHandlesLongQuotedArgumentsAndExceptionValues() {
        LoggerContext context = new LoggerContext();
        PatternLayout layout = new PatternLayout();
        layout.setContext(context);
        layout.getInstanceConverterMap().put("redact", RedactingCompositeConverter.class.getName());
        layout.setPattern("%redact(%msg%n%ex)");
        layout.start();
        String value = "q".repeat(20000);
        LoggingEvent event = new LoggingEvent("test", context.getLogger("test"), Level.ERROR,
                "request={}", new IllegalArgumentException("refresh_token=\"" + value + "\""),
                new Object[]{"{\"password\":\"" + value + "\"}"});
        String rendered = layout.doLayout(event);
        assertTrue(rendered.contains("IllegalArgumentException"));
        assertTrue(rendered.contains("[REDACTED]"));
        assertFalse(rendered.contains("qqqqqqqq"));
        assertTrue(rendered.length() < 10000);
        context.stop();
    }
}
