package com.ouctongpin.apiserver.moderation;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Autowired;
import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;
import java.util.ArrayList;

/** Call before persisting user content. Dependency failures must never silently allow a write. */
@Service
public class ModerationClient {
    private final RestClient client;

    public enum Level { LOW, MEDIUM, HIGH }
    public record Hit(String word, Level level) {}
    public record Result(Boolean passed, String normalized, List<Hit> hits) {}

    @Autowired
    public ModerationClient(RestClient.Builder builder,
            @Value("${moderation.base-url:http://localhost:8000}") String baseUrl) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(2000);
        factory.setReadTimeout(3000);
        this.client = builder.baseUrl(baseUrl).requestFactory(factory).build();
    }

    ModerationClient(RestClient client) { this.client = client; }

    /** Returns allowed content decisions; throws 422 for blocking and 503 for unavailable checks. */
    public Result requireAllowed(String text) {
        if (text == null || text.isBlank() || text.codePointCount(0, text.length()) > 2000) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid content");
        }
        Result result;
        try {
            JsonNode body = client.post().uri("/api/moderation/check")
                    .body(Map.of("text", text)).retrieve().body(JsonNode.class);
            result = parse(body);
        } catch (RestClientException e) {
            // Do not propagate response bodies, input text, URLs or credentials into errors/logs.
            throw unavailable();
        }
        if (result == null || result.passed() == null || result.normalized() == null
                || result.hits() == null || result.hits().stream().anyMatch(hit ->
                hit == null || hit.word() == null || hit.word().isBlank() || hit.level() == null)) {
            throw unavailable();
        }
        boolean high = result.hits().stream().anyMatch(hit -> hit.level() == Level.HIGH);
        if (result.passed() == high) throw unavailable();
        if (!result.passed()) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "Content blocked");
        }
        return result;
    }

    private static Result parse(JsonNode body) {
        if (body == null || !body.isObject() || !body.path("passed").isBoolean()
                || !body.path("normalized").isTextual() || !body.path("hits").isArray()) {
            throw unavailable();
        }
        List<Hit> hits = new ArrayList<>();
        for (JsonNode hit : body.get("hits")) {
            if (!hit.path("word").isTextual() || hit.path("word").asText().isBlank()
                    || !hit.path("level").isTextual()) throw unavailable();
            try {
                hits.add(new Hit(hit.get("word").asText(), Level.valueOf(hit.get("level").asText())));
            } catch (IllegalArgumentException e) {
                throw unavailable();
            }
        }
        return new Result(body.get("passed").booleanValue(), body.get("normalized").asText(), hits);
    }

    private static ResponseStatusException unavailable() {
        return new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                "Content check unavailable; retry later");
    }
}
