const ACCESS_TOKEN_KEY = 'enterprise_rag_access_token'
const SIDEBAR_COLLAPSED_KEY = 'enterprise_rag_sidebar_collapsed'
const ACTIVE_DEPARTMENT_KEY = 'enterprise_rag_active_department_id'

export function getAccessToken(): string {
  return window.localStorage.getItem(ACCESS_TOKEN_KEY) ?? ''
}

export function setAccessToken(token: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, token)
}

export function clearAccessToken(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY)
}

export function getActiveDepartmentId(): number | null {
  const rawValue = window.localStorage.getItem(ACTIVE_DEPARTMENT_KEY)
  if (!rawValue) {
    return null
  }

  const parsed = Number(rawValue)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

export function setActiveDepartmentId(departmentId: number | null): void {
  if (departmentId === null) {
    window.localStorage.removeItem(ACTIVE_DEPARTMENT_KEY)
    return
  }
  window.localStorage.setItem(ACTIVE_DEPARTMENT_KEY, String(departmentId))
}

export function clearActiveDepartmentId(): void {
  window.localStorage.removeItem(ACTIVE_DEPARTMENT_KEY)
}

export function getSidebarCollapsed(): boolean {
  return window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true'
}

export function setSidebarCollapsed(collapsed: boolean): void {
  window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(collapsed))
}
