<template>
  <el-container class="layout-shell">
    <el-aside :width="isCollapse ? '72px' : '232px'" class="layout-aside">
      <div class="brand-panel">
        <div class="brand-mark">
          <el-icon><Grid /></el-icon>
        </div>
        <div v-if="!isCollapse" class="brand-copy">
          <strong>企业级RAG管理系统</strong>
          <span>Admin Console</span>
        </div>
      </div>

      <el-scrollbar class="sidebar-scroll">
        <el-menu
          :default-active="activeMenu"
          :default-openeds="defaultOpeneds"
          :collapse="isCollapse"
          :collapse-transition="false"
          router
          class="layout-menu"
        >
          <SidebarMenuItem
            v-for="menu in menuTree"
            :key="menu.id"
            :item="menu"
          />
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <el-container class="layout-content">
      <el-header class="layout-header">
        <div class="header-topbar">
          <div class="header-left">
            <button class="icon-button" type="button" @click="toggleCollapse">
              <el-icon>
                <Expand v-if="isCollapse" />
                <Fold v-else />
              </el-icon>
            </button>

            <span class="header-divider" aria-hidden="true"></span>

            <div class="header-breadcrumb">
              <el-breadcrumb separator="/">
                <el-breadcrumb-item
                  v-for="item in breadcrumbItems"
                  :key="item.path"
                >
                  {{ item.title }}
                </el-breadcrumb-item>
              </el-breadcrumb>
            </div>
          </div>

          <div class="header-right">
            <div class="header-actions">
              <el-tooltip content="刷新页面" placement="bottom">
                <button class="icon-button icon-button--compact" type="button" @click="refreshCurrentRoute">
                  <el-icon><RefreshRight /></el-icon>
                </button>
              </el-tooltip>

              <el-tooltip content="全屏" placement="bottom">
                <button class="icon-button icon-button--compact" type="button" @click="toggleFullscreen">
                  <el-icon><FullScreen /></el-icon>
                </button>
              </el-tooltip>
            </div>

            <span class="header-divider" aria-hidden="true"></span>

            <el-dropdown @command="handleCommand">
              <button class="user-button" type="button">
                <span class="user-avatar">
                  <el-icon><UserFilled /></el-icon>
                </span>
                <span class="user-name">{{ userStore.username }}</span>
                <el-icon class="user-arrow"><ArrowDown /></el-icon>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                  <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <div class="route-tabs">
          <button
            v-for="tab in visitedTabs"
            :key="tab.path"
            type="button"
            class="route-tab"
            :class="{ 'route-tab--active': tab.path === route.path }"
            @click="goToTab(tab)"
            @contextmenu.prevent="openTabContextMenu($event, tab)"
          >
            <span>{{ tab.title }}</span>
            <el-icon
              v-if="tab.closable"
              class="route-tab__close"
              @click.stop="closeTab(tab)"
            >
              <Close />
            </el-icon>
          </button>
        </div>
      </el-header>

      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>

    <teleport to="body">
      <div
        v-if="contextMenu.visible"
        class="tab-context-menu"
        :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
      >
        <button type="button" class="tab-context-item" @click="handleTabMenuAction('refresh')">
          <el-icon><RefreshRight /></el-icon>
          <span>刷新页面</span>
        </button>
        <button type="button" class="tab-context-item" @click="handleTabMenuAction('closeCurrent')">
          <el-icon><Close /></el-icon>
          <span>关闭当前</span>
        </button>
        <button type="button" class="tab-context-item" @click="handleTabMenuAction('closeOthers')">
          <el-icon><CircleClose /></el-icon>
          <span>关闭其他</span>
        </button>
        <button type="button" class="tab-context-item" @click="handleTabMenuAction('closeLeft')">
          <el-icon><Back /></el-icon>
          <span>关闭左侧</span>
        </button>
        <button type="button" class="tab-context-item" @click="handleTabMenuAction('closeRight')">
          <el-icon><Right /></el-icon>
          <span>关闭右侧</span>
        </button>
        <button type="button" class="tab-context-item" @click="handleTabMenuAction('closeAll')">
          <el-icon><RemoveFilled /></el-icon>
          <span>全部关闭</span>
        </button>
      </div>
    </teleport>
  </el-container>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  ArrowDown,
  Back,
  CircleClose,
  Close,
  Expand,
  Fold,
  FullScreen,
  Grid,
  RefreshRight,
  RemoveFilled,
  Right,
  UserFilled
} from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'
import SidebarMenuItem from './SidebarMenuItem.vue'
import { findOpenMenuIndexes, getRenderableMenus } from '../router/menuRuntime'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const visitedTabsStorageKey = 'rag-admin:visited-tabs'

