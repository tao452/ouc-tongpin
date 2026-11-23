package com.ouctongpin.apiserver.matching;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class MatchingScoreClientTest {
    private static final String HASH = "a".repeat(64);
    private final MatchingScoreClient.Profile query = new MatchingScoreClient.Profile(
            null, List.of("ＰＹＴＨＯＮ", "跑步"), null, null);
    private final MatchingScoreClient.Candidate candidate = MatchingScoreClient.Candidate.from(
            "candidate-a", new MatchingScoreClient.Profile(null, List.of("python"), null, null));

    private MatchingScoreClient client(HttpServer server, int readMs) {
        return new MatchingScoreClient(RestClient.builder(),
                "http://127.0.0.1:" + server.getAddress().getPort(), 100, readMs);
    }

    private HttpServer serve(int status, String body, boolean header) throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/score", exchange -> {
            exchange.getRequestBody().readAllBytes();
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            if (header) exchange.getResponseHeaders().set("X-Score-Config-SHA256", HASH);
            byte[] raw = body.getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(status, raw.length);
            try (var output = exchange.getResponseBody()) { output.write(raw); }
        });
        server.start();
        return server;
    }

    private String validResponse(String id, String score) {
        return "{\"items\":[{\"id\":\"" + id + "\",\"score\":" + score
                + "}],\"feature_version\":\"features-v0.1-proposed\","
                + "\"weights_version\":\"equal-w0.1-proposed\",\"config_sha256\":\""
                + HASH + "\",\"fallback\":false}";
    }

    @Test void actualHttpSingleAndBatchValidateIdentityAndVersion() throws Exception {
        var server = serve(200, validResponse("candidate-a", "72.5"), true);
        try {
            var client = client(server, 1000);
            var single = client.scoreSingle(query, candidate);
            assertFalse(single.fallback());
            assertEquals(72.5, single.items().get(0).score());
            assertEquals(HASH, single.configSha256());
            assertEquals(single, client.scoreBatch(query, List.of(candidate)));
        } finally { server.stop(0); }
    }

    @Test void unavailableServiceUsesVisibleNormalizedTagBaseline() throws Exception {
        var server = serve(503, "{\"detail\":\"private internal input\"}", false);
        try {
            var result = client(server, 1000).scoreSingle(query, candidate);
            assertTrue(result.fallback());
            assertEquals("SERVICE_UNAVAILABLE", result.reason());
            assertEquals(50, result.items().get(0).score());
            assertNull(result.configSha256());
            assertFalse(result.toString().contains("private internal input"));
        } finally { server.stop(0); }
    }

    @Test void invalidParametersAreNotChangedIntoFallbackSuccess() throws Exception {
        var server = serve(400, "{\"detail\":\"private input\"}", false);
        try {
            var client = client(server, 1000);
            var error = assertThrows(ResponseStatusException.class,
                    () -> client.scoreSingle(query, candidate));
            assertEquals(400, error.getStatusCode().value());
            assertFalse(error.getMessage().contains("private input"));
            assertThrows(ResponseStatusException.class, () -> client.scoreBatch(query, List.of()));
            assertThrows(ResponseStatusException.class,
                    () -> client.scoreBatch(query, List.of(candidate, candidate)));
        } finally { server.stop(0); }
    }

    @Test void wrongIdsScoresOrMissingFingerprintAreNotTrusted() throws Exception {
        for (String body : List.of(validResponse("wrong-id", "72"),
                validResponse("candidate-a", "101"), "{}")) {
            var server = serve(200, body, true);
            try {
                assertEquals("INVALID_RESPONSE", client(server, 1000).scoreSingle(query, candidate).reason());
            } finally { server.stop(0); }
        }
        var server = serve(200, validResponse("candidate-a", "72"), false);
        try { assertTrue(client(server, 1000).scoreSingle(query, candidate).fallback()); }
        finally { server.stop(0); }
    }

    @Test void readTimeoutFallsBackWithoutWaitingForAFullSlowResponse() throws Exception {
        var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/score", exchange -> {
            try { Thread.sleep(400); } catch (InterruptedException error) { Thread.currentThread().interrupt(); }
            exchange.close();
        });
        server.start();
        try {
            var client = client(server, 50);
            long started = System.nanoTime();
            var result = client.scoreSingle(query, candidate);
            assertTrue(result.fallback());
            assertEquals("TIMEOUT", result.reason());
            assertTrue((System.nanoTime() - started) / 1e6 < 350);
        } finally { server.stop(0); }
    }

    @Test void boundsAndTimestampFormatAreRejectedBeforeNetworkAndUnicodeTagsAgree() throws Exception {
        assertThrows(ResponseStatusException.class, () -> new MatchingScoreClient.Profile(
                null, null, null, new MatchingScoreClient.Location(90.01, 0)));
        assertThrows(ResponseStatusException.class, () -> new MatchingScoreClient.Profile(
                List.of(Double.NaN, 0.0, 0.0, 0.0, 0.0, 0.0), null, null, null));
        assertThrows(ResponseStatusException.class, () -> new MatchingScoreClient.Profile(
                null, List.of("x".repeat(33)), null, null));
        assertThrows(ResponseStatusException.class, () -> new MatchingScoreClient.TimeSlot(
                "2026-12-01 09:00:00Z", "2026-12-01T10:00:00Z"));
        assertThrows(ResponseStatusException.class, () -> new MatchingScoreClient.TimeSlot(
                "2026-12-01T10:00:00Z", "2026-12-01T09:00:00Z"));
        var server = serve(503, "{}", false);
        try {
            var normalized = new MatchingScoreClient.Profile(null, List.of("\u0085Ｐｙｔｈｏｎ\u00a0"), null, null);
            var plain = new MatchingScoreClient.Profile(null, List.of("python"), null, null);
            assertEquals(100, client(server, 1000).scoreSingle(normalized,
                    MatchingScoreClient.Candidate.from("a", plain)).items().get(0).score());
        } finally { server.stop(0); }
    }

    @Test void timestampOffsetAndUtcRangeMatchPythonWithoutOverflow() {
        for (String start : List.of("2026-12-01T10:00:00+01:60", "2026-12-01T10:00:00+19:00",
                "2026-12-01T10:00:00+18:01", "0001-01-01T00:00:00+18:00",
                "0000-01-01T00:00:00Z")) {
            assertThrows(ResponseStatusException.class, () -> new MatchingScoreClient.TimeSlot(
                    start, "2026-12-02T10:00:00Z"));
        }
        assertDoesNotThrow(() -> new MatchingScoreClient.TimeSlot(
                "2026-12-01T09:00:00+18:00", "2026-12-02T09:00:00Z"));
    }

    @Test void missingTagsAndTiesHaveStableZeroScoresAndTimeoutConfigIsBounded() throws Exception {
        var server = serve(503, "{}", false);
        try {
            var empty = new MatchingScoreClient.Profile(null, null, null, null);
            var result = client(server, 1000).scoreBatch(empty, List.of(
                    MatchingScoreClient.Candidate.from("b", empty),
                    MatchingScoreClient.Candidate.from("a", empty)));
            assertEquals(List.of("a", "b"), result.items().stream().map(MatchingScoreClient.Score::id).toList());
            assertEquals(0, result.items().get(0).score());
            assertThrows(IllegalArgumentException.class,
                    () -> new MatchingScoreClient(RestClient.builder(), "http://localhost", 0, 500));
            assertEquals("ScoreProfile[redacted]", query.toString());
            assertEquals("ScoreCandidate[redacted]", candidate.toString());
        } finally { server.stop(0); }
    }
}
