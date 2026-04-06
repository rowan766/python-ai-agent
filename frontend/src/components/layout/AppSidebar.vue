<script setup lang="ts">
import {
  Document,
  Files,
  HomeFilled,
  OfficeBuilding,
} from '@element-plus/icons-vue'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

interface MenuItem {
  label: string
  path: string
  icon: unknown
}

const route = useRoute()
const router = useRouter()

const menuItems: MenuItem[] = [
  { label: '工作台', path: '/workspace', icon: HomeFilled },
  { label: '智能问答', path: '/rag/search', icon: Document },
  { label: '文档中心', path: '/documents', icon: Files },
  { label: '组织中心', path: '/organization', icon: OfficeBuilding },
]

const activePath = computed(() => String(route.meta.navKey ?? route.path))

function handleSelect(path: string) {
  void router.push(path)
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar__brand">
      <div class="sidebar__mark">AI</div>
      <div class="sidebar__title">知识平台</div>
    </div>

    <el-menu
      :default-active="activePath"
      class="sidebar__menu"
      @select="handleSelect"
    >
      <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
        <el-icon><component :is="item.icon" /></el-icon>
        <span class="sidebar__label">{{ item.label }}</span>
      </el-menu-item>
    </el-menu>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  height: 100%;
  flex-direction: column;
  gap: 20px;
  padding: 20px 14px;
  background:
    radial-gradient(circle at top, rgba(240, 198, 112, 0.18), transparent 34%),
    linear-gradient(180deg, #1b6b56 0%, #123e35 58%, #102c27 100%);
  color: #f6f1e8;
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 8px 10px;
}

.sidebar__mark {
  display: grid;
  height: 40px;
  width: 40px;
  place-items: center;
  border-radius: 12px;
  background: rgba(255, 248, 232, 0.14);
  color: #fff6dd;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.08em;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.sidebar__title {
  font-size: 16px;
  font-weight: 700;
  color: #fffaf0;
}

.sidebar__menu {
  border-right: 0;
  background: transparent;
}

:deep(.sidebar__menu .el-menu-item) {
  height: auto;
  min-height: 48px;
  margin-bottom: 8px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(246, 241, 232, 0.94);
  line-height: 1.3;
  padding-top: 10px;
  padding-bottom: 10px;
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

:deep(.sidebar__menu .el-menu-item.is-active) {
  background: rgba(255, 248, 232, 0.16);
  color: #fffdf7;
  box-shadow: inset 0 0 0 1px rgba(255, 248, 232, 0.08);
}

:deep(.sidebar__menu .el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.1);
  transform: translateX(2px);
}

.sidebar__label {
  font-size: 14px;
}
</style>
