import request from '@/api/request'
import type { ExamItem, ExamQuestion } from '@/types'

export interface ExamCreateRequest {
  exam_name: string
  subject: string
  grade: string
}

export function createExam(data: ExamCreateRequest) {
  return request.post<ExamItem>('/exam/create', data)
}

export function createExamWithText(data: ExamCreateRequest & { paper_text: string }) {
  const form = new FormData()
  form.append('exam_name', data.exam_name)
  form.append('subject', data.subject)
  form.append('grade', data.grade)
  form.append('paper_text', data.paper_text)
  return request.post<ExamItem>('/exam/create/with-text', form)
}

export function uploadExam(file: File, meta: ExamCreateRequest) {
  const form = new FormData()
  form.append('file', file)
  form.append('exam_name', meta.exam_name)
  form.append('subject', meta.subject)
  form.append('grade', meta.grade)
  return request.post<ExamItem>('/exam/upload', form)
}

export function listExams(params: { subject?: string; status?: string; limit?: number } = {}) {
  return request.get<ExamItem[]>('/exam/list', { params })
}

export function getExamDetail(id: number) {
  return request.get<{ exam: ExamItem; questions: ExamQuestion[] }>(`/exam/${id}`)
}

export function analyzeExam(id: number) {
  return request.post<ExamItem>(`/exam/${id}/analyze`)
}

export function getExamReport(id: number) {
  return request.get<{ exam_id: number; report_md: string; stats_json?: string; report_file?: string }>(`/exam/${id}/report`)
}

export function exportExamReport(id: number) {
  return request.get<Blob>(`/exam/${id}/report/export`, { responseType: 'blob' })
}

export interface ScoreRow {
  student_name: string
  scores: Record<string, number>
}

export function submitScoreRows(id: number, rows: ScoreRow[]) {
  return request.post(`/exam/${id}/stats`, rows)
}
