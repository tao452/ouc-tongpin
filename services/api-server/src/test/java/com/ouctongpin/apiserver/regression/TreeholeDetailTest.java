package com.ouctongpin.apiserver.regression;

import com.ouctongpin.apiserver.treehole.entity.TreeholePost;
import com.ouctongpin.apiserver.treehole.mapper.TreeholePostMapper;
import com.ouctongpin.apiserver.treehole.service.TreeholeService;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ResponseStatusException;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.any;
import static org.junit.jupiter.api.Assertions.*;

class TreeholeDetailTest {
    @Test
    void detailUsesPublicDtoAndHidesUnavailableContent() {
        var mapper = mock(TreeholePostMapper.class);
        var service = new TreeholeService();
        ReflectionTestUtils.setField(service, "postMapper", mapper);
        var post = new TreeholePost();
        post.setId(41L);
        post.setAnonymous(1);
        post.setAnonymousId("anon_v1_synthetic");
        post.setContent("合成树洞正文");
        when(mapper.selectOne(any())).thenReturn(post).thenReturn(null);
        assertEquals("合成树洞正文", service.getPost(41L).getContent());
        var error = assertThrows(ResponseStatusException.class, () -> service.getPost(41L));
        assertEquals(404, error.getStatusCode().value());
    }
}
