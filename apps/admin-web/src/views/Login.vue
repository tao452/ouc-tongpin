<template>
  <div class="login-page">
    <el-card class="login-card" shadow="always">
      <div class="login-title">OUC同频 · 管理端登录</div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="账号" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入管理员账号"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-tip">测试账号：admin / 密码任意输入 + 请使用Mock测试</div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const form = ref({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度需在 6-20 个字符', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true

  // 模拟后端接口请求（500ms 后登录成功）
  setTimeout(() => {
    loading.value = false
    ElMessage.success('登录成功！')
    console.log('Mock 登录成功，表单数据：', form.value)
    // 登录成功后跳转到看板页面
    router.push('/dashboard')
  }, 500)
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  border-radius: 12px;
  padding: 8px 12px;
}

.login-title {
  text-align: center;
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 24px;
}

.login-btn {
  width: 100%;
  letter-spacing: 8px;
}

.login-tip {
  text-align: center;
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 4px;
}
</style>
