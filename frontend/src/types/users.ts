import type { MembershipSummary, OrganizationStatus } from '@/types/auth'

export interface ManagedDepartmentSummary {
  id: number
  name: string
  code: string
}

export interface UserManagementItem {
  id: number
  email: string
  username: string
  is_active: boolean
  is_platform_admin: boolean
  organization_status: OrganizationStatus
  memberships: MembershipSummary[]
  managed_departments: ManagedDepartmentSummary[]
  created_at: string
}

export interface UserListResponse {
  items: UserManagementItem[]
  count: number
}

export interface UserListQuery {
  keyword?: string
  department_id?: number
  is_active?: boolean
}

export interface UserStatusUpdatePayload {
  is_active: boolean
}

export interface UserMembershipAssignment {
  department_id: number
  is_primary: boolean
}

export interface UserMembershipUpdatePayload {
  memberships: UserMembershipAssignment[]
}
