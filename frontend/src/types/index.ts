// 通用类型定义

export interface LoginRequest {
  username: string
  password: string
}

export interface UserInfo {
  id: number
  username: string
  display_name: string
  role: 'admin' | 'teacher' | 'student' | 'parent'
  phone?: string
}

export interface SessionInfo {
  id: number
  module: string
  title: string
  created_at?: string
  updated_at?: string
}

export interface ChatMessage {
  id?: number
  role: 'user' | 'assistant'
  content: string
  refs?: RefItem[] | null
  created_at?: string
  branches?: ReasoningBranch[]
  chosenId?: string
}

export interface ReasoningBranch {
  id: string
  title: string
  note: string
  score?: number
  chosen?: boolean
}

export interface RefItem {
  doc_name?: string
  category?: string
  chunk_index?: number
  content?: string
  score?: number
}

// SSE 事件
export interface SSEEvent {
  event: string
  data: unknown
}

export interface LessonPlan {
  id: number
  subject: string
  grade: string
  topic: string
  class_hours: number
  course_type: string
  content_json: Record<string, unknown>
  created_at?: string
}

export interface ExamItem {
  id: number
  exam_name: string
  subject: string
  grade: string
  source_file: string
  question_count: number
  status: 'pending' | 'analyzing' | 'done' | 'failed'
  error_msg?: string
  created_at?: string
}

export interface ExamQuestion {
  question_no: number
  question_type: string
  question_text: string
  answer?: string
  analysis?: string
  knowledge_points?: string[]
  difficulty?: number
  score?: number
}
