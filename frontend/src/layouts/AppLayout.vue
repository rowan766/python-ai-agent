<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <el-container class="app-shell">
    <el-aside class="app-shell__aside" width="288px">
      <AppSidebar />
    </el-aside>

    <el-container class="app-shell__main">
      <el-header class="app-shell__header">
        <AppHeader />
      </el-header>

      <el-main class="app-shell__content">
        <el-alert
          v-if="!authStore.organizationReady"
          class="app-shell__alert"
          title="当前账号还没有完成组织接入。完成部门归属后，知识库空间、文档列表和权限过滤检索才会进入你的可见范围。"
          type="warning"
          :closable="false"
          show-icon
        />

        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.app-shell__aside {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: hidden;
  border-right: 1px solid rgba(18, 56, 49, 0.08);
}

.app-shell__main {
  min-width: 0;
  background:
    radial-gradient(circle at top left, rgba(244, 225, 183, 0.5), transparent 28%),
    linear-gradient(180deg, #fcfaf4 0%, #f5f1e6 100%);
}

.app-shell__header {
  display: flex;
  align-items: center;
  padding: 28px 32px 0;
  height: auto;
}

.app-shell__content {
  padding: 24px 32px 32px;
}

.app-shell__alert {
  margin-bottom: 24px;
  border-radius: 18px;
}

@media (max-width: 1200px) {
  .app-shell {
    flex-direction: column;
  }

  .app-shell__aside {
    position: static;
    width: 100% !important;
    height: auto;
  }

  .app-shell__header,
  .app-shell__content {
    padding-left: 20px;
    padding-right: 20px;
  }
}
</style>
