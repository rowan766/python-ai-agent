import { buildApiUrl, http } from '@/api/http'
import { clearAccessToken, getAccessToken } from '@/utils/storage'
import type {
  ChatStreamPayload,
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

export async function streamChat(
  payload: ChatStreamPayload,
  options?: {
    signal?: AbortSignal
    onChunk?: (chunk: string) => void
  },
): Promise<string> {
  const token = getAccessToken()
  const response = await fetch(buildApiUrl('/api/chat'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      ...payload,
      stream: true,
    }),
    signal: options?.signal,
  })

  if (!response.ok || !response.body) {
    let detail = ''
    try {
      const data = await response.json()
      detail = typeof data?.detail === 'string' ? data.detail : ''
    } catch {
      detail = ''
    }

    if (response.status === 401) {
      clearAccessToken()
      throw new Error(detail || '登录状态已失效，请重新登录。')
    }

    if (response.status === 403) {
      throw new Error(detail || '当前账号没有访问聊天接口的权限。')
    }

    throw new Error(detail || `聊天请求失败：${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let finalText = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''

    for (const event of events) {
      const line = event
        .split('\n')
        .find((item) => item.startsWith('data: '))
      if (!line) {
        continue
      }

      const raw = line.slice(6).trim()
      if (raw === '[DONE]') {
        return finalText
      }

      const parsed = JSON.parse(raw) as { content?: string }
      const chunk = parsed.content ?? ''
      if (!chunk) {
        continue
      }

      finalText += chunk
      options?.onChunk?.(chunk)
    }
  }

  return finalText
}
