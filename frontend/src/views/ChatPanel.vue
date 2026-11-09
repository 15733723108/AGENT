<template>
  <div class="chat-panel">
    <div class="chat-toolbar">
      <el-popover
        v-model:visible="historyVisible"
        placement="bottom-start"
        :width="320"
        trigger="click"
        @show="loadSessionList"
      >
        <template #reference>
          <button class="tool-btn" type="button" :disabled="busy">历史会话</button>
        </template>
        <div class="history-panel">
          <StateBlock v-if="historyState === 'loading'" state="loading" :skeleton-rows="4" compact />
          <StateBlock
            v-else-if="historyState === 'error'"
            state="error"
            title="历史会话加载失败"
            description="服务暂时不可用，可重试；也可以直接新建会话继续提问。"
            retry-text="重试"
            compact
            @retry="loadSessionList"
          />
          <StateBlock
            v-else-if="!historyList.length"
            state="empty"
            title="暂无历史会话"
            description="发起一次提问后，会话会自动保存在这里。"
            compact
          />
          <template v-else>
            <div
              v-for="s in historyList"
              :key="s.id"
              class="history-item"
              :class="{ on: s.id === sessionId }"
            >
              <button
                type="button"
                class="hi-main"
                :aria-current="s.id === sessionId ? 'true' : undefined"
                @click="switchSession(s.id)"
              >
                <span class="hi-title">{{ s.title || '新会话' }}</span>
                <span class="hi-time">{{ formatTime(s.updated_at || s.created_at) }}</span>
              </button>
              <button
                type="button"
                class="hi-del"
                :aria-label="`删除会话：${s.title || '新会话'}`"
                @click.stop="removeSession(s.id)"
              >
                <el-icon :size="14"><Delete /></el-icon>
              </button>
            </div>
          </template>
        </div>
      </el-popover>

      <button class="tool-btn" type="button" @click="newSession" :disabled="busy">新建会话</button>
      <button
        v-if="showRefs && currentRefs.length"
        class="tool-btn muted"
        type="button"
        :aria-expanded="refsVisible"
        @click="refsVisible = !refsVisible"
      >
        引用来源 ({{ currentRefs.length }})
      </button>
    </div>

    <div
      ref="scrollRef"
      class="chat-scroll"
      role="log"
      aria-label="对话记录"
      aria-live="polite"
      aria-relevant="additions text"
      :aria-busy="busy"
    >
      <div class="chat-inner">
        <div v-if="initError" class="init-error" role="alert">
          <el-icon :size="15"><WarningFilled /></el-icon>
          <span>历史会话加载失败，仍可继续提问。</span>
          <button type="button" class="init-retry" @click="retryInit">重试</button>
        </div>
        <div v-if="!messages.length && !busy" class="chat-empty">
          <template v-if="isGeneral">
            <svg viewBox="0 0 176 70" class="empty-svg" fill="none" aria-hidden="true">
              <path d="M88 6V22M28 57V42Q28 32 38 32H138Q148 32 148 42V57M88 32V57" stroke="currentColor" stroke-width="1.5" />
              <circle cx="28" cy="60" r="5" fill="#ffffff" stroke="#e7eaf0" stroke-width="2" />
              <circle cx="88" cy="60" r="5" fill="#ffffff" stroke="#e7eaf0" stroke-width="2" />
              <circle cx="148" cy="60" r="5" fill="#ffffff" stroke="#e7eaf0" stroke-width="2" />
              <circle cx="88" cy="7" r="6" fill="#2f5bd8" />
            </svg>
            <p class="empty-title">我是劝学路小学智能体</p>
            <p class="empty-sub">可以陪你多轮对话、学习辅导、知识答疑；遇到问题会先给出多种解题思路，再帮你聚焦最优路径。</p>
          </template>
          <template v-else>
            <el-icon :size="40" color="#c3cad5"><ChatDotRound /></el-icon>
            <p class="empty-title">我是学校信息小助手</p>
            <p class="empty-sub">可以回答招生政策、作息时间、规章制度、通知公告等问题，并为你标注知识库引用来源。</p>
          </template>
        </div>

        <template v-for="(m, i) in messages" :key="i">
          <!-- 用户消息：右侧气泡 -->
          <div v-if="m.role === 'user'" class="turn user-turn">
            <div class="user-bubble">{{ m.content }}</div>
            <span class="avatar avatar-user"><el-icon :size="16"><User /></el-icon></span>
          </div>

          <!-- 助手回答 -->
          <div v-else class="turn assistant-turn">
            <span class="avatar avatar-assistant"><el-icon :size="16"><School /></el-icon></span>
            <div class="assistant-main">
            <!-- 首包到达前的等待反馈：避免「点了发送却没有任何动静」 -->
            <div v-if="showPending(m, i)" class="pending-row" role="status">
              <span class="pending-dots" aria-hidden="true"><i></i><i></i><i></i></span>
              <span>{{ pendingText }}</span>
              <button type="button" class="pending-stop" @click="stop">停止</button>
            </div>

            <!-- 通用问答：分支推理 -->
            <template v-if="isGeneral">
              <div v-if="m.branches && m.branches.length" class="branch-heading">
                <el-icon
                  v-if="chosenBranch(m) && phase !== 'branching'"
                  class="bh-check"
                  :size="14"
                ><Check /></el-icon>
                <el-icon v-else class="bh-icon" :size="14"><Connection /></el-icon>
                <span class="bh-text" :class="{ shimmer: phase === 'branching' }">{{ branchHeading(m) }}</span>
              </div>

              <div
                v-if="m.branches && m.branches.length"
                class="branch-deck"
                :class="{ collapsed: !isOpen(m) }"
              >
                <div class="branch-fan">
                  <div
                    v-for="(b, idx) in m.branches"
                    :key="b.id"
                    class="branch-card"
                    :class="{
                      chosen: b.id === m.chosenId,
                      folded: !isOpen(m) && b.id !== m.chosenId,
                    }"
                    :style="{ transform: `rotate(${isOpen(m) ? angleFor(idx, m.branches.length) : 0}deg)` }"
                  >
                    <div class="bc-top">
                      <span class="bc-label">{{ b.id === m.chosenId ? '已选思路' : '思路 0' + (idx + 1) }}</span>
                      <el-icon v-if="b.id === m.chosenId" :size="12"><Check /></el-icon>
                    </div>
                    <div class="bc-title">{{ b.title }}</div>
                    <div class="bc-note">{{ b.note }}</div>
                    <div class="bc-score">
                      <div class="bc-bar">
                        <div class="bc-fill" :style="{ width: (b.score ?? 0) + '%' }"></div>
                      </div>
                      <span class="bc-num">{{ b.score == null ? '—' : b.score }}</span>
                    </div>
                  </div>
                </div>

                <button
                  v-if="m.branches.length > 1 && m.chosenId && phase !== 'branching'"
                  type="button"
                  class="branch-toggle"
                  @click="expanded = !expanded"
                >
                  <el-icon :size="12" :class="{ rot: expanded }"><CaretBottom /></el-icon>
                  <span v-if="expanded">收起其他思路</span>
                  <span v-else>另外 {{ m.branches.length - 1 }} 种思路</span>
                </button>
              </div>

              <div v-if="m.content" class="answer markdown" v-html="renderMd(m.content)"></div>
              <span
                v-if="i === messages.length - 1 && phase === 'answering'"
                class="cursor"
                aria-hidden="true"
              ></span>
            </template>

            <!-- 学校信息问答：思考态 + 引用来源 -->
            <template v-else>
              <div
                v-if="i === messages.length - 1 && phase === 'thinking' && think"
                class="think-bar"
              >
                <el-icon class="think-icon"><MagicStick /></el-icon>
                <span>正在思考</span>
                <span class="secs">{{ elapsed }}s</span>
              </div>

              <div class="answer markdown" v-html="renderMd(m.content)"></div>
              <span
                v-if="i === messages.length - 1 && phase === 'answering'"
                class="cursor"
                aria-hidden="true"
              ></span>

              <div v-if="showRefs && refsVisible && m.refs && m.refs.length" class="refs">
                <div class="refs-title">引用来源</div>
                <div v-for="(r, ri) in m.refs" :key="ri" class="ref-item">
                  [{{ r.category || '知识库' }}] {{ r.doc_name || '文档' }}（第 {{ r.chunk_index || '-' }} 块）
                </div>
              </div>
            </template>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div class="composer">
      <textarea
        ref="textareaRef"
        v-model="question"
        aria-label="输入您的问题"
        :placeholder="busy ? '继续追问…' : '请输入您的问题，Enter 发送，Shift+Enter 换行'"
        rows="2"
        @keydown.enter.exact.prevent="send"
      ></textarea>
      <div class="composer-actions">
        <span v-if="isGeneral" class="explore-label">
          <el-icon :size="13"><Connection /></el-icon>
          <span>探索思路</span>
        </span>
        <button
          v-else
          type="button"
          class="think-btn"
          :class="{ on: think }"
          :aria-pressed="think"
          @click="think = !think"
        >
          <el-icon :size="14"><MagicStick /></el-icon>
          <span>Think</span>
          <el-icon v-if="think" :size="12"><Check /></el-icon>
        </button>

        <button
          type="button"
          class="send-btn"
          :disabled="busy ? false : !question.trim()"
          :aria-label="busy ? '停止' : '发送'"
          @click="busy ? stop() : send()"
        >
          <el-icon v-if="!busy" :size="16"><ArrowUp /></el-icon>
          <el-icon v-else :size="14"><VideoPause /></el-icon>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowUp,
  CaretBottom,
  ChatDotRound,
  Check,
  Connection,
  Delete,
  MagicStick,
  School,
  User,
  VideoPause,
  WarningFilled,
} from '@element-plus/icons-vue'
import { marked } from 'marked'
import StateBlock from '@/components/StateBlock.vue'
import {
  createSchoolSession,
  createSession,
  deleteSchoolSession,
  deleteSession,
  getHistory,
  getSchoolHistory,
  listSchoolSessions,
  listSessions,
  streamChat,
  streamSchoolChat,
} from '@/api/modules/chat'
import type { ChatMessage, ReasoningBranch, SessionInfo, SSEEvent } from '@/types'