const loadVisitedTabs = () => {
  if (typeof window === 'undefined') {
    return []
  }

  try {
    const rawValue = window.sessionStorage.getItem(visitedTabsStorageKey)
    if (!rawValue) {
      return []
    }

    const parsedValue = JSON.parse(rawValue)
    if (!Array.isArray(parsedValue)) {
      return []
    }

    return parsedValue.filter((item) => item && typeof item.path === 'string' && typeof item.title === 'string')
  } catch (error) {
    return []
  }
}

const saveVisitedTabs = (tabs) => {
  if (typeof window === 'undefined') {
    return
  }

  window.sessionStorage.setItem(visitedTabsStorageKey, JSON.stringify(tabs))
}

const isCollapse = ref(false)
const visitedTabs = ref(loadVisitedTabs())
const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  tabPath: ''
})
const handleDocumentClick = () => hideTabContextMenu()
const handleDocumentContextMenu = (event) => {
  const target = event.target
  if (!(target instanceof Element) || !target.closest('.route-tab')) {
    hideTabContextMenu()
  }
}

const activeMenu = computed(() => route.path)
const menuTree = computed(() => getRenderableMenus(userStore.menus))
const defaultOpeneds = computed(() => findOpenMenuIndexes(menuTree.value, route.path))

const findMenuTrail = (menus, targetPath, parents = []) => {
  for (const menu of menus) {
    const currentTrail = [...parents, menu]
    if (menu.routePath === targetPath || menu.path === targetPath) {
      return currentTrail
    }
    if (menu.children?.length) {
      const matched = findMenuTrail(menu.children, targetPath, currentTrail)
      if (matched.length) {
        return matched
      }
    }
  }
  return []
}

const breadcrumbItems = computed(() => {
  const menuTrail = findMenuTrail(menuTree.value, route.path)
  if (menuTrail.length) {
    return menuTrail.map((menu) => ({
      title: menu.title,
      path: menu.routePath || menu.path || `menu-${menu.id}`
    }))
  }

  if (route.meta?.title) {
    return [{ title: route.meta.title, path: route.path }]
  }

  return [{ title: '首页', path: '/dashboard' }]
})

const buildTabItem = (currentRoute) => ({
  path: currentRoute.path,
  title: currentRoute.meta?.title || currentRoute.name || currentRoute.path,
  closable: currentRoute.path !== '/dashboard'
})

const hideTabContextMenu = () => {
  contextMenu.value.visible = false
}

watch(
  () => route.path,
  () => {
    hideTabContextMenu()
    if (!route.meta?.title) {
      return
    }

    const exists = visitedTabs.value.find((item) => item.path === route.path)
    if (!exists) {
      visitedTabs.value.push(buildTabItem(route))
    }
  },
  { immediate: true }
)

watch(
  visitedTabs,
  (tabs) => {
    saveVisitedTabs(tabs)
  },
  { deep: true }
)

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

const refreshCurrentRoute = () => {
  window.location.reload()
}

const toggleFullscreen = async () => {
  if (!document.fullscreenElement) {
    await document.documentElement.requestFullscreen()
    return
  }
  await document.exitFullscreen()
}

const goToTab = (tab) => {
  if (tab.path !== route.path) {
    router.push(tab.path)
  }
}

const closeTab = (tab) => {
  if (!tab.closable) {
    return
  }

  const index = visitedTabs.value.findIndex((item) => item.path === tab.path)
  if (index === -1) {
    return
  }

  const wasActive = route.path === tab.path
  visitedTabs.value.splice(index, 1)

  if (wasActive) {
    const nextTab = visitedTabs.value[index - 1] || visitedTabs.value[index] || visitedTabs.value[0]
    router.push(nextTab?.path || '/dashboard')
  }
}

const openTabContextMenu = (event, tab) => {
  contextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    tabPath: tab.path
  }
}

const getContextTabIndex = () => visitedTabs.value.findIndex((item) => item.path === contextMenu.value.tabPath)

const ensureActiveTabExists = () => {
  if (!visitedTabs.value.some((item) => item.path === route.path)) {
    router.push(visitedTabs.value[visitedTabs.value.length - 1]?.path || '/dashboard')
  }
}

