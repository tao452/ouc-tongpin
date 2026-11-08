package com.ouctongpin.apiserver.privacy;

import ch.qos.logback.classic.LoggerContext;
import ch.qos.logback.classic.joran.JoranConfigurator;
import ch.qos.logback.classic.util.LogbackMDCAdapter;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.parallel.ResourceLock;
import org.junit.jupiter.api.parallel.Resources;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import static org.junit.jupiter.api.Assertions.*;

/** Explicit catalogue execution with synthetic identities; no real account/database access. */
@ResourceLock(Resources.SYSTEM_OUT)
class CataloguePrivacyExecutionTest {
    private final String key = "catalogue-test-key-at-least-32-bytes";

    @Test void S1_069_stableAlias() {
        AnonymousIdGenerator g = new AnonymousIdGenerator(key);
        String result = g.generate("synthetic-user-a", "treehole");
        assertEquals(result, g.generate("synthetic-user-a", "treehole"));
        assertFalse(result.contains("synthetic-user-a"));
    }

    @Test void S1_070_userIsolation() {
        AnonymousIdGenerator g = new AnonymousIdGenerator(key);
        assertNotEquals(g.generate("synthetic-user-a", "treehole"),
                g.generate("synthetic-user-b", "treehole"));
    }

    @Test void S1_071_purposeIsolation() {
        AnonymousIdGenerator g = new AnonymousIdGenerator(key);
        assertNotEquals(g.generate("synthetic-user-a", "treehole"),
                g.generate("synthetic-user-a", "match"));
    }

    @Test void S1_072_keyChange() {
        assertNotEquals(new AnonymousIdGenerator(key).generate("synthetic-user-a", "treehole"),
                new AnonymousIdGenerator(key + "-second").generate("synthetic-user-a", "treehole"));
    }

    @Test void S1_073_weakKeyRejected() {
        for (String secret : new String[]{null, "", "too-short"}) {
            assertThrows(IllegalStateException.class,
                    () -> new AnonymousIdGenerator(secret).generate("synthetic-user-a", "treehole"));
        }
    }

    @Test void S1_074_consoleRedaction() throws Exception {
        String output = log(false);
        assertTrue(output.contains("[REDACTED]"));
        assertFalse(output.contains("13800000000"));
        assertFalse(output.contains("202600000001"));
        assertFalse(output.contains("synthetic@example.com"));
        assertFalse(output.contains("test-token-only"));
    }

    @Test void S1_075_exceptionRedaction() throws Exception {
        String output = log(true);
        assertTrue(output.contains("IllegalArgumentException"));
        assertTrue(output.contains("[REDACTED]"));
        assertFalse(output.contains("202600000001"));
    }

    private String log(boolean exception) throws Exception {
        PrintStream original = System.out;
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        LoggerContext context = new LoggerContext();
        context.setMDCAdapter(new LogbackMDCAdapter());
        try {
            System.setOut(new PrintStream(bytes, true, StandardCharsets.UTF_8));
            JoranConfigurator config = new JoranConfigurator();
            config.setContext(context);
            config.doConfigure(Path.of("src/main/resources/logback-spring.xml").toFile());
            if (exception) {
                context.getLogger("catalogue").error("synthetic failure",
                        new IllegalArgumentException("studentId=202600000001"));
            } else {
                context.getLogger("catalogue").info("phone={} studentId={} email={} token={}",
                        "13800000000", "202600000001", "synthetic@example.com", "test-token-only");
            }
        } finally {
            context.stop();
            System.setOut(original);
        }
        return bytes.toString(StandardCharsets.UTF_8);
    }
}