const props = defineProps<{ module: 'general' | 'school_info' }>()
const showRefs = computed(() => props.module === 'school_info')
const isGeneral = computed(() => props.module === 'general')

const GREETINGS: Record<'general' | 'school_info', string> = {
  general:
    '你好，我是劝学路小学智能体，可以陪你多轮对话、学习辅导、知识答疑。遇到问题，我会先给出多种解题思路，再帮你聚焦最优路径。',
  school_info:
    '你好，我是学校信息小助手，可以帮你解答招生政策、作息时间、规章制度、通知公告等问题，并为答案标注知识库引用来源。',
}
const greeting = computed(() => GREETINGS[props.module])

const messages = ref<ChatMessage[]>([])
const question = ref('')
const busy = ref(false)
const phase = ref<'idle' | 'branching' | 'choosing' | 'thinking' | 'answering' | 'done'>('idle')
const think = ref(true)
const elapsed = ref(0)
const expanded = ref(false)
const sessionId = ref<number | null>(null)
const currentRefs = ref<any[]>([])
const refsVisible = ref(true)
const historyList = ref<SessionInfo[]>([])
const historyVisible = ref(false)
const historyState = ref<'loading' | 'ready' | 'error'>('loading')
const initError = ref(false)
const scrollRef = ref<HTMLElement>()
const textareaRef = ref<HTMLTextAreaElement>()

