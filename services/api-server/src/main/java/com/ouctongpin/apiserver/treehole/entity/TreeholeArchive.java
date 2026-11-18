package com.ouctongpin.apiserver.treehole.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("treehole_archive")
public class TreeholeArchive {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long postId;
    private String contentHash;
    private LocalDateTime createdAt;
}
