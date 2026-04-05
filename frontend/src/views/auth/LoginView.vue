<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref()
const form = reactive({
  email: '',
  password: '',
})

const rules = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
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
    ElMessage.error('登录失败，请检查邮箱和密码。')
    console.error(error)
  }
}
</script>

<template>
  <section class="auth-page">
    <div class="auth-page__panel auth-page__panel--hero">
      <p class="auth-page__eyebrow">Enterprise Knowledge Platform</p>
      <h1>让企业知识真正可管、可搜、可追溯。</h1>
      <p class="auth-page__lead">
        这一版前端先联通现有的认证、文档上传、向量切片与检索接口，同时预留组织、RBAC、审批流和知识空间的演进入口。
      </p>

      <div class="auth-page__highlights">
        <article>
          <strong>组织化知识空间</strong>
          <span>部门、知识库、文档与权限边界逐层收束。</span>
        </article>
        <article>
          <strong>可信问答体验</strong>
          <span>后续答案展示将明确标注来源空间与引用片段。</span>
        </article>
        <article>
          <strong>企业级治理能力</strong>
          <span>共享、审批、审计、版本管理全部以平台化方式预留。</span>
        </article>
      </div>
    </div>

    <div class="auth-page__panel auth-page__panel--form">
      <div class="auth-card">
        <div class="auth-card__header">
          <h2>登录平台</h2>
          <p>先接通现有 FastAPI 接口，后续再接入组织与角色。</p>
        </div>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="form.email" placeholder="请输入登录邮箱" />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              show-password
              placeholder="请输入密码"
              @keyup.enter="handleSubmit"
            />
          </el-form-item>

          <el-button
            class="auth-card__submit"
            type="primary"
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
</style>