// 等待反馈：首包（branches / refs / token）到达前显示，避免界面「无响应」
const pendingText = computed(() => {
  if (isGeneral.value) return '正在梳理几种解题思路…'
  return phase.value === 'thinking' ? '正在检索知识库…' : '正在生成回答…'
})

function showPending(m: ChatMessage, i: number): boolean {
  if (i !== messages.value.length - 1 || !busy.value || m.role !== 'assistant') return false
  if (m.content) return false
  // 通用问答：分支卡片出现后由卡片自身承接反馈
  if (isGeneral.value) return !m.branches?.length
  // 学校信息问答：开启 Think 时已有思考条，不重复显示
  return !think.value || phase.value !== 'thinking'
}

let timer: number | null = null
let controller: AbortController | null = null

function renderMd(text: string): string {
  return marked.parse(text || '') as string
}

function chosenBranch(m: ChatMessage): ReasoningBranch | undefined {
  if (!m.branches?.length || !m.chosenId) return undefined
  return m.branches.find((b) => b.id === m.chosenId)
}

function isOpen(m: ChatMessage): boolean {
  if (!m.branches?.length) return false
  return phase.value === 'branching' || !m.chosenId || expanded.value
}

function branchHeading(m: ChatMessage): string {
  const n = m.branches?.length || 0
  const chosen = chosenBranch(m)
  if (chosen && phase.value !== 'branching') return `已选定：${chosen.title}`
  if (phase.value === 'done') return '已评估的思路'
  if (n > 0) return `正在考虑 ${n} 种思路`
  return '正在寻找几种思路'
}

