package com.ouctongpin.apiserver.privacy;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.util.Base64;

/** Stable, purpose-scoped pseudonyms. Never use a student number as internalUserId. */
@Component
public class AnonymousIdGenerator {
    private final String secret;

    public AnonymousIdGenerator(@Value("${privacy.anonymous-id-secret:}") String secret) {
        this.secret = secret;
    }

    public String generate(String internalUserId, String purpose) {
        if (secret == null || secret.getBytes(StandardCharsets.UTF_8).length < 32) {
            throw new IllegalStateException("Anonymous ID secret must contain at least 32 bytes");
        }
        if (internalUserId == null || internalUserId.isBlank()
                || purpose == null || !purpose.matches("[a-z][a-z0-9-]{0,31}")) {
            throw new IllegalArgumentException("Internal user ID and valid purpose are required");
        }
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] digest = mac.doFinal((purpose + "\0" + internalUserId).getBytes(StandardCharsets.UTF_8));
            return "anon_v1_" + Base64.getUrlEncoder().withoutPadding().encodeToString(digest);
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("HMAC-SHA256 is unavailable", e);
        }
    }
}
