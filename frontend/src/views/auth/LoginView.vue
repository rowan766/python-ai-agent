<script setup lang="ts">
import axios from 'axios'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as authApi from '@/api/modules/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const resetFormRef = ref<FormInstance>()

const form = reactive({
  account: '',
  password: '',
  captcha_code: '',
  captcha_token: '',
})

const captchaImage = ref('')
const loadingCaptcha = ref(false)

const resetDialogVisible = ref(false)
const sendingResetCode = ref(false)
const submittingReset = ref(false)
const resendCountdown = ref(0)

const resetForm = reactive({
  email: '',
  code: '',
  newPassword: '',
  confirmPassword: '',
})

let countdownTimer: number | null = null

const loginRules: FormRules = {
  account: [{ required: true, message: '请输入账号或邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  captcha_code: [
    { required: true, message: '请输入图形验证码', trigger: 'blur' },
    { min: 5, max: 5, message: '请输入 5 位字母验证码', trigger: 'blur' },
  ],
}

const resetRules: FormRules = {
  email: [{ required: true, message: '请输入注册邮箱', trigger: 'blur' }],
  code: [
    { required: true, message: '请输入邮箱验证码', trigger: 'blur' },
    { min: 6, max: 6, message: '验证码应为 6 位', trigger: 'blur' },
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码至少 6 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback: (error?: Error) => void) => {
        if (value !== resetForm.newPassword) {
          callback(new Error('两次输入的密码不一致'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
}

const canSendResetCode = computed(() => resendCountdown.value === 0 && !sendingResetCode.value)

function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
  }
  return fallback
}

function clearCountdown() {
  if (countdownTimer !== null) {
    window.clearInterval(countdownTimer)
    countdownTimer = null
  }
}

function startCountdown(seconds = 60) {
  clearCountdown()
  resendCountdown.value = seconds
  countdownTimer = window.setInterval(() => {
    if (resendCountdown.value <= 1) {
      clearCountdown()
      resendCountdown.value = 0
      return
    }
    resendCountdown.value -= 1
  }, 1000)
}

function resetResetForm() {
  resetForm.code = ''
  resetForm.newPassword = ''
  resetForm.confirmPassword = ''
}

function openResetDialog() {
  if (form.account.includes('@') && !resetForm.email) {
    resetForm.email = form.account.trim()
  }
  resetDialogVisible.value = true
}

async function loadCaptcha() {
  loadingCaptcha.value = true
  try {
    const result = await authApi.fetchLoginCaptcha()
    form.captcha_token = result.captcha_token
    form.captcha_code = ''
    captchaImage.value = result.image_data
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '登录验证码加载失败，请刷新页面重试。'))
    console.error(error)
  } finally {
    loadingCaptcha.value = false
  }
}

async function handleSubmit() {
  if (!formRef.value) {
    return
  }

  await formRef.value.validate()

  try {
    await authStore.login(form)
    ElMessage.success('登录成功，欢迎回来。')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/workspace'
    await router.push(redirect)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '登录失败，请检查账号和密码。'))
    await loadCaptcha()
    console.error(error)
  }
}

async function handleSendResetCode() {
  await resetFormRef.value?.validateField('email')
  sendingResetCode.value = true

  try {
    const result = await authApi.requestPasswordResetCode({ email: resetForm.email.trim() })
    ElMessage.success(result.message)
    if (result.debug_code) {
      ElMessage.warning(`开发环境验证码：${result.debug_code}`)
    }
    startCountdown()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '验证码发送失败，请稍后重试。'))
    console.error(error)
  } finally {
    sendingResetCode.value = false
  }
}

async function handleResetPassword() {
  if (!resetFormRef.value) {
    return
  }

  await resetFormRef.value.validate()
  submittingReset.value = true

  try {
    const result = await authApi.resetPassword({
      email: resetForm.email.trim(),
      code: resetForm.code.trim(),
      new_password: resetForm.newPassword,
    })
    ElMessage.success(result.message)
    form.account = resetForm.email.trim()
    form.password = ''
    resetDialogVisible.value = false
    resetResetForm()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '密码重置失败，请确认邮箱和验证码。'))
    console.error(error)
  } finally {
    submittingReset.value = false
  }
}

onBeforeUnmount(() => {
  clearCountdown()
})

onMounted(() => {
  void loadCaptcha()
})
</script>