const handleTabMenuAction = (action) => {
  const currentIndex = getContextTabIndex()
  if (currentIndex === -1) {
    hideTabContextMenu()
    return
  }

  const currentTab = visitedTabs.value[currentIndex]

  if (action === 'refresh') {
    hideTabContextMenu()
    if (currentTab.path === route.path) {
      refreshCurrentRoute()
    } else {
      router.push(currentTab.path)
    }
    return
  }

  if (action === 'closeCurrent') {
    closeTab(currentTab)
  }

  if (action === 'closeOthers') {
    visitedTabs.value = visitedTabs.value.filter((item) => item.path === currentTab.path || !item.closable)
    router.push(currentTab.path)
  }

  if (action === 'closeLeft') {
    visitedTabs.value = visitedTabs.value.filter((item, index) => index >= currentIndex || !item.closable)
    ensureActiveTabExists()
  }

  if (action === 'closeRight') {
    visitedTabs.value = visitedTabs.value.filter((item, index) => index <= currentIndex || !item.closable)
    ensureActiveTabExists()
  }

  if (action === 'closeAll') {
    visitedTabs.value = visitedTabs.value.filter((item) => !item.closable)
    router.push('/dashboard')
  }

  hideTabContextMenu()
}

const handleCommand = async (command) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗?', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      userStore.logout()
      visitedTabs.value = []
      window.sessionStorage.removeItem(visitedTabsStorageKey)
      ElMessage.success('退出成功')
      router.push('/login')
    } catch (error) {
      // 用户取消
    }
  } else if (command === 'profile') {
    router.push('/profile')
  }
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
  document.addEventListener('contextmenu', handleDocumentContextMenu)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  document.removeEventListener('contextmenu', handleDocumentContextMenu)
})
</script>

<style scoped>
.layout-shell {
  height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(79, 157, 255, 0.08), transparent 24%),
    linear-gradient(180deg, #f6f8fb 0%, #f1f5f9 100%);
}

.layout-aside {
  background:
    radial-gradient(ellipse at 0% 0%, rgba(0, 200, 185, 0.10) 0%, transparent 55%),
    radial-gradient(ellipse at 100% 100%, rgba(0, 120, 200, 0.08) 0%, transparent 50%),
    linear-gradient(180deg, #0b2535 0%, #0d2e42 40%, #091e2e 100%);
  border-right: 1px solid rgba(0, 210, 195, 0.08);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.25);
  transition: width 0.28s ease;
}

.brand-panel {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 66px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #00c6b8 0%, #0088cc 100%);
  color: #fff;
  font-size: 16px;
  box-shadow: 0 6px 18px rgba(0, 198, 184, 0.40);
}

.brand-copy {
  display: flex;
  flex-direction: column;
}

.brand-copy strong {
  color: #f8fbff;
  font-size: 15px;
  line-height: 1.2;
}

.brand-copy span {
  color: #93a7be;
  font-size: 11px;
  margin-top: 2px;
}

.sidebar-scroll {
  height: calc(100vh - 66px);
}

.layout-menu {
  padding: 12px 10px 20px;
  border-right: none;
  background: transparent;
}

.layout-menu:not(.el-menu--collapse) {
  width: 232px;
}

:deep(.el-menu) {
  border-right: none;
  background: transparent;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  height: 42px;
  margin: 4px 6px;
  border-radius: 8px;
  color: #b9c8d8;
  transition: all 0.18s ease;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  background: rgba(255, 255, 255, 0.08) !important;
  color: #ffffff !important;
}

:deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, #00c0b4 0%, #0088cc 100%) !important;
  color: #ffffff !important;
  box-shadow: 0 6px 18px rgba(0, 180, 170, 0.30);
}

:deep(.el-sub-menu .el-menu-item) {
  min-width: auto;
  margin-left: 16px;
  color: #93a7be;
}

:deep(.el-sub-menu .el-menu-item.is-active) {
  background: rgba(0, 196, 180, 0.18) !important;
  color: #ffffff !important;
  box-shadow: inset 3px 0 0 #00d4c8;
}

:deep(.el-sub-menu__icon-arrow) {
  color: #b5c2d1;
}

:deep(.el-menu--collapse .el-menu-item),
:deep(.el-menu--collapse .el-sub-menu__title) {
  justify-content: center;
}

