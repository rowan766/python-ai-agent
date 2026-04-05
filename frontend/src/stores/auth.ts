import { defineStore } from 'pinia'
import * as authApi from '@/api/modules/auth'
import type {
  AuthUser,
  LoginPayload,
  OrganizationStatus,
  RegisterPayload,
} from '@/types/auth'
import { clearAccessToken, getAccessToken, setAccessToken } from '@/utils/storage'

interface AuthState {
  token: string
  user: AuthUser | null
  initialized: boolean
  loading: boolean
  organizationStatus: OrganizationStatus
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: '',
    user: null,
    initialized: false,
    loading: false,
    organizationStatus: 'pending_assignment',
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token),
    organizationReady: (state) => state.organizationStatus === 'ready',
    displayName: (state) => state.user?.username || state.user?.email || '未登录用户',
  },
  actions: {
    hydrate() {
      this.token = getAccessToken()
      this.initialized = true
    },
    persistToken(token: string) {
      this.token = token
      setAccessToken(token)
    },
    clearSession() {
      this.token = ''
      this.user = null
      this.organizationStatus = 'pending_assignment'
      clearAccessToken()
    },
    async ensureSession() {
      if (!this.initialized) {
        this.hydrate()
      }

      if (this.token && !this.user) {
        await this.fetchCurrentUser()
      }
    },
    async login(payload: LoginPayload) {
      this.loading = true
      try {
        const result = await authApi.login(payload)
        this.persistToken(result.access_token)
        await this.fetchCurrentUser()
      } finally {
        this.loading = false
      }
    },
    async register(payload: RegisterPayload) {
      this.loading = true
      try {
        const result = await authApi.register(payload)
        this.persistToken(result.access_token)
        await this.fetchCurrentUser()
      } finally {
        this.loading = false
      }
    },
    async fetchCurrentUser(): Promise<AuthUser> {
      const user = await authApi.fetchCurrentUser()
      this.user = user
      this.organizationStatus = user.organization_status
      return user
    },
    logout() {
      this.clearSession()
    },
  },
})