<template>
  <section class="auth-page">
    <div class="auth-page__panel auth-page__panel--hero">
      <p class="auth-page__eyebrow">Enterprise Knowledge Platform</p>
      <h1>让企业知识真正可管、可搜、可追溯。</h1>
      <p class="auth-page__lead">
        现在已经支持账号或邮箱登录、JWT 会话校验，以及通过邮箱验证码找回密码，认证链路可以直接跑通前后端联调。
      </p>

      <div class="auth-page__highlights">
        <article>
          <strong>账户密码登录</strong>
          <span>支持用户名或邮箱登录，便于企业内部统一入口接入。</span>
        </article>
        <article>
          <strong>邮箱验证码重置</strong>
          <span>忘记密码时可直接发送 6 位验证码到邮箱完成重置。</span>
        </article>
        <article>
          <strong>JWT 会话校验</strong>
          <span>路由守卫和后端接口都会验证令牌有效性，过期后自动回到登录页。</span>
        </article>
      </div>
    </div>

    <div class="auth-page__panel auth-page__panel--form">
      <div class="auth-card">
        <div class="auth-card__header">
          <h2>登录平台</h2>
          <p>输入账号或邮箱与密码即可进入工作台，密码丢失时可直接在这里找回。</p>
        </div>

        <el-form ref="formRef" :model="form" :rules="loginRules" label-position="top">
          <el-form-item label="账号 / 邮箱" prop="account">
            <el-input
              v-model="form.account"
              placeholder="请输入用户名或登录邮箱"
              @keyup.enter="handleSubmit"
              size="large"/>
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              show-password
              placeholder="请输入密码"
              @keyup.enter="handleSubmit"
              size="large"
            />
          </el-form-item>

          <el-form-item label="图形验证码" prop="captcha_code">
            <div class="auth-card__captcha-row">
              <el-input
                class="auth-card__captcha-input"
                v-model="form.captcha_code"
                maxlength="5"
                placeholder="请输入图片中的字母"
                @keyup.enter="handleSubmit"
              />
              <button
                type="button"
                class="auth-card__captcha-image"
                :disabled="loadingCaptcha"
                @click="loadCaptcha"
              >
                <img v-if="captchaImage" class="auth-card__captcha-img" :src="captchaImage" alt="登录图形验证码" />
                <span v-else>{{ loadingCaptcha ? '加载中...' : '点击获取验证码' }}</span>
              </button>
            </div>
            <div class="auth-card__captcha-hint">看不清？点击图片刷新验证码。</div>
          </el-form-item>

          <div class="auth-card__aux">
            <el-button text type="primary" @click="openResetDialog">忘记密码</el-button>
          </div>

          <el-button
            class="auth-card__submit"
            type="primary"
            size="large"
            :loading="authStore.loading"
            @click="handleSubmit"
          >
            登录并进入工作台
          </el-button>
        </el-form>

        <div class="auth-card__footer">
          还没有账号？
          <router-link to="/register">去注册</router-link>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="resetDialogVisible"
      title="邮箱验证码重置密码"
      width="min(92vw, 520px)"
      destroy-on-close
    >
      <div class="reset-dialog__intro">
        输入注册邮箱，发送 6 位验证码到邮箱后即可设置新密码。
      </div>

      <el-form ref="resetFormRef" :model="resetForm" :rules="resetRules" label-position="top">
        <el-form-item label="注册邮箱" prop="email">
          <el-input v-model="resetForm.email" size="large" placeholder="请输入注册邮箱" />
        </el-form-item>

        <el-form-item label="邮箱验证码" prop="code">
          <div class="reset-dialog__code-row">
            <el-input
              v-model="resetForm.code"
              size="large"
              maxlength="6"
              placeholder="请输入 6 位验证码"
              @keyup.enter="handleResetPassword"
            />
            <el-button
              size="large"
              :disabled="!canSendResetCode"
              :loading="sendingResetCode"
              @click="handleSendResetCode"
            >
              {{ resendCountdown > 0 ? `${resendCountdown}s 后重发` : '发送验证码' }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="resetForm.newPassword"
            size="large"
            type="password"
            show-password
            placeholder="请输入至少 6 位的新密码"
          />
        </el-form-item>

        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input
            v-model="resetForm.confirmPassword"
            size="large"
            type="password"
            show-password
            placeholder="请再次输入新密码"
            @keyup.enter="handleResetPassword"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="reset-dialog__footer">
          <el-button size="large" @click="resetDialogVisible = false">取消</el-button>
          <el-button size="large" type="primary" :loading="submittingReset" @click="handleResetPassword">
            重置密码
          </el-button>
        </div>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.auth-page {
  display: grid;
  min-height: 100vh;
  grid-template-columns: minmax(0, 1.2fr) minmax(380px, 0.8fr);
  background:
    linear-gradient(135deg, rgba(20, 73, 61, 0.96), rgba(11, 34, 31, 0.98)),
    radial-gradient(circle at 20% 20%, rgba(238, 189, 83, 0.28), transparent 28%);
}

.auth-page__panel {
  min-width: 0;
}

.auth-page__panel--hero {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 64px;
  color: #f8f3e7;
}

.auth-page__eyebrow {
  margin-bottom: 18px;
  color: rgba(248, 243, 231, 0.76);
  font-size: 13px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1 {
  max-width: 680px;
  margin: 0;
  color: #fffaf0;
  font-size: clamp(38px, 5vw, 62px);
  line-height: 1.04;
}

.auth-page__lead {
  max-width: 620px;
  margin-top: 22px;
  color: rgba(248, 243, 231, 0.82);
  font-size: 18px;
  line-height: 1.8;
}

.auth-page__highlights {
  display: grid;
  max-width: 720px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 40px;
}

.auth-page__highlights article {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border: 1px solid rgba(248, 243, 231, 0.12);
  border-radius: 24px;
  padding: 18px;
  background: rgba(255, 255, 255, 0.06);
}

.auth-page__highlights strong {
  font-size: 16px;
}

.auth-page__highlights span {
  color: rgba(248, 243, 231, 0.72);
  font-size: 13px;
  line-height: 1.6;
}

.auth-page__panel--form {
  display: grid;
  place-items: center;
  padding: 32px;
  background: linear-gradient(180deg, #f8f2e5 0%, #f6f0e4 100%);
}

.auth-card {
  width: min(100%, 460px);
  border: 1px solid rgba(25, 48, 43, 0.08);
  border-radius: 28px;
  padding: 30px;
  background: rgba(255, 252, 245, 0.9);
  box-shadow: 0 24px 60px rgba(24, 54, 48, 0.12);
}

.auth-card__header {
  margin-bottom: 24px;
}

.auth-card__header h2 {
  margin: 0;
  color: #1d2724;
  font-size: 28px;
}

.auth-card__header p {
  margin-top: 10px;
  color: #6f7169;
  line-height: 1.7;
}

.auth-card__aux {
  display: flex;
  justify-content: flex-end;
  margin: -4px 0 8px;
}

.auth-card__captcha-row {
  display: grid;
  grid-template-columns: minmax(0, 188px) 120px;
  gap: 12px;
  align-items: center;
  width: fit-content;
  max-width: 100%;
}

.auth-card__captcha-image {
  display: grid;
  place-items: center;
  height: 40px;
  overflow: hidden;
  border: 1px solid rgba(25, 48, 43, 0.12);
  border-radius: 12px;
  padding: 0;
  background: #fff9ef;
  cursor: pointer;
  appearance: none;
}

.auth-card__captcha-image:disabled {
  cursor: wait;
  opacity: 0.72;
}

.auth-card__captcha-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: fill;
}

:deep(.auth-card__captcha-input .el-input__wrapper) {
  min-height: 40px;
}

.auth-card__captcha-hint {
  margin-top: 8px;
  color: #7a786f;
  font-size: 12px;
}

.auth-card__submit {
  width: 100%;
  margin-top: 10px;
}

.auth-card__footer {
  margin-top: 18px;
  color: #6f7169;
  text-align: center;
}

.auth-card__footer a {
  color: #1f6f54;
  font-weight: 600;
  text-decoration: none;
}

.reset-dialog__intro {
  margin-bottom: 16px;
  color: #5f625a;
  line-height: 1.7;
}

.reset-dialog__code-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  width: 100%;
}

.reset-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 1100px) {
  .auth-page {
    grid-template-columns: 1fr;
  }

  .auth-page__panel--hero {
    padding: 32px 20px 12px;
  }

  .auth-page__highlights {
    grid-template-columns: 1fr;
  }

  .auth-page__panel--form {
    padding: 20px;
  }
}

@media (max-width: 640px) {
  .auth-card__captcha-row,
  .reset-dialog__code-row {
    grid-template-columns: 1fr;
  }
}
</style>
