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
            "{\"studentId\": \"202600000001\"}", "Bearer abc.def.ghi"})
    void removesSensitiveValues(String input) {
        String output = LogRedactor.redact(input);
        assertNotEquals(input, output);
        assertTrue(output.contains("[REDACTED]"));
        for (String value : new String[]{"13800000000", "202600000001", "abc.def.ghi",
                "11000020000101000X", "test@example.com", "test password", "abcxyz", "abc-test"}) {
            assertFalse(output.contains(value), output);
        }
    }

    @Test void preservesUsefulDiagnostics() {
        assertNull(LogRedactor.redact(null));
        assertEquals("status=500 duration=30ms", LogRedactor.redact("status=500 duration=30ms"));
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
}
