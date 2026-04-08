<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import { getSidebarCollapsed, setSidebarCollapsed } from '@/utils/storage'
import { computed, ref, watch } from 'vue'

const isSidebarCollapsed = ref(getSidebarCollapsed())

const sidebarWidth = computed(() => (isSidebarCollapsed.value ? '96px' : '288px'))

watch(isSidebarCollapsed, (collapsed) => {
  setSidebarCollapsed(collapsed)
})

function toggleSidebar() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}
</script>

<template>
  <el-container class="app-shell">
    <el-aside class="app-shell__aside" :width="sidebarWidth">
      <AppSidebar :collapsed="isSidebarCollapsed" @toggle="toggleSidebar" />
    </el-aside>

    <el-container class="app-shell__main">
      <el-header class="app-shell__header">
        <AppHeader />
      </el-header>

      <el-main class="app-shell__content">
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
  transition: width 0.24s ease;
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
