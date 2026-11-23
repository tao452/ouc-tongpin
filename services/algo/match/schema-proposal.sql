-- US-12 feature snapshot proposal. M5/M1 review before adding any production migration.
-- No raw interests, emotion text, precise coordinates or login identifiers are stored here.
CREATE TABLE match_feature_snapshot_proposal (
    id BIGINT NOT NULL AUTO_INCREMENT,
    request_key VARCHAR(64) NOT NULL,
    candidate_key VARCHAR(64) NOT NULL,
    feature_version VARCHAR(64) NOT NULL,
    weights_version VARCHAR(64) NOT NULL,
    config_sha256 CHAR(64) NOT NULL,
    source_data_sha256 CHAR(64) NOT NULL,
    features JSON NOT NULL,
    score DECIMAL(9,6) NOT NULL,
    fallback BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uk_request_candidate_versions
        (request_key, candidate_key, feature_version, weights_version),
    CONSTRAINT ck_score_range CHECK (score >= 0 AND score <= 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- Private table only. Link to authorized internal accounts in M5's private data layer,
-- not through public-reader grants or externally supplied userId fields.