function angleFor(idx: number, total: number): number {
  const cols = Math.min(total, 3)
  const column = idx % 3
  return (column - (cols - 1) / 2) * 4
}

function startTimer() {
  elapsed.value = 0
  timer = window.setInterval(() => {
    elapsed.value += 1
  }, 1000)
}

function stopTimer() {
  if (timer !== null) {
    window.clearInterval(timer)
    timer = null
  }
}

function scrollBottom() {
  nextTick(() => {
    if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  })
}

async function ensureSession() {
  if (sessionId.value) return
  const resp = props.module === 'school_info' ? await createSchoolSession() : await createSession(props.module)
  sessionId.value = resp.id
}

async function loadHistory() {
  if (!sessionId.value) return
  const resp = props.module === 'school_info' ? await getSchoolHistory(sessionId.value) : await getHistory(sessionId.value)
  messages.value = resp.messages.map((m: any) => ({ role: m.role, content: m.content, refs: m.refs }))
  scrollBottom()
}

async function newSession() {
  if (busy.value) return
  sessionId.value = null
  messages.value = []
  currentRefs.value = []
  expanded.value = false
  seedGreeting()
}

function seedGreeting() {
  messages.value = [{ role: 'assistant', content: greeting.value }]
}

async function loadSessionList() {
  historyState.value = 'loading'
  try {
    const api = props.module === 'school_info' ? listSchoolSessions : listSessions
    historyList.value = (await api()) as unknown as SessionInfo[]
    historyState.value = 'ready'
    initError.value = false
  } catch {
    // 全局拦截器已弹出错误提示，这里只记录状态供面板/横幅渲染重试入口
    historyState.value = 'error'
  }
}

async function retryInit() {
  await loadSessionList()
  if (historyState.value === 'ready' && !sessionId.value && historyList.value.length) {
    sessionId.value = historyList.value[0].id
    await loadHistory()
  }
}

async function switchSession(id: number) {
  if (busy.value) return
  historyVisible.value = false
  if (id === sessionId.value) return
  sessionId.value = id
  messages.value = []
  currentRefs.value = []
  await loadHistory()
}

