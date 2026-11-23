package com.ouctongpin.apiserver.matching;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.server.ResponseStatusException;

import java.net.SocketTimeoutException;
import java.text.Normalizer;
import java.time.OffsetDateTime;
import java.util.*;

/** Internal US-12 adapter. Public matching authorization/routing stays with the business service. */
@Service
public class MatchingScoreClient {
    private static final String TIMESTAMP = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
            + "(?:\\.[0-9]{1,6})?(?:Z|[+-](?:(?:0[0-9]|1[0-7]):[0-5][0-9]|18:00))";
    public record Location(double lat, double lng) {}
    public record TimeSlot(String start, String end) {
        public TimeSlot {
            try {
                if (start == null || end == null || start.length() > 64 || end.length() > 64
                        || !start.matches(TIMESTAMP) || !end.matches(TIMESTAMP)
                        || !OffsetDateTime.parse(end).isAfter(OffsetDateTime.parse(start))) throw invalid();
                var first = OffsetDateTime.parse(start).withOffsetSameInstant(java.time.ZoneOffset.UTC);
                var last = OffsetDateTime.parse(end).withOffsetSameInstant(java.time.ZoneOffset.UTC);
                if (first.getYear() < 1 || first.getYear() > 9999
                        || last.getYear() < 1 || last.getYear() > 9999) throw invalid();
            } catch (java.time.format.DateTimeParseException error) { throw invalid(); }
        }
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Profile(@JsonProperty("emotion_vector") List<Double> emotionVector,
                          List<String> interests, List<TimeSlot> availability, Location location) {
        public Profile {
            validateProfile(emotionVector, interests, availability, location);
            interests = interests == null ? List.of() : List.copyOf(interests);
            availability = availability == null ? List.of() : List.copyOf(availability);
            emotionVector = emotionVector == null ? null : List.copyOf(emotionVector);
        }
        @Override public String toString() { return "ScoreProfile[redacted]"; }
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Candidate(String id, @JsonProperty("emotion_vector") List<Double> emotionVector,
                            List<String> interests, List<TimeSlot> availability, Location location) {
        public Candidate {
            Profile normalized = new Profile(emotionVector, interests, availability, location);
            emotionVector = normalized.emotionVector();
            interests = normalized.interests();
            availability = normalized.availability();
        }
        public static Candidate from(String id, Profile profile) {
            return new Candidate(id, profile.emotionVector(), profile.interests(),
                    profile.availability(), profile.location());
        }
        @Override public String toString() { return "ScoreCandidate[redacted]"; }
    }

    public record Score(String id, double score) {}
    public record Result(List<Score> items, String featureVersion, String weightsVersion,
                         String configSha256, boolean fallback, String reason) {}

    private final RestClient client;

    public MatchingScoreClient(RestClient.Builder builder,
            @Value("${matching.base-url:http://localhost:8000}") String baseUrl,
            @Value("${matching.connect-timeout-ms:200}") int connectMs,
            @Value("${matching.read-timeout-ms:500}") int readMs) {
        if (connectMs < 1 || connectMs > 5000 || readMs < 1 || readMs > 5000) {
            throw new IllegalArgumentException("Scoring timeout must be within 1..5000 ms");
        }
        var factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectMs);
        factory.setReadTimeout(readMs);
        client = builder.baseUrl(baseUrl).requestFactory(factory).build();
    }

    public Result scoreSingle(Profile query, Candidate candidate) {
        return request(query, candidate == null ? List.of() : List.of(candidate), true);
    }

    public Result scoreBatch(Profile query, List<Candidate> candidates) {
        return request(query, candidates, false);
    }

