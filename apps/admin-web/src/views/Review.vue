<template>
  <div class="review-container">
    <h2>树洞内容审核台</h2>
    <el-table :data="tableData" border style="width: 100%; margin-top: 20px;">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="content" label="内容" />
      <el-table-column prop="time" label="发布时间" width="180" />
      <el-table-column label="操作" width="200">
        <template #default="scope">
          <el-button type="success" size="small" @click="handlePass(scope.row)">通过</el-button>
          <el-button type="danger" size="small" @click="handleReject(scope.row)">驳回</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const tableData = ref([
  { id: 1, content: '今天图书馆人好多，感觉大家都在卷...', time: '2026-11-16 10:00' },
  { id: 2, content: '有没有人一起去海边散散步呀？', time: '2026-11-16 11:30' },
  { id: 3, content: '期中考试考砸了，好难过，求安慰。', time: '2026-11-16 14:15' }
])

const handlePass = (row: any) => {
  ElMessage.success(`已通过 ID:${row.id} 的内容`)
}

const handleReject = (row: any) => {
  ElMessageBox.confirm('确定要驳回这条内容吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    ElMessage.success(`已驳回 ID:${row.id} 的内容`)
  }).catch(() => {
    ElMessage.info('已取消操作')
  })
}
</script>

<style scoped>
.review-container { padding: 20px; }
</style>
