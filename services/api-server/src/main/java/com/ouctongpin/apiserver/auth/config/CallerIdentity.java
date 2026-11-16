package com.ouctongpin.apiserver.auth.config;

import java.security.Principal;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

public final class CallerIdentity {
    private CallerIdentity() { }

    public static long require(Principal principal) {
        if (principal != null) {
            try {
                long id = Long.parseLong(principal.getName());
                if (id > 0) return id;
            } catch (NumberFormatException ignored) { }
        }
        throw new ResponseStatusException(HttpStatus.UNAUTHORIZED);
    }
}
