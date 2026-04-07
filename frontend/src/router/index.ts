import { ElMessage } from 'element-plus'
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { title: '登录', publicOnly: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { title: '注册', publicOnly: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/workspace' },
      {
        path: 'workspace',
        name: 'workspace',
        component: () => import('@/views/workspace/WorkspaceView.vue'),
        meta: { title: '工作台', navKey: '/workspace', requiresAuth: true },
      },
      {
        path: 'organization',
        name: 'organization',
        component: () => import('@/views/organization/OrganizationCenterView.vue'),
        meta: { title: '组织中心', navKey: '/organization', requiresAuth: true },
      },
      {
        path: 'onboarding',
        redirect: {
          name: 'organization',
          query: { tab: 'access' },
        },
      },
      {
        path: 'departments',
        name: 'departments',
        component: () => import('@/views/organization/DepartmentManagementView.vue'),
        meta: { title: '部门治理', navKey: '/organization', requiresAuth: true },
      },
      {
        path: 'knowledge-bases',
        redirect: {
          name: 'documents',
          query: { tab: 'bases' },
        },
      },
      {
        path: 'documents',
        name: 'documents',
        component: () => import('@/views/documents/DocumentLibraryView.vue'),
        meta: { title: '文档中心', navKey: '/documents', requiresAuth: true },
      },
      {
        path: 'documents/upload',
        redirect: {
          name: 'documents',
          query: { tab: 'upload' },
        },
      },
      {
        path: 'ai/chat',
        name: 'ai-chat',
        component: () => import('@/views/rag/RagSearchView.vue'),
        meta: { title: 'AI 对话', navKey: '/ai/chat', requiresAuth: true },
      },
      {
        path: 'knowledge/search',
        name: 'knowledge-search',
        component: () => import('@/views/rag/RagSearchView.vue'),
        meta: { title: '知识检索', navKey: '/knowledge/search', requiresAuth: true },
      },
      {
        path: 'rag/search',
        redirect: {
          name: 'knowledge-search',
        },
      },
      {
        path: 'approvals',
        redirect: {
          name: 'organization',
          query: { tab: 'approvals' },
        },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/system/NotFoundView.vue'),
    meta: { title: '页面不存在' },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia)

  if (!authStore.initialized) {
    authStore.hydrate()
  }

  if (to.meta.publicOnly && authStore.isAuthenticated) {
    return { name: 'workspace' }
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return {
      name: 'login',
      query: {
        redirect: to.fullPath,
      },
    }
  }

  if (to.meta.requiresAuth && authStore.isAuthenticated) {
    try {
      await authStore.ensureSession()
    } catch {
      authStore.logout()
      ElMessage.error('登录状态已失效，请重新登录。')
      return {
        name: 'login',
        query: {
          redirect: to.fullPath,
        },
      }
    }
  }

  return true
})
