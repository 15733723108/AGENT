import request from '@/api/request'
import type { LoginRequest, UserInfo } from '@/types'

export function login(data: LoginRequest) {
  return request.post<{ access_token: string; token_type: string; user: UserInfo }>('/auth/login', data)
}

export interface RegisterRequest {
  username: string
  password: string
  display_name: string
  role: 'teacher' | 'student'
}

export interface RegisterResult {
  access_token?: string | null
  token_type?: string
  user?: UserInfo | null
  message?: string
  pending?: boolean
}

export function register(data: RegisterRequest) {
  return request.post<RegisterResult>('/auth/register', data)
}

export interface PendingTeacher {
  id: number
  username: string
  display_name: string
  phone: string
  created_at?: string
}

export function listPendingTeachers() {
  return request.get<PendingTeacher[]>('/auth/pending-teachers')
}

export function approveTeacher(userId: number) {
  return request.post<{ user_id: number; message: string }>(`/auth/teachers/${userId}/approve`)
}

export function rejectTeacher(userId: number) {
  return request.post<{ user_id: number; message: string }>(`/auth/teachers/${userId}/reject`)
}

export function getProfile() {
  return request.get<UserInfo>('/auth/me')
}
