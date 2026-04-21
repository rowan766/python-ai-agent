import request from '../utils/request'

export const uploadImages = (formData) => {
  return request.post('/upload/images', formData, { timeout: 120000 })
}

export const uploadFiles = (formData) => {
  return request.post('/upload/files', formData, { timeout: 120000 })
}

export const downloadFileBlob = (id) => {
  return request.get(`/upload/file/${id}/download`, {
    responseType: 'blob'
  })
}

export const deleteUploadedFile = (id) => {
  return request.delete(`/upload/file/${id}`)
}
