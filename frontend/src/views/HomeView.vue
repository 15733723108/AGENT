<template>
  <!-- 工作台：面向教师/学生/家长的功能入口，不再展示部署命令 -->
  <div class="home app-page">
    <section class="hero" aria-labelledby="home-title">
      <div class="hero-main">
        <span class="app-eyebrow"><el-icon :size="12"><House /></el-icon>工作台</span>
        <h1 id="home-title" class="hero-title">{{ greeting }}，{{ displayName }}</h1>
        <p class="hero-desc">{{ roleDesc }}</p>
        <div class="hero-actions">
          <el-button type="primary" @click="go('/chat/general')">
            <el-icon style="margin-right: 6px"><ChatDotRound /></el-icon>开始提问
          </el-button>
          <el-button v-if="canTeach" @click="go('/lesson')">生成一份教案</el-button>
        </div>
      </div>

      <aside class="hero-aside" aria-label="今日信息">
        <div class="today-label">今天</div>
        <div class="today-date">{{ todayDate }}</div>
        <div class="today-week">{{ todayWeek }}</div>
        <div class="today-tip">
          <el-icon :size="14"><InfoFilled /></el-icon>
          <span>所有问答均保存在历史会话中，可随时回到上次的讨论。</span>
        </div>
      </aside>
    </section>

    <section class="section" aria-labelledby="entry-title">
      <div class="app-section-head">
        <div>
          <h2 id="entry-title" class="app-section-title">功能入口</h2>
          <p class="app-section-desc">按教学流程组织，选择需要的模块直接进入。</p>
        </div>
        <span class="section-count">{{ visibleCards.length }} 个可用模块</span>
      </div>

      <div class="feature-grid">
        <button
          v-for="card in visibleCards"
          :key="card.path"
          type="button"
          class="feature-card app-card-interactive"
          :aria-label="`进入${card.name}：${card.desc}`"
          @click="go(card.path)"
        >
          <span class="feature-icon" :class="'tone-' + card.tone" aria-hidden="true">
            <el-icon :size="20"><component :is="card.icon" /></el-icon>
          </span>
          <span class="feature-name">{{ card.name }}</span>
          <span class="feature-desc">{{ card.desc }}</span>
          <span class="feature-arrow" aria-hidden="true"><el-icon :size="15"><ArrowRight /></el-icon></span>
        </button>
      </div>
    </section>

    <section class="section" aria-labelledby="guide-title">
      <div class="app-section-head">
        <div>
          <h2 id="guide-title" class="app-section-title">使用指引</h2>
          <p class="app-section-desc">三步走完一次完整的备课与答疑流程。</p>
        </div>
      </div>

      <ol class="guide-list">
        <li v-for="(step, i) in steps" :key="step.title" class="guide-item">
          <span class="guide-no" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
          <div class="guide-body">
            <div class="guide-title">{{ step.title }}</div>
            <div class="guide-desc">{{ step.desc }}</div>
          </div>
          <el-button v-if="step.path" size="small" text type="primary" @click="go(step.path)">
            {{ step.action }}<el-icon style="margin-left: 4px"><ArrowRight /></el-icon>
          </el-button>
        </li>
      </ol>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight,
  ChatDotRound,
  DataAnalysis,
  House,
  InfoFilled,
  Notebook,
  School,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const canTeach = computed(() => userStore.role !== 'student' && userStore.role !== 'parent')
const displayName = computed(() => userStore.user?.display_name || '老师')

