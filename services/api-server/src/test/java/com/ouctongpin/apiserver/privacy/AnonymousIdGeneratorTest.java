package com.ouctongpin.apiserver.privacy;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class AnonymousIdGeneratorTest {
    private final String secret = "test-only-secret-at-least-32-bytes-long";

    @Test void stableScopedAndKeyed() {
        AnonymousIdGenerator generator = new AnonymousIdGenerator(secret);
        String id = generator.generate("user-42", "treehole");
        assertEquals(id, generator.generate("user-42", "treehole"));
        assertTrue(id.matches("anon_v1_[A-Za-z0-9_-]{43}"));
        assertFalse(id.contains("user-42"));
        assertNotEquals(id, generator.generate("user-43", "treehole"));
        assertNotEquals(id, generator.generate("user-42", "match"));
        assertNotEquals(id, new AnonymousIdGenerator(secret + "-rotated").generate("user-42", "treehole"));
    }

    @Test void rejectMissingWeakKeysAndInvalidIdentity() {
        for (String key : new String[]{null, "", "too-short"}) {
            assertThrows(IllegalStateException.class,
                    () -> new AnonymousIdGenerator(key).generate("user", "treehole"));
        }
        AnonymousIdGenerator generator = new AnonymousIdGenerator(secret);
        assertThrows(IllegalArgumentException.class, () -> generator.generate(null, "treehole"));
        assertThrows(IllegalArgumentException.class, () -> generator.generate(" ", "treehole"));
        assertThrows(IllegalArgumentException.class, () -> generator.generate("user", "a\0b"));
        assertThrows(IllegalArgumentException.class, () -> generator.generate("user", null));
    }
}
