export interface DepartmentNode {
  id: number
  parent_id: number | null
  code: string
  name: string
  full_name: string
  manager_user_id: number | null
  status: string
  children: DepartmentNode[]
}

export interface DepartmentTreeResponse {
  items: DepartmentNode[]
  count: number
}

export interface BootstrapDepartmentPayload {
  code: string
  name: string
  full_name?: string
}

export interface CreateDepartmentPayload {
  parent_id?: number
  code: string
  name: string
  full_name?: string
}

export interface UpdateDepartmentPayload {
  name?: string
  full_name?: string
  status?: 'active' | 'inactive'
}

export interface DepartmentMemberItem {
  membership_id: number
  user_id: number
  username: string
  email: string
  membership_type: string
  is_primary: boolean
  status: string
}

export interface DepartmentMemberListResponse {
  items: DepartmentMemberItem[]
  count: number
}

export interface DepartmentImpact {
  department_id: number
  child_department_count: number
  active_member_count: number
  knowledge_base_count: number
  document_count: number
}

export interface DepartmentManagerUpdatePayload {
  manager_user_id: number
}

export interface DepartmentParentUpdatePayload {
  parent_id?: number
}

export interface DepartmentJoinRequestPayload {
  target_department_id: number
  requested_role_code?: string
  reason: string
}

export interface DepartmentJoinDecisionPayload {
  review_comment?: string
}

export interface DepartmentJoinRequestItem {
  id: number
  target_department_id: number
  target_department_name: string
  requested_role_code?: string
  reason: string
  status: string
  review_comment?: string
  submitted_at: string
  reviewed_at?: string
}

export interface PendingDepartmentJoinRequestItem {
  id: number
  applicant_user_id: number
  applicant_email: string
  applicant_username: string
  target_department_id: number
  target_department_name: string
  requested_role_code?: string
  reason: string
  status: string
  submitted_at: string
}

export interface DepartmentJoinRequestListResponse<T> {
  items: T[]
  count: number
}
