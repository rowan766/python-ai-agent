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
  account: string
  password: string
  captcha_code: string
  captcha_token: string
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

export interface PasswordResetCodePayload {
  email: string
}

export interface PasswordResetCodeResponse {
  message: string
  expires_in_minutes: number
  debug_code?: string | null
}

export interface PasswordResetPayload {
  email: string
  code: string
  new_password: string
}

export interface SessionResponse {
  token_valid: boolean
  user: AuthUser
}

export interface LoginCaptchaResponse {
  captcha_token: string
  image_data: string
  expires_in_minutes: number
}