async function removeSession(id: number) {
  if (busy.value) return
  try {
    await ElMessageBox.confirm('删除后将无法恢复，确认删除该会话？', '删除会话', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  const api = props.module === 'school_info' ? deleteSchoolSession : deleteSession
  await api(id)
  historyList.value = historyList.value.filter((s) => s.id !== id)
  if (sessionId.value === id) {
    sessionId.value = null
    messages.value = []
    currentRefs.value = []
    await ensureSession()
    seedGreeting()
  }
  ElMessage.success('已删除')
}

function formatTime(s?: string): string {
  if (!s) return ''
  const d = new Date(s.replace(' ', 'T'))
  if (isNaN(d.getTime())) return s
  const diff = Date.now() - d.getTime()
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const hour = Math.floor(min / 60)
  if (hour < 24) return `${hour} 小时前`
  const day = Math.floor(hour / 24)
  if (day < 7) return `${day} 天前`
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function send() {
  const q = question.value.trim()
  if (!q || busy.value) return
  question.value = ''
  busy.value = true
  phase.value = isGeneral.value ? 'branching' : 'thinking'
  expanded.value = false
  startTimer()
  currentRefs.value = []
  controller = new AbortController()

  try {
    await ensureSession()
    messages.value.push({ role: 'user', content: q })
    const answer: ChatMessage = { role: 'assistant', content: '', branches: [], chosenId: undefined }
    messages.value.push(answer)
    const aidx = messages.value.length - 1
    let firstToken = false

    const onEvent = (ev: SSEEvent) => {
      if (ev.event === 'branches') {
        const data = ev.data as { branches: ReasoningBranch[] }
        messages.value[aidx].branches = data.branches || []
        phase.value = 'branching'
        scrollBottom()
      } else if (ev.event === 'chosen') {
        const data = ev.data as { id: string }
        messages.value[aidx].chosenId = data.id
        const list = messages.value[aidx].branches
        if (list) {
          messages.value[aidx].branches = list.map((b) => ({ ...b, chosen: b.id === data.id }))
        }
        phase.value = 'choosing'
        scrollBottom()
      } else if (ev.event === 'token') {
        if (!firstToken) {
          firstToken = true
          phase.value = 'answering'
          stopTimer()
        }
        const data = ev.data as { text: string }
        messages.value[aidx].content += data.text || ''
        scrollBottom()
      } else if (ev.event === 'refs') {
        messages.value[aidx].refs = ev.data as any[]
        currentRefs.value = messages.value[aidx].refs || []
      } else if (ev.event === 'done') {
        phase.value = 'done'
      } else if (ev.event === 'error') {
        const data = ev.data as { message: string }
        ElMessage.error(data.message || '生成失败')
        if (!messages.value[aidx].content) messages.value[aidx].content = '（生成失败）'
      }
    }

    if (props.module === 'school_info') {
      await streamSchoolChat(sessionId.value!, q, onEvent, controller.signal)
    } else {
      await streamChat(sessionId.value!, q, onEvent, controller.signal)
    }
    phase.value = 'done'
    scrollBottom()
  } catch (e: any) {
    if (e?.name === 'AbortError') {
      const last = messages.value[messages.value.length - 1]
      if (last?.role === 'assistant' && !last.content) last.content = '（已停止）'
    } else {
      ElMessage.error(e.message || '请求失败')
      const last = messages.value[messages.value.length - 1]
      if (last?.role === 'assistant' && !last.content) messages.value.pop()
    }
  } finally {
    stopTimer()
    busy.value = false
    controller = null
  }
}

function stop() {
  controller?.abort()
}

onMounted(async () => {
  // 懒加载：进入模块时读取历史会话，若有则载入最近一条，否则显示开局提示词（不创建占位会话）
  await loadSessionList()
  if (historyState.value === 'error') {
    initError.value = true
    seedGreeting()
    return
  }
  if (historyList.value.length) {
    sessionId.value = historyList.value[0].id
    await loadHistory()
  } else {
    seedGreeting()
  }
})

onUnmounted(() => {
  stopTimer()
  controller?.abort()
})
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  /* 与 MainLayout 共用同一组变量：header 高度 + content 上下 padding */
  height: calc(100dvh - var(--app-header-h) - var(--app-gutter) * 2);
  background: #ffffff;
}

.chat-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0 10px;
  border-bottom: 1px solid #e7eaf0;
}
.tool-btn {
  padding: 5px 12px;
  font-size: 13px;
  color: #15181f;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 150ms ease;
}
.tool-btn:hover {
  background: #f2f4f7;
}
.tool-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.tool-btn.muted {
  color: #5b6472;
}
.chat-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px 0;
}
.chat-inner {
  width: 100%;
  max-width: 860px;
  margin: 0 auto;
  padding: 0 var(--space-2);
  box-sizing: border-box;
}

.chat-empty {
  text-align: center;
  color: #98a1b0;
  padding-top: 120px;
}
.chat-empty p {
  margin-top: 12px;
  font-size: 13px;
}
.empty-svg {
  width: 176px;
  height: 70px;
  color: #98a1b0;
}
.empty-title {
  font-size: 16px;
  font-weight: 500;
  color: #15181f;
  margin-top: 20px !important;
}
.empty-sub {
  color: #98a1b0;
  font-size: 12px;
  margin-top: 6px !important;
}

.turn {
  margin-bottom: 20px;
}

.user-turn {
  display: flex;
  justify-content: flex-end;
  align-items: flex-start;
  gap: 8px;
}
.user-bubble {
  max-width: calc(100% - 40px);
  padding: 9px 14px;
  background: #eef2fd;
  border-radius: 10px 10px 4px 10px;
  font-size: 14px;
  line-height: 1.6;
  color: #15181f;
  white-space: pre-wrap;
  word-break: break-word;
}

