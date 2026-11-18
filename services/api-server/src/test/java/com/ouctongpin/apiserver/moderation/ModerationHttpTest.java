package com.ouctongpin.apiserver.moderation;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import static org.junit.jupiter.api.Assertions.*;

class ModerationHttpTest {
    @Test void productionRequestFactoryMakesRealHttpRequest() throws Exception {
        HttpServer upstream = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        upstream.createContext("/api/moderation/check", exchange -> {
            String input = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            byte[] body = (input.contains("allow")
                    ? "{\"passed\":true,\"normalized\":\"allow\",\"hits\":[]}"
                    : "{\"passed\":false,\"normalized\":\"blocked\",\"hits\":[{\"word\":\"x\",\"level\":\"HIGH\"}]}")
                    .getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        upstream.start();
        try {
            ModerationClient client = new ModerationClient(RestClient.builder(),
                    "http://127.0.0.1:" + upstream.getAddress().getPort());
            assertTrue(client.requireAllowed("allow").passed());
            assertEquals(422, assertThrows(ResponseStatusException.class,
                    () -> client.requireAllowed("block")).getStatusCode().value());
        } finally {
            upstream.stop(0);
        }
    }
}
