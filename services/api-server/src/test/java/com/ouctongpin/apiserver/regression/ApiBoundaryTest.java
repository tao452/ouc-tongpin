package com.ouctongpin.apiserver.regression;

import com.ouctongpin.apiserver.checkin.controller.CheckinController;
import com.ouctongpin.apiserver.checkin.service.CheckinService;
import com.ouctongpin.apiserver.common.GlobalExceptionHandler;
import com.ouctongpin.apiserver.treehole.controller.TreeholeController;
import com.ouctongpin.apiserver.treehole.service.TreeholeService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.http.MediaType;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.hamcrest.Matchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class ApiBoundaryTest {
    private CheckinService checkins;
    private TreeholeService posts;
    private MockMvc mvc;

    @BeforeEach void setup() {
        checkins = mock(CheckinService.class);
        posts = mock(TreeholeService.class);
        CheckinController checkinController = new CheckinController();
        TreeholeController treeholeController = new TreeholeController();
        ReflectionTestUtils.setField(checkinController, "checkinService", checkins);
        ReflectionTestUtils.setField(treeholeController, "treeholeService", posts);
        mvc = MockMvcBuilders.standaloneSetup(checkinController, treeholeController)
                .setControllerAdvice(new GlobalExceptionHandler()).build();
    }

    @ParameterizedTest
    @ValueSource(strings = {
        "{\"emotion\":\"UNKNOWN\",\"intensity\":3}",
        "{\"emotion\":\"\",\"intensity\":3}",
        "{\"emotion\":\"HAPPY\",\"intensity\":0}",
        "{\"emotion\":\"HAPPY\",\"intensity\":6}",
        "{\"emotion\":\"HAPPY\"}",
        "{\"intensity\":3}",
        "{\"emotion\":\"HAPPY\",\"intensity\":3,\"checkinDate\":\"PRIVATE-INVALID-DATE\"}",
        "{"
    })
    void invalidCheckinNeverReachesPersistence(String body) throws Exception {
        mvc.perform(post("/api/emotions/checkins").contentType(MediaType.APPLICATION_JSON)
                .content(body)).andExpect(status().isBadRequest())
                .andExpect(content().string(not(containsString("PRIVATE-INVALID-DATE"))));
        verifyNoInteractions(checkins);
    }

    @ParameterizedTest
    @ValueSource(ints = {100, 101})
    void noteBoundaryIsEnforced(int length) throws Exception {
        var result = mvc.perform(post("/api/emotions/checkins").contentType(MediaType.APPLICATION_JSON)
                .content("{\"emotion\":\"CALM\",\"intensity\":3,\"note\":\""
                        + "x".repeat(length) + "\"}"));
        if (length == 100) {
            result.andExpect(status().isOk());
            verify(checkins).doCheckin(1L, "CALM", 3, "x".repeat(length), null);
        } else {
            result.andExpect(status().isBadRequest());
            verifyNoInteractions(checkins);
        }
    }

    @ParameterizedTest
    @ValueSource(strings = {"UNKNOWN", "", "private-value"})
    void invalidTreeholeTagNeverReachesModerationOrPersistence(String tag) throws Exception {
        mvc.perform(post("/api/treehole/posts").contentType(MediaType.APPLICATION_JSON)
                .content("{\"content\":\"synthetic\",\"emotionTag\":\"" + tag + "\"}"))
                .andExpect(status().isBadRequest());
        verifyNoInteractions(posts);
    }
}
