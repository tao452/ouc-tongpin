<template>
  <div class="audit-page">
    <el-card shadow="never" class="audit-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">待审核内容</span>
          <div class="header-actions">
            <el-button type="success" :disabled="!selected.length" @click="handleBatch('approve')">
              批量通过
            </el-button>
            <el-button type="danger" :disabled="!selected.length" @click="handleBatch('reject')">
              批量驳回
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="tableData"
        border
        stripe
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="user" label="用户" width="140" />
        <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
        <el-table-column prop="time" label="时间" width="170" />
      </el-table>

      <el-pagination
        class="pagination"
        background
        layout="total, prev, pager, next"
        :total="tableData.length"
        :page-size="10"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// mock 数据
const tableData = ref([
  { id: 1001, user: '张三', content: '今天心情不太好，感觉压力很大，想找人聊聊。', time: '2026-11-01 09:12:33' },
  { id: 1002, user: '李四', content: '最近的课程作业太多了，有点焦虑，晚上睡不着觉。', time: '2026-11-01 09:45:10' },
  { id: 1003, user: '王五', content: '和室友闹矛盾了，心情很郁闷，不知道该怎么办。', time: '2026-11-01 10:03:51' },
  { id: 1004, user: '赵六', content: '考试没考好，觉得自己很失败，对未来很迷茫。', time: '2026-11-01 10:22:08' },
  { id: 1005, user: '孙七', content: '今天天气很好，出去走走感觉心情放松了不少！', time: '2026-11-01 11:05:44' },
  { id: 1006, user: '周八', content: '最近总是凌晨三四点才睡得着，白天没精神，很苦恼。', time: '2026-11-01 11:30:19' }
])

const selected = ref([])

// 勾选变化时记录选中的行
const handleSelectionChange = (rows) => {
  selected.value = rows
}

// 批量处理（mock）
const handleBatch = (type) => {
  const ids = selected.value.map((item) => item.id)

  // 驳回前弹确认框，防止误操作
  if (type === 'reject') {
    ElMessageBox.confirm(
      `确定要驳回选中的 ${ids.length} 条内容吗？`,
      '批量驳回',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    ).then(() => {
      ElMessage.warning(`已驳回 ${ids.length} 条内容（ID: ${ids.join('、')}）`)
      removeRows(ids)
    }).catch(() => {})
  } else {
    ElMessage.success(`已通过 ${ids.length} 条内容（ID: ${ids.join('、')}）`)
    removeRows(ids)
  }
}

// mock：从列表移除已处理的行
const removeRows = (ids) => {
  tableData.value = tableData.value.filter((item) => !ids.includes(item.id))
}
</script>

<style scoped>
.audit-page {
  padding: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>