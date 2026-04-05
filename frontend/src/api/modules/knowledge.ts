import { http } from '@/api/http'
import type {
  CreateKnowledgeBaseShareRequestPayload,
  CreateKnowledgeBasePayload,
  KnowledgeBaseListResponse,
  KnowledgeBaseShareListResponse,
  KnowledgeBaseShareRequestListResponse,
  KnowledgeDocumentListResponse,
  ShareDecisionPayload,
  UploadKnowledgeDocumentPayload,
  UploadKnowledgeDocumentResponse,
} from '@/types/knowledge'

export async function fetchKnowledgeBases(departmentId?: number): Promise<KnowledgeBaseListResponse> {
  const { data } = await http.get<KnowledgeBaseListResponse>('/api/knowledge-bases', {
    params: departmentId ? { department_id: departmentId } : undefined,
  })
  return data
}

export async function createKnowledgeBase(payload: CreateKnowledgeBasePayload) {
  const { data } = await http.post('/api/knowledge-bases', payload)
  return data
}

export async function fetchKnowledgeBaseShares(
  knowledgeBaseId: number,
): Promise<KnowledgeBaseShareListResponse> {
  const { data } = await http.get<KnowledgeBaseShareListResponse>(
    `/api/knowledge-bases/${knowledgeBaseId}/shares`,
  )
  return data
}

export async function createKnowledgeBaseShareRequest(
  knowledgeBaseId: number,
  payload: CreateKnowledgeBaseShareRequestPayload,
) {
  const { data } = await http.post(`/api/knowledge-bases/${knowledgeBaseId}/share-requests`, payload)
  return data
}

export async function fetchMyKnowledgeBaseShareRequests(): Promise<KnowledgeBaseShareRequestListResponse> {
  const { data } = await http.get<KnowledgeBaseShareRequestListResponse>(
    '/api/knowledge-bases/share-requests/my',
  )
  return data
}

export async function fetchPendingKnowledgeBaseShareRequests(): Promise<KnowledgeBaseShareRequestListResponse> {
  const { data } = await http.get<KnowledgeBaseShareRequestListResponse>(
    '/api/knowledge-bases/share-requests/pending',
  )
  return data
}

export async function approveKnowledgeBaseShareRequest(
  requestId: number,
  payload: ShareDecisionPayload,
) {
  const { data } = await http.post(`/api/knowledge-bases/share-requests/${requestId}/approve`, payload)
  return data
}

export async function rejectKnowledgeBaseShareRequest(
  requestId: number,
  payload: ShareDecisionPayload,
) {
  const { data } = await http.post(`/api/knowledge-bases/share-requests/${requestId}/reject`, payload)
  return data
}

export async function fetchKnowledgeDocuments(params?: {
  knowledge_base_id?: number
  department_id?: number
}): Promise<KnowledgeDocumentListResponse> {
  const { data } = await http.get<KnowledgeDocumentListResponse>('/api/documents', {
    params,
  })
  return data
}

export async function uploadKnowledgeDocument(
  payload: UploadKnowledgeDocumentPayload,
): Promise<UploadKnowledgeDocumentResponse> {
  const formData = new FormData()
  formData.append('knowledge_base_id', String(payload.knowledge_base_id))
  formData.append('visibility_scope', payload.visibility_scope)
  formData.append('file', payload.file)

  const { data } = await http.post<UploadKnowledgeDocumentResponse>('/api/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return data
}
