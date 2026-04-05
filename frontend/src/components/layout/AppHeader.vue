<script setup lang="ts">
import { ArrowRight, Finished, Link, SwitchButton } from '@element-plus/icons-vue'
import { buildApiUrl } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const breadcrumbs = computed(() =>
  route.matched
    .map((record) => record.meta?.title)
    .filter((title): title is string => typeof title === 'string' && title.length > 0),
)

function openDocs() {
  window.open(buildApiUrl('/docs'), '_blank', 'noopener,noreferrer')
}

function logout() {
  authStore.logout()
  void router.push('/login')
}
</script>

<template>
  <header class="app-header">
    <div>
      <el-breadcrumb :separator-icon="ArrowRight">
        <el-breadcrumb-item v-for="item in breadcrumbs" :key="item">
          {{ item }}
        </el-breadcrumb-item>
      </el-breadcrumb>
      <div class="app-header__headline">
        {{ breadcrumbs.at(-1) || 'Enterprise RAG' }}
      </div>
    </div>

    <div class="app-header__actions">
      <el-tag
        :type="authStore.organizationReady ? 'success' : 'warning'"
        effect="plain"
        round
      >
        <el-icon><Finished /></el-icon>
        <span>{{ authStore.organizationReady ? '组织已接入' : '组织待接入' }}</span>
      </el-tag>

      <el-button text @click="openDocs">
        <el-icon><Link /></el-icon>
        <span>接口文档</span>
      </el-button>

      <el-dropdown>
        <div class="app-header__profile">
          <div class="app-header__avatar">{{ authStore.displayName.slice(0, 1).toUpperCase() }}</div>
          <div>
            <div class="app-header__name">{{ authStore.displayName }}</div>
            <div class="app-header__email">{{ authStore.user?.email }}</div>
          </div>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="router.push('/onboarding')">
              组织接入
            </el-dropdown-item>
            <el-dropdown-item divided @click="logout">
              <el-icon><SwitchButton /></el-icon>
              <span>退出登录</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.app-header__headline {
  margin-top: 12px;
  font-size: 28px;
  font-weight: 700;
  color: #183630;
  letter-spacing: -0.03em;
}

.app-header__actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.app-header__profile {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.app-header__avatar {
  display: grid;
  height: 38px;
  width: 38px;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(145deg, #1f6f54, #ba8a2e);
  color: #fff;
  font-weight: 700;
}

.app-header__name {
  font-weight: 600;
  color: #1d2724;
}

.app-header__email {
  color: #6f7169;
  font-size: 12px;
}

@media (max-width: 900px) {
  .app-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .app-header__actions {
    flex-wrap: wrap;
  }
}
</style>
