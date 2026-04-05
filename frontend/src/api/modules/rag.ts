import { http } from '@/api/http'
import type {
  ModelHealthResponse,
  SearchResponse,
  SupportedFormatsResponse,
  UploadResponse,
} from '@/types/rag'

export async function fetchSupportedFormats(): Promise<SupportedFormatsResponse> {
  const { data } = await http.get<SupportedFormatsResponse>('/api/rag/supported-formats')
  return data
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await http.post<UploadResponse>('/api/rag/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return data
}

export async function queryKnowledge(
  query: string,
  limit: number,
  knowledgeBaseId?: number,
): Promise<SearchResponse> {
  const { data } = await http.post<SearchResponse>('/api/rag/query', null, {
    params: {
      query,
      limit,
      knowledge_base_id: knowledgeBaseId,
    },
  })
  return data
}

export async function fetchEmbeddingHealth(): Promise<ModelHealthResponse> {
  const { data } = await http.get<ModelHealthResponse>('/api/rag/debug/embedding')
  return data
}

export async function fetchChatHealth(): Promise<ModelHealthResponse> {
  const { data } = await http.get<ModelHealthResponse>('/api/rag/debug/chat')
  return data
}