const hour = new Date().getHours()
const greeting = computed(() => {
  if (hour < 6) return '夜深了'
  if (hour < 11) return '早上好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const ROLE_DESC: Record<string, string> = {
  admin: '知识库、教师审核与资源管理都在这里，也可以直接使用全部教学能力。',
  teacher: '备课、答疑、学情分析，今天也交给智能体搭把手。',
  student: '有问题随时问，也可以查学校的通知、作息和制度。',
  parent: '了解学校信息，招生政策与规章制度都能直接提问。',
}
const roleDesc = computed(() => ROLE_DESC[userStore.role] || ROLE_DESC.teacher)

const now = new Date()
const todayDate = `${now.getFullYear()} 年 ${now.getMonth() + 1} 月 ${now.getDate()} 日`
const todayWeek = `星期${'日一二三四五六'[now.getDay()]}`

interface Card {
  name: string
  desc: string
  path: string
  tone: string
  icon: Component
  teachOnly?: boolean
}
const cards: Card[] = [
  { name: '通用问答', desc: '多轮对话 · 学习辅导 · 知识答疑', path: '/chat/general', tone: 'blue', icon: ChatDotRound },
  { name: '教案一键生成', desc: '输入课题与学段，生成完整教案', path: '/lesson', tone: 'green', icon: Notebook, teachOnly: true },
  { name: '学校信息问答', desc: '招生 · 作息 · 制度，附引用来源', path: '/chat/school', tone: 'amber', icon: School },
  { name: '智能试卷研判', desc: '上传试卷，逐题解析与学情报告', path: '/exam', tone: 'violet', icon: DataAnalysis, teachOnly: true },
]
const visibleCards = computed(() => cards.filter((c) => canTeach.value || !c.teachOnly))

const steps = computed(() => {
  const list = [
    { title: '先把问题问清楚', desc: '在「通用问答」描述教学或学习问题，智能体会先给出多种解题思路，再收敛到最优路径。', path: '/chat/general', action: '去提问' },
    ...(canTeach.value
      ? [{ title: '生成并导出教案', desc: '填写学科、年级与课题，一键生成结构化教案，可导出 Word 或 Markdown。', path: '/lesson', action: '去生成' }]
      : []),
    { title: '核对来源与查资源', desc: '学校信息问答会标注知识库引用；电子书与试卷可在资源中心直接查阅下载。', path: '/library', action: '去查阅' },
  ]
  return list
})

function go(path: string) {
  router.push(path)
}
</script>

<style scoped>
.home {
  padding-bottom: var(--space-8);
}

/* ---------------- Hero ---------------- */
.hero {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: var(--space-6);
  padding: var(--space-8);
  margin-bottom: var(--space-8);
  border: 1px solid var(--notion-border);
  border-radius: var(--radius-lg);
  background: linear-gradient(120deg, #fbfcff 0%, #ffffff 58%, #f7fbf9 100%);
  box-shadow: var(--app-shadow-soft);
}
.hero-main {
  min-width: 0;
}
.hero-title {
  margin: var(--space-3) 0 var(--space-2);
  font-family: var(--notion-font-display);
  font-size: 26px;
  font-weight: 700;
  line-height: 1.35;
  color: var(--notion-text);
  letter-spacing: 0.3px;
}
.hero-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.8;
  color: var(--notion-text-secondary);
}
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-5);
}

.hero-aside {
  width: 220px;
  flex-shrink: 0;
  padding: var(--space-4);
  border-left: 1px solid var(--notion-border);
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.today-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--notion-text-muted);
}
.today-date {
  margin-top: 6px;
  font-size: 15px;
  font-weight: 700;
  color: var(--notion-text);
}
.today-week {
  margin-top: 2px;
  font-size: 12px;
  color: var(--notion-text-secondary);
}
.today-tip {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: var(--space-4);
  padding-top: var(--space-3);
  border-top: 1px dashed var(--notion-border);
  font-size: 11px;
  line-height: 1.6;
  color: var(--notion-text-muted);
}
.today-tip .el-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

/* ---------------- 分区 ---------------- */
.section {
  margin-top: var(--space-8);
}
.section-count {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--notion-text-muted);
}

/* ---------------- 功能卡 ---------------- */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-4);
}
.feature-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0;
  min-height: 156px;
  padding: var(--space-5);
  text-align: left;
  font-family: inherit;
  background: #fff;
  border: 1px solid var(--notion-border);
  border-radius: var(--radius-md);
  box-shadow: var(--notion-shadow-sm);
  cursor: pointer;
}
.feature-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  margin-bottom: var(--space-4);
  border-radius: var(--radius-sm);
}
.tone-blue { color: #2f5bd8; background: #eef2fd; }
.tone-green { color: #0e8f76; background: #e8f3f0; }
.tone-amber { color: #b28901; background: #fcf7e6; }
.tone-violet { color: #6d4bd8; background: #f1edfc; }
.feature-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--notion-text);
}
.feature-desc {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--notion-text-secondary);
}
.feature-arrow {
  position: absolute;
  top: var(--space-5);
  right: var(--space-5);
  color: var(--notion-text-muted);
  opacity: 0;
  transform: translateX(-4px);
  transition: opacity var(--dur-fast) ease, transform var(--dur-fast) ease;
}
.feature-card:hover .feature-arrow,
.feature-card:focus-visible .feature-arrow {
  opacity: 1;
  transform: translateX(0);
}

/* ---------------- 使用指引 ---------------- */
.guide-list {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid var(--notion-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: #fff;
}
.guide-item {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
}
.guide-item + .guide-item {
  border-top: 1px solid var(--notion-border);
}
.guide-no {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--notion-bg-page);
  border: 1px solid var(--notion-border);
  font-size: 12px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--notion-blue);
}
.guide-body {
  flex: 1;
  min-width: 0;
}
.guide-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--notion-text);
}
.guide-desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--notion-text-secondary);
}

/* ---------------- 响应式 ---------------- */
@media (max-width: 900px) {
  .hero-aside {
    display: none;
  }
}
@media (max-width: 768px) {
  .hero {
    padding: var(--space-5);
    margin-bottom: var(--space-6);
  }
  .hero-title {
    font-size: 21px;
  }
  .section {
    margin-top: var(--space-6);
  }
  .app-section-head {
    margin-bottom: var(--space-3);
  }
  .feature-grid {
    grid-template-columns: 1fr;
    gap: var(--space-3);
  }
  .feature-card {
    min-height: 0;
  }
  .guide-item {
    flex-wrap: wrap;
    padding: var(--space-4);
  }
  .guide-item .el-button {
    margin-left: 48px;
  }
}
</style>
