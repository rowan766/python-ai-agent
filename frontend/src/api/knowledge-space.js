import request from '../utils/request'

export const getKnowledgeSpaceList = (params) => {
  return request.get('/knowledge-space', { params })
}

export const getKnowledgeSpaceDetail = (id) => {
  return request.get(`/knowledge-space/${id}`)
}

export const createKnowledgeSpace = (data) => {
  return request.post('/knowledge-space', data)
}

export const updateKnowledgeSpace = (id, data) => {
  return request.put(`/knowledge-space/${id}`, data)
}

export const saveKnowledgeSpaceMember = (spaceId, data) => {
  return request.post(`/knowledge-space/${spaceId}/members`, data)
}

export const deleteKnowledgeSpaceMember = (spaceId, memberId) => {
  return request.delete(`/knowledge-space/${spaceId}/members/${memberId}`)
}

export const saveKnowledgeSpaceShare = (spaceId, data) => {
  return request.post(`/knowledge-space/${spaceId}/shares`, data)
}

export const deleteKnowledgeSpaceShare = (spaceId, shareId) => {
  return request.delete(`/knowledge-space/${spaceId}/shares/${shareId}`)
}
