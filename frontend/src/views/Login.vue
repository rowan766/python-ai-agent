<template>
  <div class="login-container">
    <!-- 背景光晕 -->
    <div class="bg-orb bg-orb-1"></div>
    <div class="bg-orb bg-orb-2"></div>

    <!-- 整体居中内容区 -->
    <div class="login-content">

      <!-- 左侧：品牌区（直接在背景上，无卡片） -->
      <div class="brand-panel">
        <div class="brand-logo-wrap">
          <div class="brand-logo">R</div>
          <span class="brand-badge">ENTERPRISE KNOWLEDGE ENGINE</span>
        </div>
        <h1 class="brand-title">企业级<span class="brand-rag">RAG</span></h1>
        <p class="brand-desc">
          智能化知识管理平台，将分散的企业文档统一入库，<br />
          结合向量检索与大语言模型，为团队提供精准的知识问答服务。
        </p>

        <div class="feature-grid">
          <div v-for="f in features" :key="f.title" class="feature-card">
            <div class="feature-icon">{{ f.icon }}</div>
            <div>
              <div class="feature-title">{{ f.title }}</div>
              <div class="feature-desc">{{ f.desc }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：登录卡片 -->
      <div class="login-box">
        <div class="login-header">
          <h2>欢迎登录</h2>
          <p>请输入账号和密码登录企业知识库平台</p>
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
              class="form-input"
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
              class="form-input"
            />
          </el-form-item>

          <el-form-item prop="captchaCode">
            <div class="captcha-row">
              <el-input
                v-model="loginForm.captchaCode"
                placeholder="请输入验证码"
                size="large"
                class="captcha-input form-input"
              />
              <button
                type="button"
                class="captcha-image-button"
                :disabled="captchaLoading"
                @click="fetchCaptcha"
              >
                <img v-if="captchaImage" :src="captchaImage" alt="验证码" class="captcha-image" />
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
              {{ loading ? '登录中...' : '登 录' }}
            </el-button>
          </el-form-item>
        </el-form>

        <div class="login-footer">ENTERPRISE RAG PLATFORM</div>
      </div>

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

const features = [
  { icon: '📂', title: '多格式文档管理', desc: '支持 PDF、Word、图片等格式，OCR 自动识别' },
  { icon: '🔍', title: '混合语义检索', desc: '向量相似度 + 关键词双引擎，召回率更高' },
  { icon: '🤖', title: 'AI 智能问答', desc: '精准引用文档内容，大模型生成结构化答案' },
  { icon: '🔐', title: '细粒度权限控制', desc: '按部门、角色、成员隔离知识空间访问权限' },
]

const loginForm = reactive({
  username: 'admin',
  password: '123456',
  captchaId: '',
  captchaCode: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于6位', trigger: 'blur' },
  ],
  captchaCode: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { min: 4, message: '验证码长度不能小于4位', trigger: 'blur' },
  ],
}

