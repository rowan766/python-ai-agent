import { http } from '@/api/http'
import type {
  UserListQuery,
  UserListResponse,
  UserMembershipUpdatePayload,
  UserStatusUpdatePayload,
} from '@/types/users'

export async function fetchUsers(params?: UserListQuery): Promise<UserListResponse> {
  const { data } = await http.get<UserListResponse>('/api/users', { params })
  return data
}

export async function updateUserStatus(userId: number, payload: UserStatusUpdatePayload) {
  const { data } = await http.patch(`/api/users/${userId}/status`, payload)
  return data
}

export async function updateUserMemberships(
  userId: number,
  payload: UserMembershipUpdatePayload,
) {
  const { data } = await http.put(`/api/users/${userId}/memberships`, payload)
  return data
}