.assistant-turn {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 14px;
  line-height: 1.75;
  color: #15181f;
}
.avatar {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #ffffff;
}
.avatar-assistant {
  background: linear-gradient(135deg, #2f5bd8, #0e8f76);
  box-shadow: 0 2px 6px rgba(47, 91, 216, 0.28);
}
.avatar-user {
  background: #e9edf3;
  color: #5b6472;
}
.assistant-main {
  flex: 1;
  min-width: 0;
}

/* 分支推理：标题 */
.branch-heading {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  font-size: 12px;
  color: #98a1b0;
}
.bh-icon {
  color: #98a1b0;
}
.bh-check {
  color: #0e8f76;
}
.bh-text {
  font-weight: 500;
}
.bh-text.shimmer {
  animation: pixelShimmer 1.5s ease-in-out infinite;
}
@keyframes pixelShimmer {
  0%, 100% {
    opacity: 0.35;
  }
  50% {
    opacity: 1;
  }
}

/* 分支推理：卡片 */
.branch-deck {
  margin: 0 0 6px;
}
.branch-fan {
  display: flex;
  gap: 10px;
  align-items: stretch;
}
.branch-card {
  display: flex;
  flex-direction: column;
  width: 0;
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid #e7eaf0;
  border-radius: 8px;
  background: #ffffff;
  transform-origin: top left;
  transition: border-color 150ms ease, background-color 150ms ease;
}
.branch-card.chosen {
  border-color: rgba(47, 91, 216, 0.55);
  background: rgba(47, 91, 216, 0.05);
}
.branch-card.folded {
  display: none;
}
.branch-deck.collapsed .branch-card.chosen {
  flex: none;
  width: 100%;
  max-width: 560px;
}
.bc-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #98a1b0;
}
.branch-card.chosen .bc-top {
  color: #0e8f76;
}
.bc-title {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.3;
  color: #15181f;
  word-break: break-word;
}
.bc-note {
  margin-top: 6px;
  font-size: 11px;
  line-height: 1.4;
  color: #98a1b0;
  word-break: break-word;
  flex: 1;
}
.bc-score {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}
.bc-bar {
  flex: 1;
  height: 4px;
  background: #f2f4f7;
  border-radius: 999px;
  overflow: hidden;
}
.bc-fill {
  height: 100%;
  background: #2f5bd8;
  border-radius: 999px;
  transition: width 180ms linear;
}
.branch-card.chosen .bc-fill {
  background: #0e8f76;
}
.bc-num {
  width: 20px;
  text-align: right;
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  color: #98a1b0;
}
.branch-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  padding: 2px 6px;
  font-size: 11px;
  color: #98a1b0;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: color 150ms ease;
}
.branch-toggle:hover {
  color: #15181f;
}
.branch-toggle .rot {
  transform: rotate(180deg);
}

/* 学校信息：思考态 */
.think-bar {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 10px;
  font-size: 12px;
  color: #98a1b0;
}
.think-icon {
  color: #98a1b0;
}
.secs {
  margin-left: auto;
  font-variant-numeric: tabular-nums;
  color: #c3cad5;
}

.markdown :deep(p) {
  margin: 6px 0;
}
.markdown :deep(pre) {
  background: #f5f7fa;
  color: #15181f;
  border: 1px solid #e7eaf0;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}
.markdown :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 13px;
}

.cursor {
  display: inline-block;
  width: 4px;
  height: 18px;
  margin-left: 3px;
  background: #15181f;
  border-radius: 1px;
  vertical-align: -3px;
  animation: blink 1s steps(2) infinite;
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}

.refs {
  margin-top: 10px;
  padding: 8px 12px;
  background: #f5f7fa;
  border: 1px solid #e7eaf0;
  border-radius: 6px;
  font-size: 12px;
  color: #5b6472;
}
.refs-title {
  font-weight: 600;
  margin-bottom: 4px;
  color: #15181f;
}
.ref-item {
  margin-top: 2px;
  line-height: 1.6;
}

.composer {
  flex-shrink: 0;
  width: 100%;
  max-width: 860px;
  margin: 0 auto;
  background: #ffffff;
  border: 1px solid #e7eaf0;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  padding: 12px 12px 10px;
  transition: border-color var(--dur-fast) ease, box-shadow var(--dur-fast) ease;
}
/* textarea 自身 outline:none，用容器焦点环补足键盘可见性 */
.composer:focus-within {
  border-color: var(--notion-blue);
  box-shadow: 0 0 0 2px rgba(47, 91, 216, 0.18);
}
.composer textarea {
  display: block;
  width: 100%;
  min-height: 64px;
  max-height: 140px;
  resize: none;
  border: none;
  outline: none;
  background: transparent;
  padding: 2px;
  font-size: 15px;
  line-height: 1.6;
  color: #15181f;
  box-sizing: border-box;
}
.composer textarea::placeholder {
  color: #98a1b0;
}
.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.explore-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #98a1b0;
}

