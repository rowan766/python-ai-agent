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

export const searchDocumentChunks = (params) => {
  return request.get('/document/search', { params })
}
