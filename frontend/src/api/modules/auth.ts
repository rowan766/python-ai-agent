import { http } from '@/api/http'
import type {
  AuthUser,
  LoginCaptchaResponse,
  LoginPayload,
  PasswordResetCodePayload,
  PasswordResetCodeResponse,
  PasswordResetPayload,
  RegisterPayload,
  SessionResponse,
  TokenResponse,
} from '@/types/auth'

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const { data } = await http.post<TokenResponse>('/api/auth/login', payload)
  return data
}

export async function fetchLoginCaptcha(): Promise<LoginCaptchaResponse> {
  const { data } = await http.get<LoginCaptchaResponse>('/api/auth/login-captcha')
  return data
}

export async function register(payload: RegisterPayload): Promise<TokenResponse> {
  const { data } = await http.post<TokenResponse>('/api/auth/register', payload)
  return data
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const { data } = await http.get<AuthUser>('/api/auth/me')
  return data
}

export async function verifySession(): Promise<SessionResponse> {
  const { data } = await http.get<SessionResponse>('/api/auth/session')
  return data
}

export async function requestPasswordResetCode(
  payload: PasswordResetCodePayload,
): Promise<PasswordResetCodeResponse> {
  const { data } = await http.post<PasswordResetCodeResponse>('/api/auth/password-reset/code', payload)
  return data
}

export async function resetPassword(payload: PasswordResetPayload): Promise<{ message: string }> {
  const { data } = await http.post<{ message: string }>('/api/auth/password-reset/confirm', payload)
  return data
}
