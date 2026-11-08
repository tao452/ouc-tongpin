package com.ouctongpin.apiserver.moderation;

import com.ouctongpin.apiserver.common.GlobalExceptionHandler;
import com.ouctongpin.apiserver.treehole.controller.TreeholeController;
import com.ouctongpin.apiserver.treehole.service.TreeholeService;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.server.ResponseStatusException;

import static org.hamcrest.Matchers.not;
import static org.hamcrest.Matchers.containsString;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class TreeholeModerationHttpTest {
    @ParameterizedTest
    @ValueSource(ints = {0, 501})
    void blankAndOversizedPostsReturn400WithoutCallingBusinessService(int length) throws Exception {
        TreeholeService service = mock(TreeholeService.class);
        TreeholeController controller = new TreeholeController();
        ReflectionTestUtils.setField(controller, "treeholeService", service);
        var mvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new GlobalExceptionHandler()).build();
        String text = length == 0 ? " " : "x".repeat(length);
        mvc.perform(post("/api/treehole/posts").contentType(MediaType.APPLICATION_JSON)
                .content("{\"content\":\"" + text + "\",\"emotionTag\":\"CALM\"}"))
                .andExpect(status().isBadRequest());
        verifyNoInteractions(service);
    }

    @ParameterizedTest
    @ValueSource(ints = {422, 503})
    void advicePreservesStatusWithoutEchoingContentOrDependencyDetails(int status) throws Exception {
        TreeholeService service = mock(TreeholeService.class);
        when(service.createPost(anyLong(), any())).thenThrow(new ResponseStatusException(
                HttpStatus.valueOf(status), "PRIVATE-UPSTREAM-DETAILS"));
        TreeholeController controller = new TreeholeController();
        ReflectionTestUtils.setField(controller, "treeholeService", service);
        var mvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new GlobalExceptionHandler()).build();
        mvc.perform(post("/api/treehole/posts").contentType(MediaType.APPLICATION_JSON)
                .content("{\"content\":\"PRIVATE-CONTENT\",\"emotionTag\":\"CALM\"}"))
                .andExpect(status().is(status))
                .andExpect(jsonPath("$.code").value(status))
                .andExpect(content().string(not(containsString("PRIVATE-CONTENT"))))
                .andExpect(content().string(not(containsString("PRIVATE-UPSTREAM-DETAILS"))));
    }
}
