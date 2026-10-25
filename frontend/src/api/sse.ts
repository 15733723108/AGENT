import type { SSEEvent } from '@/types'

/**
 * SSE 流式解析：使用 fetch + ReadableStream 逐行解析
 * 后端事件格式：
 *   event: token
 *   data: {"text": "..."}
 *   （空行分隔）
 */
export async function streamSSE(
  url: string,
  body: unknown,
  onEvent: (ev: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const userStore = await import('@/stores/user').then((m) => m.useUserStore())

  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${userStore.token}`,
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(body),
    signal,
  })

  if (!resp.ok || !resp.body) {
    let detail = `HTTP ${resp.status}`
    try {
      const j = await resp.json()
      detail = j.detail || detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // 按空行切分事件块
    let idx: number
    while ((idx = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      const ev = parseBlock(block)
      if (ev) onEvent(ev)
    }
  }
  // 尾部残余块
  if (buffer.trim()) {
    const ev = parseBlock(buffer)
    if (ev) onEvent(ev)
  }
}

function parseBlock(block: string): SSEEvent | null {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of block.split('\n')) {
    const trimmed = line.replace(/\r$/, '')
    if (trimmed.startsWith('event:')) {
      event = trimmed.slice(6).trim()
    } else if (trimmed.startsWith('data:')) {
      dataLines.push(trimmed.slice(5).trim())
    }
  }
  if (!dataLines.length) return null
  try {
    const data = dataLines.length === 1 ? JSON.parse(dataLines[0]) : dataLines.join('\n')
    return { event, data }
  } catch {
    return { event, data: dataLines.join('\n') }
  }
}
