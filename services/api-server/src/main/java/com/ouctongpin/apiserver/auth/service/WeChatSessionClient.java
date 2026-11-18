package com.ouctongpin.apiserver.auth.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;

@Component
public class WeChatSessionClient {
    private final String appId;
    private final String secret;
    private final boolean mockEnabled;
    private final ObjectMapper json;
    private final URI endpoint;

    @Autowired
    public WeChatSessionClient(@Value("${auth.wechat.app-id:}") String appId,
            @Value("${auth.wechat.secret:}") String secret,
            @Value("${auth.wechat.mock-enabled:false}") boolean mockEnabled, ObjectMapper json) {
        this(appId, secret, mockEnabled, json, URI.create("https://api.weixin.qq.com/sns/jscode2session"));
    }

    // Alternate transport endpoint is constructor-only, for an isolated provider contract test.
    public WeChatSessionClient(String appId, String secret, boolean mockEnabled,
                              ObjectMapper json, URI endpoint) {
        if (!mockEnabled && (appId.isBlank() || secret.isBlank())) {
            throw new IllegalStateException("Configure WeChat credentials; mock login is disabled by default");
        }
        this.appId = appId;
        this.secret = secret;
        this.mockEnabled = mockEnabled;
        this.json = json;
        this.endpoint = endpoint;
    }

    public String exchange(String code) {
        if (mockEnabled) {
            try {
                return "mock_" + HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                        .digest(code.getBytes(StandardCharsets.UTF_8)));
            } catch (java.security.NoSuchAlgorithmException impossible) {
                throw new IllegalStateException("SHA-256 unavailable");
            }
        }
        HttpURLConnection connection = null;
        try {
            String query = "?appid=" + encode(appId) + "&secret=" + encode(secret)
                    + "&js_code=" + encode(code) + "&grant_type=authorization_code";
            connection = (HttpURLConnection) URI.create(endpoint + query).toURL().openConnection();
            connection.setInstanceFollowRedirects(false);
            connection.setConnectTimeout(3000);
            connection.setReadTimeout(5000);
            if (connection.getResponseCode() != 200) throw unavailable();
            byte[] raw;
            try (var body = connection.getInputStream()) { raw = body.readNBytes(8193); }
            if (raw.length > 8192) throw unavailable();
            JsonNode response = json.readTree(raw);
            if (response == null || !response.isObject()) throw unavailable();
            if (response.has("errcode")) {
                if (!response.get("errcode").isIntegralNumber()) throw unavailable();
                int error = response.get("errcode").asInt();
                if (error == 40029 || error == 40163) {
                    throw new ResponseStatusException(HttpStatus.UNAUTHORIZED);
                }
                if (error != 0) throw unavailable();
            }
            JsonNode openid = response.get("openid");
            if (openid == null || !openid.isTextual()
                    || !openid.asText().matches("[A-Za-z0-9_-]{1,128}")) throw unavailable();
            // session_key/unionid and the original response are deliberately not retained.
            return openid.asText();
        } catch (java.io.IOException | IllegalArgumentException error) {
            throw unavailable();
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static String encode(String value) { return URLEncoder.encode(value, StandardCharsets.UTF_8); }
    private static ResponseStatusException unavailable() {
        return new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE);
    }
}
