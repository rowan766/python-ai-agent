const ACCESS_TOKEN_KEY = 'enterprise_rag_access_token'
const SIDEBAR_COLLAPSED_KEY = 'enterprise_rag_sidebar_collapsed'

export function getAccessToken(): string {
  return window.localStorage.getItem(ACCESS_TOKEN_KEY) ?? ''
}

export function setAccessToken(token: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, token)
}

export function clearAccessToken(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY)
}

export function getSidebarCollapsed(): boolean {
  return window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true'
}

export function setSidebarCollapsed(collapsed: boolean): void {
  window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(collapsed))
}
