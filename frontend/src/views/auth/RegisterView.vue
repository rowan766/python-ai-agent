<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref()
const form = reactive({
  email: '',
  username: '',
  password: '',
})

const rules = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
}

async function handleSubmit() {
  if (!formRef.value) {
    return
  }

  await formRef.value.validate()

  try {
    await authStore.register(form)
    ElMessage.success('注册成功，接下来先完成组织接入。')
    await router.push(authStore.organizationReady ? '/workspace' : '/onboarding')
  } catch (error) {
    ElMessage.error('注册失败，请确认邮箱或用户名是否已存在。')
    console.error(error)
  }
}
</script>

<template>
  <section class="register-page">
    <div class="register-page__hero">
      <p class="register-page__eyebrow">Phase 1 Frontend</p>
      <h1>从账号体系开始，把企业级 RAG 平台真正搭起来。</h1>
      <p class="register-page__copy">
        注册完成后会直接进入组织接入流程，再开始配置知识空间、上传资料和处理审批。
      </p>
    </div>

    <div class="register-page__form-wrap">
      <div class="register-card">
        <h2>创建账号</h2>
        <p>注册成功后先加入组织，再进入知识空间和文档工作流。</p>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="form.email" placeholder="请输入邮箱" />
          </el-form-item>
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              show-password
              placeholder="至少 6 位"
              @keyup.enter="handleSubmit"
            />
          </el-form-item>

          <el-button
            class="register-card__submit"
            type="primary"
            :loading="authStore.loading"
            @click="handleSubmit"
          >
            注册并进入平台
          </el-button>
        </el-form>

        <div class="register-card__footer">
          已有账号？
          <router-link to="/login">去登录</router-link>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.register-page {
  display: grid;
  min-height: 100vh;
  grid-template-columns: minmax(0, 1fr) minmax(420px, 520px);
  background:
    radial-gradient(circle at left top, rgba(186, 138, 46, 0.2), transparent 28%),
    linear-gradient(180deg, #fbf8f1 0%, #efe7da 100%);
}

.register-page__hero {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 64px;
}

.register-page__eyebrow {
  margin-bottom: 16px;
  color: #89652a;
  font-size: 13px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1 {
  max-width: 680px;
  margin: 0;
  color: #183630;
  font-size: clamp(38px, 5vw, 58px);
  line-height: 1.08;
}

.register-page__copy {
  max-width: 640px;
  margin-top: 20px;
  color: #615e56;
  font-size: 18px;
  line-height: 1.8;
}

.register-page__form-wrap {
  display: grid;
  place-items: center;
  padding: 32px;
  background: linear-gradient(180deg, rgba(24, 54, 48, 0.98), rgba(11, 34, 31, 0.98));
}

.register-card {
  width: min(100%, 460px);
  border-radius: 28px;
  padding: 30px;
  background: #fffdf7;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
}

.register-card h2 {
  margin: 0;
  color: #1d2724;
  font-size: 28px;
}

.register-card p {
  margin: 10px 0 24px;
  color: #6f7169;
  line-height: 1.7;
}

.register-card__submit {
  width: 100%;
  margin-top: 10px;
}

.register-card__footer {
  margin-top: 18px;
  color: #6f7169;
  text-align: center;
}

.register-card__footer a {
  color: #1f6f54;
  font-weight: 600;
  text-decoration: none;
}

@media (max-width: 1100px) {
  .register-page {
    grid-template-columns: 1fr;
  }

  .register-page__hero,
  .register-page__form-wrap {
    padding: 24px 20px;
  }
}
</style>
