import request from '@/api/request'

export interface KbDocument {
  id: number
  doc_name: string
  category: string
  file_type: string
  file_path: string
  chunk_count: number
  is_active: boolean
  created_at?: string
}

export function listDocuments(params: { category?: string; active_only?: boolean; limit?: number } = {}) {
  return request.get<KbDocument[]>('/kb/documents', { params })
}

export interface KbDocumentContent {
  doc_id: number
  doc_name: string
  category: string
  file_type: string
  content: string
}

export function getDocumentContent(docId: number) {
  return request.get<KbDocumentContent>(`/kb/documents/${docId}/content`)
}

export function downloadDocument(docId: number) {
  return request.get<Blob>(`/kb/documents/${docId}/download`, { responseType: 'blob' })
}

export function uploadDocument(file: File, category = 'auto') {
  const form = new FormData()
  form.append('file', file)
  form.append('category', category)
  return request.post<{ doc_id: number; doc_name: string; chunk_count: number }>('/kb/upload', form)
}

export function importText(data: { title: string; category: string; content: string }) {
  return request.post<{ doc_id: number; doc_name: string; chunk_count: number }>('/kb/import-text', data)
}

export function libraryUpload(file: File, name: string, category: string) {
  const form = new FormData()
  form.append('file', file)
  form.append('name', name)
  form.append('category', category)
  return request.post<{ doc_id: number; doc_name: string; chunk_count: number }>('/kb/library/upload', form)
}

export function deactivateDocument(docId: number) {
  return request.post<{ doc_id: number }>('/kb/deactivate', { doc_id: docId })
}