.think-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 500;
  color: #5b6472;
  background: transparent;
  border: 1px solid #e7eaf0;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 150ms ease, border-color 150ms ease, color 150ms ease;
}
.think-btn:hover {
  background: #f2f4f7;
}
.think-btn.on {
  color: #15181f;
  border-color: rgba(47, 91, 216, 0.35);
  background: rgba(47, 91, 216, 0.06);
}

.send-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  color: #ffffff;
  background: #15181f;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 150ms ease, opacity 150ms ease;
}
.send-btn:hover {
  background: #0f141d;
}
.send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* ============ 初始化失败横幅 ============ */
.init-error {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  padding: 8px 12px;
  font-size: 12px;
  color: var(--notion-text-secondary);
  background: var(--el-color-danger-light-9);
  border: 1px solid var(--el-color-danger-light-7);
  border-radius: var(--radius-sm);
}
.init-error .el-icon {
  flex-shrink: 0;
  color: var(--notion-red);
}
.init-retry {
  margin-left: auto;
  padding: 2px 6px;
  font: inherit;
  color: var(--notion-blue);
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* ============ 首包等待态 ============ */
.pending-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
  font-size: 12px;
  color: var(--notion-text-muted);
}
.pending-dots {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.pending-dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--notion-blue);
  animation: pending-bounce 1.1s ease-in-out infinite;
}
.pending-dots i:nth-child(2) { animation-delay: 0.15s; }
.pending-dots i:nth-child(3) { animation-delay: 0.3s; }
@keyframes pending-bounce {
  0%, 70%, 100% { opacity: 0.3; transform: translateY(0); }
  35% { opacity: 1; transform: translateY(-3px); }
}
.pending-stop {
  padding: 2px 6px;
  font: inherit;
  color: var(--notion-text-secondary);
  background: transparent;
  border: 1px solid var(--notion-border);
  border-radius: 4px;
  cursor: pointer;
}
.pending-stop:hover {
  background: var(--notion-hover);
}

/* ============ 窄屏适配 ============ */
@media (max-width: 768px) {
  .chat-scroll {
    padding: 12px 0;
  }
  .chat-toolbar {
    flex-wrap: wrap;
    gap: 4px;
  }
  .tool-btn {
    padding: 5px 8px;
  }
  .chat-empty {
    padding-top: 56px;
  }
  .empty-svg {
    width: 140px;
    height: 56px;
  }
  .user-bubble {
    max-width: calc(100% - 38px);
  }
  .branch-fan {
    overflow-x: auto;
    padding-bottom: 6px;
  }
  .branch-card {
    min-width: 170px;
  }
  .composer {
    padding: 10px 10px 8px;
  }
  .explore-label {
    display: none;
  }
}
</style>

<style>
/* 历史会话面板：随 popover 渲染到 body，需全局样式 */
.history-panel {
  max-height: 320px;
  overflow-y: auto;
  margin: -4px 0;
}
.history-empty {
  padding: 16px 0;
  margin: 0;
  text-align: center;
  font-size: 12px;
  color: #98a1b0;
}
.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 150ms ease;
}
.history-item:hover {
  background: #f5f7fa;
}
.history-item.on {
  background: #f2f4f7;
}
/* 会话条目改为两个并列的原生 button，键盘可聚焦、无嵌套交互元素 */
.hi-main {
  flex: 1;
  min-width: 0;
  display: block;
  padding: 0;
  font: inherit;
  text-align: left;
  background: transparent;
  border: none;
  cursor: pointer;
}
.hi-title {
  display: block;
  font-size: 13px;
  color: #15181f;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hi-time {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: #98a1b0;
}
.hi-del {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  color: #98a1b0;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: color 150ms ease, background-color 150ms ease;
}
.hi-del:hover {
  color: #eb5757;
  background: var(--el-color-danger-light-9);
}
</style>