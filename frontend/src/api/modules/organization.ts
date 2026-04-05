import { http } from '@/api/http'
import type {
  BootstrapDepartmentPayload,
  CreateDepartmentPayload,
  DepartmentImpact,
  DepartmentManagerUpdatePayload,
  DepartmentMemberListResponse,
  DepartmentParentUpdatePayload,
  DepartmentJoinDecisionPayload,
  DepartmentJoinRequestListResponse,
  DepartmentJoinRequestItem,
  DepartmentJoinRequestPayload,
  DepartmentTreeResponse,
  PendingDepartmentJoinRequestItem,
  UpdateDepartmentPayload,
} from '@/types/organization'

export async function fetchDepartmentTree(): Promise<DepartmentTreeResponse> {
  const { data } = await http.get<DepartmentTreeResponse>('/api/departments/tree')
  return data
}

export async function bootstrapFirstDepartment(payload: BootstrapDepartmentPayload) {
  const { data } = await http.post('/api/departments/bootstrap', payload)
  return data
}

export async function createDepartment(payload: CreateDepartmentPayload) {
  const { data } = await http.post('/api/departments', payload)
  return data
}

export async function updateDepartment(departmentId: number, payload: UpdateDepartmentPayload) {
  const { data } = await http.patch(`/api/departments/${departmentId}`, payload)
  return data
}

export async function fetchDepartmentMembers(
  departmentId: number,
): Promise<DepartmentMemberListResponse> {
  const { data } = await http.get<DepartmentMemberListResponse>(
    `/api/departments/${departmentId}/members`,
  )
  return data
}

export async function fetchDepartmentImpact(departmentId: number): Promise<DepartmentImpact> {
  const { data } = await http.get<DepartmentImpact>(`/api/departments/${departmentId}/impact`)
  return data
}

export async function updateDepartmentManager(
  departmentId: number,
  payload: DepartmentManagerUpdatePayload,
) {
  const { data } = await http.patch(`/api/departments/${departmentId}/manager`, payload)
  return data
}

export async function updateDepartmentParent(
  departmentId: number,
  payload: DepartmentParentUpdatePayload,
) {
  const { data } = await http.patch(`/api/departments/${departmentId}/parent`, payload)
  return data
}

export async function createDepartmentJoinRequest(payload: DepartmentJoinRequestPayload) {
  const { data } = await http.post('/api/department-requests', payload)
  return data
}

export async function fetchMyDepartmentJoinRequests() {
  const { data } = await http.get<DepartmentJoinRequestListResponse<DepartmentJoinRequestItem>>(
    '/api/department-requests/my',
  )
  return data
}

export async function fetchPendingDepartmentJoinRequests() {
  const { data } = await http.get<
    DepartmentJoinRequestListResponse<PendingDepartmentJoinRequestItem>
  >('/api/department-requests/pending')
  return data
}

export async function approveDepartmentJoinRequest(
  requestId: number,
  payload: DepartmentJoinDecisionPayload,
) {
  const { data } = await http.post(`/api/department-requests/${requestId}/approve`, payload)
  return data
}

export async function rejectDepartmentJoinRequest(
  requestId: number,
  payload: DepartmentJoinDecisionPayload,
) {
  const { data } = await http.post(`/api/department-requests/${requestId}/reject`, payload)
  return data
}