const fetchCaptcha = async () => {
  captchaLoading.value = true
  try {
    const res = await getCaptcha()
    loginForm.captchaId = res.data.captchaId
    loginForm.captchaCode = ''
    captchaImage.value = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(res.data.captchaSvg)}`
  } catch {
    captchaImage.value = ''
  } finally {
    captchaLoading.value = false
  }
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
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
  })
}

onMounted(() => {
  fetchCaptcha()
})
</script>

<style scoped>
/* ── 整页背景 ────────────────────────────────────────────────────── */
.login-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(ellipse at 15% 15%, rgba(0, 210, 195, 0.13) 0%, transparent 45%),
    radial-gradient(ellipse at 85% 85%, rgba(0, 130, 210, 0.12) 0%, transparent 45%),
    radial-gradient(ellipse at 70% 10%, rgba(0, 170, 230, 0.09) 0%, transparent 35%),
    radial-gradient(ellipse at 25% 90%, rgba(0, 180, 160, 0.08) 0%, transparent 35%),
    linear-gradient(145deg, #071c2b 0%, #0b2e42 28%, #0d3a52 55%, #0a2d40 78%, #071a27 100%);
}

/* ── 背景光晕（装饰用） ──────────────────────────────────────────── */
.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  pointer-events: none;
  z-index: 0;
}
.bg-orb-1 {
  width: 640px;
  height: 640px;
  top: -200px;
  left: -160px;
  background: radial-gradient(circle, rgba(0, 205, 190, 0.20) 0%, rgba(0, 160, 180, 0.08) 50%, transparent 70%);
}
.bg-orb-2 {
  width: 560px;
  height: 560px;
  bottom: -160px;
  right: -100px;
  background: radial-gradient(circle, rgba(0, 140, 215, 0.18) 0%, rgba(0, 100, 190, 0.07) 50%, transparent 70%);
}

/* ── 居中内容区（左品牌 + 右卡片） ─────────────────────────────── */
.login-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 80px;
  width: 100%;
  max-width: 1160px;
  padding: 0 60px;
}

/* ── 左侧品牌区（无卡片，直接在背景上） ─────────────────────────── */
.brand-panel {
  flex: 1;
  min-width: 0;
}

.brand-logo-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.brand-logo {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: linear-gradient(135deg, #00c6b8, #0088cc);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 800;
  color: #fff;
  box-shadow: 0 4px 16px rgba(0, 198, 184, 0.45);
  flex-shrink: 0;
}

.brand-badge {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1.5px;
  color: rgba(0, 210, 200, 0.7);
}

.brand-title {
  font-size: 56px;
  font-weight: 800;
  color: #fff;
  line-height: 1.1;
  margin: 0 0 20px;
  letter-spacing: -1px;
}

.brand-rag {
  background: linear-gradient(90deg, #00d4c8, #00aaff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brand-desc {
  font-size: 14px;
  line-height: 1.9;
  color: rgba(190, 220, 235, 0.65);
  margin: 0 0 36px;
}

/* ── 特性卡片 ────────────────────────────────────────────────────── */
.feature-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.feature-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px 20px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  backdrop-filter: blur(6px);
  transition: background 0.2s, border-color 0.2s;
}

.feature-card:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(0, 210, 200, 0.2);
}

.feature-icon {
  font-size: 24px;
  line-height: 1;
  margin-top: 1px;
  flex-shrink: 0;
}

.feature-title {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.88);
  margin-bottom: 4px;
}

.feature-desc {
  font-size: 13px;
  color: rgba(170, 205, 220, 0.55);
  line-height: 1.5;
}

/* ── 右侧登录卡片 ────────────────────────────────────────────────── */
.login-box {
  width: 380px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 20px;
  padding: 44px 40px 36px;
  box-shadow:
    0 24px 64px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.06);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h2 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 700;
  color: #0f2536;
}

.login-header p {
  margin: 0;
  font-size: 13px;
  color: #8a9db5;
}

/* ── 表单 ────────────────────────────────────────────────────────── */
.login-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.form-input :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px #dde5f0;
  background: #f7fafd;
  transition: box-shadow 0.2s, background 0.2s;
}

.form-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #9abce8;
}

.form-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(0, 150, 200, 0.28) !important;
  background: #fff;
}

/* ── 验证码 ──────────────────────────────────────────────────────── */
.captcha-row {
  display: flex;
  gap: 10px;
  width: 100%;
}

.captcha-input {
  flex: 1;
}

.captcha-image-button {
  width: 120px;
  height: 44px;
  padding: 4px;
  border: 1px solid #dde5f0;
  border-radius: 10px;
  background: linear-gradient(135deg, #dff2ff 0%, #d9e8ff 40%, #efe2ff 100%);
  cursor: pointer;
  overflow: hidden;
  flex-shrink: 0;
  transition: border-color 0.2s, transform 0.15s, box-shadow 0.2s;
}

.captcha-image-button:hover:not(:disabled) {
  border-color: #9abce8;
  box-shadow: 0 4px 12px rgba(0, 120, 200, 0.12);
  transform: translateY(-1px);
}

.captcha-image-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.captcha-image {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 7px;
  mix-blend-mode: multiply;
}

.captcha-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #7a90a8;
  font-size: 12px;
}

/* ── 登录按钮 ────────────────────────────────────────────────────── */
.login-button {
  width: 100%;
  height: 46px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 3px;
  background: linear-gradient(135deg, #00b8b0, #0088cc);
  border: none;
  box-shadow: 0 6px 18px rgba(0, 160, 180, 0.35);
  transition: opacity 0.2s, transform 0.15s, box-shadow 0.2s;
}

.login-button:hover {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(0, 160, 180, 0.42);
}

/* ── 底部标注 ────────────────────────────────────────────────────── */
.login-footer {
  text-align: center;
  margin-top: 20px;
  font-size: 10px;
  letter-spacing: 2.5px;
  color: #b8c8d8;
}

/* ── 响应式 ──────────────────────────────────────────────────────── */
@media (max-width: 860px) {
  .brand-panel { display: none; }
  .login-content { justify-content: center; padding: 0 20px; }
  .login-box { width: 100%; max-width: 400px; }
}
</style>
