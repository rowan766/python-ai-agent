import request from '../utils/request'

export const getDocumentList = (params) => {
  return request.get('/document', { params })
}

export const getDocumentDetail = (id) => {
  return request.get(`/document/${id}`)
}

export const getDocumentChunks = (id, params) => {
  return request.get(`/document/${id}/chunks`, { params })
}

export const getDocumentQueueStatus = () => {
  return request.get('/document/queue/status')
}

export const reprocessDocument = (id, data = { force: false }) => {
  return request.post(`/document/${id}/reprocess`, data)
}

export const deleteDocument = (id) => {
  return request.delete(`/document/${id}`)
}

export const searchDocumentChunks = (params) => {
  return request.get('/document/search', { params })
}

export const askDocumentQuestion = (data) => {
  return request.post('/document/qa', data, { timeout: 60000 })
}

export const getDocumentQaSessions = () => {
  return request.get('/document/qa/sessions')
}

export const createDocumentQaSession = (data = {}) => {
  return request.post('/document/qa/sessions', data)
}

export const updateDocumentQaSession = (id, data) => {
  return request.put(`/document/qa/sessions/${id}`, data)
}

export const syncDocumentQaSession = (id, data) => {
  return request.put(`/document/qa/sessions/${id}/sync`, data)
}

export const deleteDocumentQaSession = (id) => {
  return request.delete(`/document/qa/sessions/${id}`)
}

export const deleteDocumentQaMessage = (sessionId, messageId) => {
  return request.delete(`/document/qa/sessions/${sessionId}/messages/${messageId}`)
}
