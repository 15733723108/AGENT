import request from '@/api/request'
import type { LessonPlan } from '@/types'

export interface LessonGenerateRequest {
  subject: string
  grade: string
  topic: string
  class_hours?: number
  course_type?: string
  student_profile?: string
  use_textbook_rag?: boolean
}

export function generateLesson(data: LessonGenerateRequest) {
  return request.post<LessonPlan>('/lesson/generate', data)
}

export function listLessons(params: { subject?: string; limit?: number } = {}) {
  return request.get<LessonPlan[]>('/lesson/plans', { params })
}

export function getLesson(id: number) {
  return request.get<LessonPlan>(`/lesson/plans/${id}`)
}

export function exportLesson(id: number, fmt: 'md' | 'docx' = 'md') {
  return request.get<Blob>(`/lesson/plans/${id}/export`, { params: { fmt }, responseType: 'blob' })
}
