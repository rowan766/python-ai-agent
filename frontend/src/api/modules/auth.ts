import { http } from '@/api/http'
import type { AuthUser, LoginPayload, RegisterPayload, TokenResponse } from '@/types/auth'

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const { data } = await http.post<TokenResponse>('/api/auth/login', payload)
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
