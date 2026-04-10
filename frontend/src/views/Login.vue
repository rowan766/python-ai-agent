<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-title">
        <h2>后台管理系统</h2>
        <p>欢迎登录</p>
      </div>
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="rules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        <el-form-item prop="captchaCode">
          <div class="captcha-row">
            <el-input
              v-model="loginForm.captchaCode"
              placeholder="请输入验证码"
              size="large"
              class="captcha-input"
            />
            <button
              type="button"
              class="captcha-image-button"
              :disabled="captchaLoading"
              @click="fetchCaptcha"
            >
              <img
                v-if="captchaImage"
                :src="captchaImage"
                alt="验证码"
                class="captcha-image"
              />
              <span v-else class="captcha-placeholder">
                {{ captchaLoading ? '加载中...' : '获取验证码' }}
              </span>
            </button>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-button"
            native-type="submit"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import { getCaptcha } from '../api/auth'

const router = useRouter()
const userStore = useUserStore()

const loginFormRef = ref(null)
const loading = ref(false)
const captchaLoading = ref(false)
const captchaImage = ref('')

const loginForm = reactive({
  username: 'admin',
  password: '123456',
  captchaId: '',
  captchaCode: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于6位', trigger: 'blur' }
  ],
  captchaCode: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { min: 4, message: '验证码长度不能小于4位', trigger: 'blur' }
  ]
}

const fetchCaptcha = async () => {
  captchaLoading.value = true
  try {
    const res = await getCaptcha()
    loginForm.captchaId = res.data.captchaId
    loginForm.captchaCode = ''
    captchaImage.value = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(res.data.captchaSvg)}`
  } catch (error) {
    captchaImage.value = ''
  } finally {
    captchaLoading.value = false
  }
}

const handleLogin = async () => {
  if (!loginFormRef.value) return

  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await userStore.login(loginForm)
        ElMessage.success('登录成功')
        router.push('/')
      } catch (error) {
        ElMessage.error(error.message || '登录失败')
        fetchCaptcha()
      } finally {
        loading.value = false
      }
    }
  })
}

onMounted(() => {
  fetchCaptcha()
})
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  width: 420px;
  padding: 40px;
  background: white;
  border-radius: 10px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.login-title {
  text-align: center;
  margin-bottom: 40px;
}

.login-title h2 {
  margin: 0;
  font-size: 28px;
  color: #333;
}

.login-title p {
  margin: 10px 0 0 0;
  color: #666;
  font-size: 14px;
}

.login-form {
  margin-top: 20px;
}

.login-button {
  width: 100%;
}

.captcha-row {
  display: flex;
  gap: 12px;
  width: 100%;
}

.captcha-input {
  flex: 1;
}

.captcha-image-button {
  position: relative;
  width: 132px;
  height: 44px;
  padding: 4px;
  border: 1px solid #d9e6fb;
  border-radius: 8px;
  background:
    repeating-linear-gradient(120deg, rgba(255, 255, 255, 0.22) 0 6px, rgba(255, 255, 255, 0) 6px 14px),
    radial-gradient(circle at 22% 30%, rgba(255, 255, 255, 0.34) 0 8%, transparent 9%),
    radial-gradient(circle at 78% 68%, rgba(255, 255, 255, 0.26) 0 7%, transparent 8%),
    linear-gradient(135deg, #dff2ff 0%, #d9e8ff 26%, #efe2ff 52%, #ffe9d2 100%);
  cursor: pointer;
  overflow: hidden;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.captcha-image-button:hover:not(:disabled) {
  border-color: #b7cdf5;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.78),
    0 10px 22px rgba(102, 126, 234, 0.16);
  transform: translateY(-1px);
}

.captcha-image-button:disabled {
  cursor: wait;
  opacity: 0.7;
}

.captcha-image {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 6px;
  mix-blend-mode: multiply;
}

.captcha-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #606266;
  font-size: 13px;
}
</style>
