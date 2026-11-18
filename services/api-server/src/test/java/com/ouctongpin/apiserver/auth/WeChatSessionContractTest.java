package com.ouctongpin.apiserver.auth;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.auth.config.JwtUtil;
import com.ouctongpin.apiserver.auth.service.WeChatSessionClient;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.web.server.ResponseStatusException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;
import static org.junit.jupiter.api.Assertions.*;

/** Provider HTTP contract tests use a local stub, not live WeChat credentials. */
class WeChatSessionContractTest {
    @ParameterizedTest @ValueSource(strings = {"", "short", "change-me-placeholder-key-at-least-32-bytes",
            "ouctongpin-secret-key-1234567890abcdefghijklmn"})
    void weakOrPublicSigningKeysCannotStart(String secret) {
        assertThrows(IllegalStateException.class, () -> new JwtUtil(secret, 120));
    }

    @Test void liveModeNeverSilentlyFallsBackToMock() {
        assertThrows(IllegalStateException.class,
                () -> new WeChatSessionClient("", "", false, new ObjectMapper()));
        var fixture = new WeChatSessionClient("", "", true, new ObjectMapper());
        assertEquals(fixture.exchange("one"), fixture.exchange("one"));
        assertNotEquals(fixture.exchange("one"), fixture.exchange("two"));
    }

    @Test void validatesProviderResponseAndDoesNotReturnSessionCredentials() throws Exception {
        AtomicReference<String> query = new AtomicReference<>();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            query.set(exchange.getRequestURI().getRawQuery());
            byte[] response = "{\"openid\":\"verified-provider-user\",\"session_key\":\"PRIVATE-SESSION\"}"
                    .getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, response.length);
            try (var out = exchange.getResponseBody()) { out.write(response); }
        });
        server.start();
        try {
            var client = client(server);
            assertEquals("verified-provider-user", client.exchange("code&extra=value"));
            assertTrue(query.get().contains("js_code=code%26extra%3Dvalue"));
            assertTrue(query.get().endsWith("grant_type=authorization_code"));
        } finally { server.stop(0); }
    }

    @ParameterizedTest @ValueSource(strings = {"{", "[]", "{}", "{\"openid\":123}",
            "{\"errcode\":45011,\"errmsg\":\"PRIVATE-UPSTREAM\"}",
            "{\"errcode\":\"invalid\",\"openid\":\"value\"}"})
    void malformedOrUnavailableProviderFailsClosedWithoutEcho(String body) throws Exception {
        assertEquals(503, status(body, 200));
    }

    @Test void invalidCodeIsUnauthorizedAndRedirectIsNeverFollowed() throws Exception {
        assertEquals(401, status("{\"errcode\":40029,\"errmsg\":\"PRIVATE-UPSTREAM\"}", 200));
        assertEquals(503, status("PRIVATE-UPSTREAM", 302));
        assertEquals(503, status("x".repeat(8193), 200));
    }

    private int status(String body, int httpStatus) throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            byte[] raw = body.getBytes(StandardCharsets.UTF_8);
            if (httpStatus == 302) exchange.getResponseHeaders().set("Location",
                    "http://127.0.0.1:" + server.getAddress().getPort() + "/followed");
            exchange.sendResponseHeaders(httpStatus, raw.length);
            try (var out = exchange.getResponseBody()) { out.write(raw); }
        });
        server.createContext("/followed", exchange -> {
            byte[] valid = "{\"openid\":\"must-not-follow\"}".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, valid.length);
            try (var out = exchange.getResponseBody()) { out.write(valid); }
        });
        server.start();
        try {
            var error = assertThrows(ResponseStatusException.class, () -> client(server).exchange("code"));
            assertFalse(error.getMessage().contains("PRIVATE-UPSTREAM"));
            assertFalse(error.getMessage().contains("provider-secret"));
            return error.getStatusCode().value();
        } finally { server.stop(0); }
    }

    private WeChatSessionClient client(HttpServer server) {
        return new WeChatSessionClient("provider-app", "provider-secret", false, new ObjectMapper(),
                URI.create("http://127.0.0.1:" + server.getAddress().getPort() + "/"));
    }
}
