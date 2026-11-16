package com.ouctongpin.apiserver.auth.config;

import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import java.security.Key;
import java.nio.charset.StandardCharsets;
import java.util.Date;

@Component
public class JwtUtil {
    private static final String ISSUER = "ouc-tongpin";
    private static final String AUDIENCE = "ouc-miniprogram";
    private final Key key;
    private final long lifetimeMillis;

    public JwtUtil(@Value("${jwt.secret}") String secret,
                   @Value("${jwt.expire-minutes:120}") long minutes) {
        if (secret.isBlank() || secret.getBytes(StandardCharsets.UTF_8).length < 32
                || secret.startsWith("change-me")
                || secret.equals("ouctongpin-secret-key-1234567890abcdefghijklmn")
                || minutes < 1 || minutes > 1440) {
            throw new IllegalStateException("A private JWT key and bounded expiry are required");
        }
        key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        lifetimeMillis = Math.multiplyExact(minutes, 60_000);
    }

    public String generateToken(Long userId) {
        if (userId == null || userId <= 0) throw new IllegalArgumentException("Invalid user");
        Date now = new Date();
        return Jwts.builder().setSubject(userId.toString()).setIssuer(ISSUER).setAudience(AUDIENCE)
                .setIssuedAt(now).setExpiration(new Date(now.getTime() + lifetimeMillis))
                .signWith(key, SignatureAlgorithm.HS256).compact();
    }

    public long verify(String token) {
        if (token == null || token.length() > 4096) throw new IllegalArgumentException("Invalid token");
        Jws<Claims> parsed = Jwts.parserBuilder().setSigningKey(key)
                .requireIssuer(ISSUER).requireAudience(AUDIENCE)
                .setCompressionCodecResolver(header -> {
                    if (header.getCompressionAlgorithm() != null) {
                        throw new UnsupportedJwtException("Compressed tokens are unsupported");
                    }
                    return null;
                }).build().parseClaimsJws(token);
        Claims claims = parsed.getBody();
        String subject = claims.getSubject();
        if (!"HS256".equals(parsed.getHeader().getAlgorithm())
                || claims.getExpiration() == null || claims.getIssuedAt() == null
                || claims.getIssuedAt().getTime() > System.currentTimeMillis() + 30_000
                || subject == null || !subject.matches("[1-9][0-9]{0,18}")) {
            throw new IllegalArgumentException("Invalid token claims");
        }
        return Long.parseLong(subject);
    }
}
