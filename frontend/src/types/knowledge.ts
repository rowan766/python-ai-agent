export interface KnowledgeBaseItem {
  id: number
  department_id: number
  department_name: string
  code: string
  name: string
  description?: string | null
  visibility_scope: string
  status: string
  document_count: number
  created_by: number
  created_at: string
}

export interface KnowledgeBaseListResponse {
  items: KnowledgeBaseItem[]
  count: number
}

export interface CreateKnowledgeBasePayload {
  department_id: number
  code: string
  name: string
  description?: string
  visibility_scope: string
}

export interface KnowledgeDocumentItem {
  id: number
  knowledge_base_id: number
  knowledge_base_name: string
  department_id: number
  department_name: string
  title: string
  filename: string
  file_extension: string
  visibility_scope: string
  status: string
  chunks_count: number
  uploader_user_id: number
  uploader_username: string
  created_at: string
}

export interface KnowledgeDocumentListResponse {
  items: KnowledgeDocumentItem[]
  count: number
}

export interface UploadKnowledgeDocumentPayload {
  knowledge_base_id: number
  visibility_scope: string
  file: File
}

export interface UploadKnowledgeDocumentResponse {
  status: string
  message: string
  document: KnowledgeDocumentItem
}

export interface KnowledgeBaseShareItem {
  id: number
  target_department_id: number
  target_department_name: string
  status: string
  created_at: string
}

export interface KnowledgeBaseShareListResponse {
  items: KnowledgeBaseShareItem[]
  count: number
}

export interface CreateKnowledgeBaseShareRequestPayload {
  target_department_id: number
  reason: string
}

export interface KnowledgeBaseShareRequestItem {
  id: number
  knowledge_base_id: number
  knowledge_base_name: string
  source_department_id: number
  source_department_name: string
  target_department_id: number
  target_department_name: string
  requested_by: number
  requested_by_username: string
  requested_by_email: string
  reason: string
  status: string
  review_comment?: string | null
  submitted_at: string
  reviewed_at?: string | null
}

export interface KnowledgeBaseShareRequestListResponse {
  items: KnowledgeBaseShareRequestItem[]
  count: number
}

export interface ShareDecisionPayload {
  review_comment?: string
}