:deep(.el-menu--collapse .el-menu-item .el-icon),
:deep(.el-menu--collapse .el-sub-menu__title .el-icon),
:deep(.el-menu--collapse .el-menu-item [class^='el-icon']),
:deep(.el-menu--collapse .el-menu-item [class*=' el-icon']),
:deep(.el-menu--collapse .el-sub-menu__title [class^='el-icon']),
:deep(.el-menu--collapse .el-sub-menu__title [class*=' el-icon']) {
  margin-right: 0 !important;
  margin-left: 0 !important;
}

:deep(.el-menu--collapse .el-sub-menu__title span),
:deep(.el-menu--collapse .el-menu-item .el-menu-tooltip__trigger),
:deep(.el-menu--collapse .el-menu-item .el-tooltip__trigger),
:deep(.el-menu--collapse .el-sub-menu__title .el-tooltip__trigger) {
  display: flex !important;
  align-items: center;
  justify-content: center;
  width: 100%;
}

.layout-content {
  min-width: 0;
}

.layout-header {
  height: auto;
  padding: 0;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid #e7edf4;
  box-shadow: 0 6px 22px rgba(15, 23, 42, 0.04);
}

.header-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 6px 18px 4px;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-divider {
  width: 1px;
  height: 18px;
  background: linear-gradient(180deg, rgba(214, 224, 236, 0) 0%, #d8e1eb 20%, #d8e1eb 80%, rgba(214, 224, 236, 0) 100%);
  flex: 0 0 1px;
}

.header-breadcrumb {
  color: #6b7b91;
  font-size: 12px;
}

.header-breadcrumb :deep(.el-breadcrumb__inner) {
  font-weight: 500;
}

.header-breadcrumb :deep(.el-breadcrumb__separator) {
  color: #b3c0cf;
  margin: 0 10px;
}

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: 1px solid #e5ebf3;
  border-radius: 6px;
  background: #fff;
  color: #587089;
  cursor: pointer;
  transition: all 0.18s ease;
}

.icon-button--compact {
  width: 30px;
  height: 30px;
}

.icon-button:hover {
  border-color: #d6e0ec;
  background: #f7f9fc;
  color: #4c6178;
}

.icon-button:focus-visible,
.user-button:focus-visible,
.route-tab:focus-visible,
.tab-context-item:focus-visible {
  outline: 2px solid rgba(0, 185, 175, 0.28);
  outline-offset: 1px;
}

.user-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px 4px 6px;
  border: 1px solid #e8eef6;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  color: #334155;
  transition: all 0.18s ease;
}

.user-button:hover {
  border-color: #d6e0ec;
  background: #f7f9fc;
  color: #334155;
}

.user-avatar {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: linear-gradient(135deg, #d9ecff 0%, #eef6ff 100%);
  color: #2f7ef7;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
}

.user-arrow {
  color: #8ea2b8;
  font-size: 12px;
}

.route-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px 8px;
  border-top: 1px solid #edf1f6;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.78);
  overflow-x: auto;
}

.route-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 9px;
  border: 1px solid #dfe5ee;
  border-radius: 4px;
  background: #fff;
  color: #63788f;
  cursor: pointer;
  white-space: nowrap;
  font-size: 12px;
  transition: all 0.18s ease;
}

.route-tab:hover {
  color: #35506d;
  border-color: #bfd4ee;
  background: linear-gradient(180deg, #f6faff 0%, #eaf3ff 100%);
  box-shadow: 0 4px 10px rgba(47, 126, 247, 0.08);
}

.route-tab--active {
  color: #fff;
  background: linear-gradient(135deg, #00b8b0 0%, #0088cc 100%);
  border-color: transparent;
}

.route-tab__close {
  font-size: 11px;
  border-radius: 999px;
  transition: all 0.18s ease;
}

.route-tab:hover .route-tab__close {
  background: rgba(47, 126, 247, 0.12);
  color: #2f7ef7;
}

.route-tab--active .route-tab__close {
  color: rgba(255, 255, 255, 0.88);
}

.route-tab--active:hover .route-tab__close {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}

.layout-main {
  padding: 16px;
  background: transparent;
}

.tab-context-menu {
  position: fixed;
  z-index: 3000;
  min-width: 144px;
  padding: 6px 0;
  border: 1px solid #e6ebf2;
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12);
}

.tab-context-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: #334155;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}

.tab-context-item:hover {
  background: #f5f8fc;
}

@media (max-width: 960px) {
  .layout-shell {
    display: block;
  }

  .layout-aside {
    display: none;
  }

  .header-topbar {
    padding: 6px 12px 4px;
  }

  .route-tabs {
    padding: 8px 12px 8px;
  }

  .layout-main {
    padding: 12px;
  }
}
</style>
