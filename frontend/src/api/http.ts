import axios from 'axios'
import { clearAccessToken, getAccessToken } from '@/utils/storage'

const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || 'http://127.0.0.1:8000'
export const apiBaseUrl = rawApiBaseUrl.replace(/\/+$/, '')

export const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: 20000,
})

http.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearAccessToken()
    }
    return Promise.reject(error)
  },
)

export function buildApiUrl(path: string): string {
  return `${apiBaseUrl}${path.startsWith('/') ? path : `/${path}`}`
}
