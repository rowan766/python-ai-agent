export interface UploadResponse {
  status: string
  filename: string
  chunks: number
  message: string
}

export interface SearchResult {
  content: string
  score: number
  metadata: Record<string, unknown>
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  count: number
}

export interface SupportedFormatsResponse {
  supported_formats: string[]
}

export interface ModelHealthResponse {
  status: 'ok' | 'error'
  embedding_model?: string
  chat_model?: string
  base_url: string
  sample_text?: string
  prompt?: string
  dimensions?: number
  vector_preview?: number[]
  response_preview?: string
  error?: string
}
