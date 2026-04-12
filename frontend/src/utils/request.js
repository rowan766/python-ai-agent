import axios from 'axios'
import { ElMessage } from 'element-plus'
import { API_BASE_URL } from './api-base-url'

const clearAuthState = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user-store')
}

const redirectToLogin = () => {
  if (typeof window === 'undefined') {
    return
  }

  if (window.location.pathname === '/login') {
    return
  }

  const redirect = `${window.location.pathname}${window.location.search}${window.location.hash}`
  const loginUrl = `/login?redirect=${encodeURIComponent(redirect)}`
  window.location.replace(loginUrl)
}

// 创建 axios 实例
const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    if (config.data instanceof FormData) {
      if (typeof config.headers?.setContentType === 'function') {
        config.headers.setContentType(undefined)
      } else if (config.headers) {
        delete config.headers['Content-Type']
      }
    }

    // 从 localStorage 获取 token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    // 直接返回 data
    return response.data
  },
  error => {
    // 统一错误处理
    const status = error.response?.status
    const message = error.response?.data?.message || error.response?.data?.detail || error.message || '请求失败'

    if (status === 401) {
      clearAuthState()
      ElMessage.error(message || '登录状态已失效，请重新登录')
      redirectToLogin()
      return Promise.reject(error)
    }

    ElMessage.error(message)
    console.error('Response error:', error)
    return Promise.reject(error)
  }
)

export default request
