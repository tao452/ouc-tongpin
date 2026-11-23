package com.ouctongpin.apiserver.matching;

import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

/** Opt-in actual Java-to-container HTTP integration, excluded from ordinary unit counts. */
class MatchingScoreDockerIT {
    @Test void actualFastApiSingleAndBatchRespectVersionAndMissingFeatures() {
        String base = System.getenv("MATCH_DOCKER_URL");
        assertNotNull(base, "Run explicitly against the owned Docker scoring service");
        assertTrue(base.matches("http://127\\.0\\.0\\.1:[0-9]+"));
        var client = new MatchingScoreClient(RestClient.builder(), base, 200, 500);
        var profile = new MatchingScoreClient.Profile(List.of(1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                List.of("Python"), List.of(new MatchingScoreClient.TimeSlot(
                "2026-12-01T10:00:00+08:00", "2026-12-01T12:00:00+08:00")),
                new MatchingScoreClient.Location(36, 120));
        var candidate = MatchingScoreClient.Candidate.from("synthetic-a", profile);
        var one = client.scoreSingle(profile, candidate);
        assertFalse(one.fallback());
        assertEquals(100, one.items().get(0).score());
        assertEquals("features-v0.1-proposed", one.featureVersion());
        assertTrue(one.configSha256().matches("[a-f0-9]{64}"));
        assertEquals(one, client.scoreBatch(profile, List.of(candidate)));
        var empty = new MatchingScoreClient.Profile(null, null, null, null);
        var zeros = client.scoreBatch(empty, List.of(
                MatchingScoreClient.Candidate.from("z", empty),
                MatchingScoreClient.Candidate.from("a", empty)));
        assertFalse(zeros.fallback());
        assertEquals(List.of("a", "z"), zeros.items().stream().map(MatchingScoreClient.Score::id).toList());
        assertTrue(zeros.items().stream().allMatch(score -> score.score() == 0));
    }
}
