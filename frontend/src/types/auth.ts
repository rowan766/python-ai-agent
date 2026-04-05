export interface MembershipSummary {
  id: number
  department_id: number
  department_name: string
  department_code: string
  membership_type: string
  is_primary: boolean
  status: string
}

export interface AuthUser {
  id: number
  email: string
  username: string
  organization_status: OrganizationStatus
  memberships: MembershipSummary[]
}

export type OrganizationStatus = 'pending_assignment' | 'ready'

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  email: string
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}
