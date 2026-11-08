package com.ouctongpin.apiserver.moderation;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

import java.net.SocketTimeoutException;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;

class ModerationClientTest {
    private ModerationClient client;
    private MockRestServiceServer server;

    @BeforeEach void setup() {
        RestClient.Builder builder = RestClient.builder();
        server = MockRestServiceServer.bindTo(builder).build();
        client = new ModerationClient(builder.baseUrl("http://algo:8000").build());
    }

    private void reply(String json) {
        server.expect(requestTo("http://algo:8000/api/moderation/check"))
                .andExpect(method(HttpMethod.POST)).andExpect(content().json("{\"text\":\"test\"}"))
                .andRespond(withSuccess(json, MediaType.APPLICATION_JSON));
    }

    @ParameterizedTest
    @ValueSource(strings = {"[]", "[{\"word\":\"提示词\",\"level\":\"LOW\"}]",
            "[{\"word\":\"提示词\",\"level\":\"MEDIUM\"}]"})
    void allowsNonBlockingDecisions(String hits) {
        reply("{\"passed\":true,\"normalized\":\"test\",\"hits\":" + hits + "}");
        assertTrue(client.requireAllowed("test").passed());
        server.verify();
    }

    @Test void blocksHighRisk() {
        reply("{\"passed\":false,\"normalized\":\"test\",\"hits\":[{\"word\":\"词\",\"level\":\"HIGH\"}]}");
        assertEquals(422, assertThrows(ResponseStatusException.class,
                () -> client.requireAllowed("test")).getStatusCode().value());
        server.verify();
    }

    @ParameterizedTest
    @ValueSource(strings = {"", "{", "{}", "null", "{\"passed\":true}",
            "{\"passed\":false,\"normalized\":\"test\",\"hits\":[]}",
            "{\"passed\":true,\"normalized\":\"test\",\"hits\":[null]}",
            "{\"passed\":true,\"normalized\":\"test\",\"hits\":[{\"word\":\"词\"}]}",
            "{\"passed\":true,\"normalized\":\"test\",\"hits\":[{\"word\":\"词\",\"level\":\"HIGH\"}]}",
            "{\"passed\":true,\"normalized\":\"test\",\"hits\":[{\"word\":\"词\",\"level\":\"OTHER\"}]}",
            "{\"passed\":\"true\",\"normalized\":\"test\",\"hits\":[]}"})
    void rejectsIncompleteOrInconsistentResponses(String body) {
        reply(body);
        assertEquals(503, assertThrows(ResponseStatusException.class,
                () -> client.requireAllowed("test")).getStatusCode().value());
        server.verify();
    }

    @Test void timeoutFailsClosed() {
        server.expect(anything()).andRespond(withException(new SocketTimeoutException("secret text")));
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> client.requireAllowed("test"));
        assertEquals(503, error.getStatusCode().value());
        assertFalse(error.toString().contains("secret text"));
        assertNull(error.getCause());
        server.verify();
    }

    @ParameterizedTest
    @ValueSource(ints = {400, 401, 422, 500, 503})
    void dependencyErrorsFailClosed(int status) {
        server.expect(anything()).andRespond(withStatus(HttpStatus.valueOf(status)).body("secret text"));
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> client.requireAllowed("test"));
        assertEquals(503, error.getStatusCode().value());
        assertFalse(error.toString().contains("secret text"));
        server.verify();
    }

    @Test void invalidInputNeverCallsService() {
        for (String input : new String[]{null, " ", "a".repeat(2001)}) {
            assertEquals(400, assertThrows(ResponseStatusException.class,
                    () -> client.requireAllowed(input)).getStatusCode().value());
        }
        server.verify();
    }
}