    private Result request(Profile query, List<Candidate> candidates, boolean single) {
        if (query == null || candidates == null || candidates.isEmpty() || candidates.size() > 100
                || candidates.stream().anyMatch(c -> c == null || c.id() == null
                || !c.id().matches("[A-Za-z0-9_-]{1,64}"))
                || candidates.stream().map(Candidate::id).distinct().count() != candidates.size()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid scoring input");
        }
        candidates = List.copyOf(candidates);
        try {
            Object body = single ? Map.of("query", query, "candidate", candidates.get(0))
                    : Map.of("query", query, "candidates", candidates);
            var response = client.post().uri("/score").body(body).retrieve().toEntity(JsonNode.class);
            JsonNode root = response.getBody();
            if (root == null || !root.path("items").isArray()
                    || root.path("items").size() != candidates.size()
                    || !root.path("fallback").isBoolean() || root.path("fallback").asBoolean()
                    || !version(root.path("feature_version")) || !version(root.path("weights_version"))
                    || !root.path("config_sha256").isTextual()
                    || !root.get("config_sha256").asText().matches("[a-f0-9]{64}")
                    || !root.get("config_sha256").asText().equals(
                            response.getHeaders().getFirst("X-Score-Config-SHA256"))) {
                return fallback(query, candidates, "INVALID_RESPONSE");
            }
            Set<String> expected = new HashSet<>(candidates.stream().map(Candidate::id).toList());
            List<Score> scores = new ArrayList<>();
            for (JsonNode row : root.get("items")) {
                if (!row.path("id").isTextual() || !expected.remove(row.get("id").asText())
                        || !row.path("score").isNumber() || !Double.isFinite(row.get("score").asDouble())
                        || row.get("score").asDouble() < 0 || row.get("score").asDouble() > 100) {
                    return fallback(query, candidates, "INVALID_RESPONSE");
                }
                scores.add(new Score(row.get("id").asText(), row.get("score").asDouble()));
            }
            scores.sort(Comparator.comparingDouble(Score::score).reversed().thenComparing(Score::id));
            return new Result(List.copyOf(scores), root.get("feature_version").asText(),
                    root.get("weights_version").asText(), root.get("config_sha256").asText(), false, null);
        } catch (HttpClientErrorException invalid) {
            // Parameter/auth errors are not service outages; never turn them into a successful fallback.
            throw new ResponseStatusException(invalid.getStatusCode(), "Scoring request rejected");
        } catch (RestClientException unavailable) {
            Throwable cause = unavailable;
            for (int depth = 0; cause != null && depth < 16; depth++, cause = cause.getCause()) {
                if (cause instanceof SocketTimeoutException) return fallback(query, candidates, "TIMEOUT");
            }
            return fallback(query, candidates, "SERVICE_UNAVAILABLE");
        }
    }

    private static boolean version(JsonNode value) {
        return value.isTextual() && !value.asText().isBlank() && value.asText().length() <= 64;
    }

    private static Set<String> tags(List<String> input) {
        Set<String> result = new HashSet<>();
        for (String tag : input == null ? List.<String>of() : input) {
            if (tag == null) continue;
            String normalized = Normalizer.normalize(tag, Normalizer.Form.NFKC);
            int start = 0, end = normalized.length();
            while (start < end && space(normalized.codePointAt(start)))
                start += Character.charCount(normalized.codePointAt(start));
            while (end > start && space(normalized.codePointBefore(end)))
                end -= Character.charCount(normalized.codePointBefore(end));
            normalized = normalized.substring(start, end).toLowerCase(Locale.ROOT);
            if (!normalized.isEmpty()) result.add(normalized);
        }
        return result;
    }

    private static boolean space(int codePoint) {
        return Character.isWhitespace(codePoint) || Character.isSpaceChar(codePoint) || codePoint == 0x85;
    }

    private static ResponseStatusException invalid() {
        return new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid scoring input");
    }

    private static void validateProfile(List<Double> emotion, List<String> interests,
                                        List<TimeSlot> availability, Location location) {
        if (emotion != null && (emotion.size() != 6 || emotion.stream().anyMatch(v ->
                v == null || !Double.isFinite(v) || v < 0 || v > 1))) throw invalid();
        if (interests != null && (interests.size() > 32 || interests.stream().anyMatch(v ->
                v == null || v.isEmpty() || v.codePointCount(0, v.length()) > 32))) throw invalid();
        if (availability != null && (availability.size() > 16
                || availability.stream().anyMatch(Objects::isNull))) throw invalid();
        if (location != null && (!Double.isFinite(location.lat()) || !Double.isFinite(location.lng())
                || location.lat() < -90 || location.lat() > 90
                || location.lng() < -180 || location.lng() > 180)) throw invalid();
    }

    private static Result fallback(Profile query, List<Candidate> candidates, String reason) {
        List<Score> scores = new ArrayList<>();
        Set<String> left = tags(query.interests());
        for (Candidate candidate : candidates) {
            Set<String> right = tags(candidate.interests()), union = new HashSet<>(left);
            union.addAll(right);
            right.retainAll(left);
            double score = union.isEmpty() ? 0 : 100.0 * right.size() / union.size();
            scores.add(new Score(candidate.id(), Math.round(score * 1_000_000) / 1_000_000.0));
        }
        scores.sort(Comparator.comparingDouble(Score::score).reversed().thenComparing(Score::id));
        return new Result(List.copyOf(scores), "tag-baseline-v1", "tag-only-v1", null, true, reason);
    }
}
