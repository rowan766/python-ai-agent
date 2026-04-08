<script setup lang="ts">
import {
  ChatDotRound,
  Expand,
  Files,
  Fold,
  HomeFilled,
  OfficeBuilding,
  Search,
  Finished,
  UploadFilled,
  UserFilled,
} from '@element-plus/icons-vue'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

interface MenuItem {
  label: string
  path: string
  icon: unknown
}

const props = defineProps<{
  collapsed: boolean
}>()

const emit = defineEmits<{
  (event: 'toggle'): void
}>()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const menuItems = computed<MenuItem[]>(() => {
  if (!authStore.organizationReady) {
    return [{ label: '组织接入', path: '/onboarding', icon: OfficeBuilding }]
  }

  const items: MenuItem[] = [
    { label: '工作台', path: '/workspace', icon: HomeFilled },
    { label: '知识空间', path: '/knowledge-bases', icon: Files },
    { label: '文档中心', path: '/documents', icon: Files },
    { label: '上传文档', path: '/documents/upload', icon: UploadFilled },
    { label: '知识检索', path: '/knowledge/search', icon: Search },
    { label: 'AI 对话', path: '/ai/chat', icon: ChatDotRound },
    { label: '审批中心', path: '/approvals', icon: Finished },
    { label: '组织与部门', path: '/organization', icon: OfficeBuilding },
  ]

  if (authStore.isPlatformAdmin) {
    items.push({ label: '用户管理', path: '/users', icon: UserFilled })
  }

  return items
})

const activePath = computed(() => String(route.meta.navKey ?? route.path))

function handleSelect(path: string) {
  void router.push(path)
}
</script>

<template>
  <aside :class="['sidebar', { 'sidebar--collapsed': props.collapsed }]">
    <div class="sidebar__brand">
      <div class="sidebar__brand-main">
        <div class="sidebar__mark">AI</div>
        <div v-if="!props.collapsed" class="sidebar__title">知识平台</div>
      </div>

      <el-tooltip :content="props.collapsed ? '展开菜单' : '收起菜单'" placement="right">
        <button class="sidebar__toggle" type="button" @click="emit('toggle')">
          <el-icon>
            <component :is="props.collapsed ? Expand : Fold" />
          </el-icon>
        </button>
      </el-tooltip>
    </div>

    <el-menu
      :default-active="activePath"
      :collapse="props.collapsed"
      :collapse-transition="false"
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
  background: #ffffff;
  color: #111827;
}

.sidebar__brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 4px 8px 10px;
}

.sidebar__brand-main {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 12px;
}

.sidebar__mark {
  display: grid;
  height: 40px;
  width: 40px;
  place-items: center;
  border-radius: 10px;
  background: #409eff;
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.sidebar__title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  white-space: nowrap;
}

.sidebar__toggle {
  display: grid;
  height: 34px;
  width: 34px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  background: #ffffff;
  color: #6b7280;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease;
}

.sidebar__toggle:hover {
  background: #f5f7fa;
  transform: translateY(-1px);
}

.sidebar__menu {
  border-right: 0;
  background: transparent;
}

:deep(.sidebar__menu.el-menu--collapse) {
  width: 100%;
}

:deep(.sidebar__menu .el-menu-item) {
  height: auto;
  min-height: 48px;
  margin-bottom: 8px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: #4b5563;
  line-height: 1.3;
  padding-top: 10px;
  padding-bottom: 10px;
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

:deep(.sidebar__menu.el-menu--collapse .el-menu-item) {
  justify-content: center;
  padding-right: 0;
  padding-left: 0;
}

:deep(.sidebar__menu.el-menu--collapse .el-menu-item .el-icon) {
  margin-right: 0;
}

:deep(.sidebar__menu .el-menu-item.is-active) {
  border-color: rgba(64, 158, 255, 0.25);
  background: #ecf5ff;
  color: #409eff;
  box-shadow: none;
}

:deep(.sidebar__menu .el-menu-item:hover) {
  background: #f5f7fa;
  transform: none;
}

.sidebar__label {
  font-size: 14px;
}

.sidebar--collapsed {
  padding-right: 12px;
  padding-left: 12px;
}
</style>
