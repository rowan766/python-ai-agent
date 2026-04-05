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
        path: 'onboarding',
        name: 'onboarding',
        component: () => import('@/views/OnboardingView.vue'),
        meta: { title: '组织接入', navKey: '/onboarding', requiresAuth: true },
      },
      {
        path: 'departments',
        name: 'departments',
        component: () => import('@/views/organization/DepartmentManagementView.vue'),
        meta: { title: '部门治理', navKey: '/departments', requiresAuth: true },
      },
      {
        path: 'knowledge-bases',
        name: 'knowledge-bases',
        component: () => import('@/views/knowledge/KnowledgeBaseListView.vue'),
        meta: { title: '知识库空间', navKey: '/knowledge-bases', requiresAuth: true },
      },
      {
        path: 'documents',
        name: 'documents',
        component: () => import('@/views/documents/DocumentLibraryView.vue'),
        meta: { title: '文档中心', navKey: '/documents', requiresAuth: true },
      },
      {
        path: 'documents/upload',
        name: 'documents-upload',
        component: () => import('@/views/documents/DocumentUploadView.vue'),
        meta: { title: '上传文档', navKey: '/documents/upload', requiresAuth: true },
      },
      {
        path: 'rag/search',
        name: 'rag-search',
        component: () => import('@/views/rag/RagSearchView.vue'),
        meta: { title: '智能检索', navKey: '/rag/search', requiresAuth: true },
      },
      {
        path: 'approvals',
        name: 'approvals',
        component: () => import('@/views/approvals/ApprovalCenterView.vue'),
        meta: { title: '审批中心', navKey: '/approvals', requiresAuth: true },
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
