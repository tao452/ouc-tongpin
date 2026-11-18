<template>
  <div class="login-page">
    <el-card class="login-card" shadow="always">
<<<<<<< HEAD
      <div class="login-title">OUCåŒé¢‘ Â· ç®¡ç†ç«¯ç™»å½•</div>
=======
<<<<<<< HEAD
      <div class="login-title">ºóÌ¨¹ÜÀíÏµÍ³</div>
=======
      <div class="login-title">åå°ç®¡ç†ç³»ç»Ÿ</div>
>>>>>>> 7c67518fc91583a3983ea265b85f6d2a54d12eab
>>>>>>> develop

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent="handleLogin"
      >
<<<<<<< HEAD
        <el-form-item label="è´¦å·" prop="username">
          <el-input
            v-model="form.username"
            placeholder="è¯·è¾“å…¥ç®¡ç†å‘˜è´¦å·"
=======
<<<<<<< HEAD
        <el-form-item label="ÕËºÅ" prop="username">
          <el-input
            v-model="form.username"
            placeholder="ÇëÊäÈëÕËºÅ"
=======
        <el-form-item label="è´¦å·" prop="username">
          <el-input
            v-model="form.username"
            placeholder="è¯·è¾“å…¥è´¦å·"
>>>>>>> 7c67518fc91583a3983ea265b85f6d2a54d12eab
>>>>>>> develop
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

<<<<<<< HEAD
        <el-form-item label="å¯†ç " prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="è¯·è¾“å…¥å¯†ç "
=======
<<<<<<< HEAD
        <el-form-item label="ÃÜÂë" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="ÇëÊäÈëÃÜÂë"
=======
        <el-form-item label="å¯†ç " prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="è¯·è¾“å…¥å¯†ç "
>>>>>>> 7c67518fc91583a3983ea265b85f6d2a54d12eab
>>>>>>> develop
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
<<<<<<< HEAD
            ç™» å½•
=======
<<<<<<< HEAD
            µÇ Â¼
=======
            ç™» å½•
>>>>>>> 7c67518fc91583a3983ea265b85f6d2a54d12eab
>>>>>>> develop
          </el-button>
        </el-form-item>
      </el-form>

<<<<<<< HEAD
      <div class="login-tip">æµ‹è¯•è´¦å·ï¼šadmin / å¯†ç ä»»æ„è¾“å…¥ + è¯·ä½¿ç”¨Mockæµ‹è¯•</div>
=======
<<<<<<< HEAD
      <div class="login-tip">ÌáÊ¾£ºÈÎÒâÕËºÅ + ÈÎÒâÃÜÂë¼´¿ÉµÇÂ¼£¨mock£©</div>
=======
      <div class="login-tip">æç¤ºï¼šä»»æ„è´¦å· + ä»»æ„å¯†ç å³å¯ç™»å½•ï¼ˆmockï¼‰</div>
>>>>>>> 7c67518fc91583a3983ea265b85f6d2a54d12eab
>>>>>>> develop
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
<<<<<<< HEAD
  username: [{ required: true, message: 'è¯·è¾“å…¥è´¦å·', trigger: 'blur' }],
  password: [
    { required: true, message: 'è¯·è¾“å…¥å¯†ç ', trigger: 'blur' },
    { min: 6, max: 20, message: 'å¯†ç é•¿åº¦éœ€åœ¨ 6-20 ä¸ªå­—ç¬¦', trigger: 'blur' }
=======
<<<<<<< HEAD
  username: [{ required: true, message: 'ÇëÊäÈëÕËºÅ', trigger: 'blur' }],
  password: [
    { required: true, message: 'ÇëÊäÈëÃÜÂë', trigger: 'blur' },
    { min: 6, max: 20, message: 'ÃÜÂë³¤¶ÈĞèÎª 6-20 Î»', trigger: 'blur' }
=======
  username: [{ required: true, message: 'è¯·è¾“å…¥è´¦å·', trigger: 'blur' }],
  password: [
    { required: true, message: 'è¯·è¾“å…¥å¯†ç ', trigger: 'blur' },
    { min: 6, max: 20, message: 'å¯†ç é•¿åº¦éœ€ä¸º 6-20 ä½', trigger: 'blur' }
>>>>>>> 7c67518fc91583a3983ea265b85f6d2a54d12eab
>>>>>>> develop
  ]
}

const handleLogin = async () => {
<<<<<<< HEAD
=======
<<<<<<< HEAD
  // ±íµ¥Ğ£Ñé
=======
  // è¡¨å•æ ¡éªŒ
>>>>>>> 7c67518fc91583a3983ea265b85f6d2a54d12eab
>>>>>>> develop
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true

<<<<<<< HEAD
  // æ¨¡æ‹Ÿåç«¯æ¥å£è¯·æ±‚ï¼ˆ500ms åç™»å½•æˆåŠŸï¼‰
  setTimeout(() => {
    loading.value = false
    ElMessage.success('ç™»å½•æˆåŠŸï¼')
    console.log('Mock ç™»å½•æˆåŠŸï¼Œè¡¨å•æ•°æ®ï¼š', form.value)
    // ç™»å½•æˆåŠŸåè·³è½¬åˆ°çœ‹æ¿é¡µé¢
    router.push('/dashboard')
=======
<<<<<<< HEAD
  // mock µÇÂ¼£ºÄ£Äâ 500ms ÍøÂçÇëÇó
  setTimeout(() => {
    loading.value = false
    ElMessage.success('µÇÂ¼³É¹¦')
    console.log('mock µÇÂ¼ĞÅÏ¢£º', form.value)
    // ºóĞø¿ÉÔÚÕâÀïĞ´£ºrouter.push('/dashboard')
=======
  // mock ç™»å½•ï¼šæ¨¡æ‹Ÿ 500ms ç½‘ç»œè¯·æ±‚
  setTimeout(() => {
    loading.value = false
    ElMessage.success('ç™»å½•æˆåŠŸ')
    // åç»­å¯åœ¨è¿™é‡Œå†™ï¼šrouter.push('/dashboard')
>>>>>>> 7c67518fc91583a3983ea265b85f6d2a54d12eab
>>>>>>> develop
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
<<<<<<< HEAD
</style>
=======
<<<<<<< HEAD
</style>
=======
</style>
>>>>>>> 7c67518fc91583a3983ea265b85f6d2a54d12eab
>>>>>>> develop
