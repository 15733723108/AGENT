import request from '@/api/request'
import { streamSSE } from '@/api/sse'
import type { SSEEvent, SessionInfo } from '@/types'

export function createSession(module: string, title = '') {
  return request.post<SessionInfo>('/chat/sessions', { module, title })
}

export function listSessions() {
  return request.get<SessionInfo[]>('/chat/sessions')
}

export function deleteSession(sessionId: number) {
  return request.delete<{ status: string }>(`/chat/sessions/${sessionId}`)
}

export function getHistory(sessionId: number) {
  return request.get<{ session: SessionInfo; messages: any[] }>(`/chat/sessions/${sessionId}/history`)
}

export async function streamChat(
  sessionId: number,
  question: string,
  onEvent: (ev: SSEEvent) => void,
  signal?: AbortSignal,
) {
  await streamSSE('/api/chat/chat', { session_id: sessionId, question }, onEvent, signal)
}

export function createSchoolSession(title = '') {
  return request.post<SessionInfo>('/school_info/sessions', { module: 'school_info', title })
}

export function listSchoolSessions() {
  return request.get<SessionInfo[]>('/school_info/sessions')
}

export function deleteSchoolSession(sessionId: number) {
  return request.delete<{ status: string }>(`/school_info/sessions/${sessionId}`)
}

export function getSchoolHistory(sessionId: number) {
  return request.get<{ session: SessionInfo; messages: any[] }>(`/school_info/sessions/${sessionId}/history`)
}

export async function streamSchoolChat(
  sessionId: number,
  question: string,
  onEvent: (ev: SSEEvent) => void,
  signal?: AbortSignal,
) {
  await streamSSE('/api/school_info/chat', { session_id: sessionId, question }, onEvent, signal)
}
