<template>
  <div class="layout" :class="{ 'is-compact': compact, 'is-mobile': mobile }">
    <!-- 移动端抽屉遮罩：点击 / ESC 关闭 -->
    <transition name="overlay-fade">
      <div
        v-if="mobile && drawerOpen"
        class="sidebar-overlay"
        aria-hidden="true"
        @click="drawerOpen = false"
      />
    </transition>

    <aside
      id="app-sidebar"
      class="sidebar"
      :class="{ 'is-open': drawerOpen }"
      :aria-label="'主导航'"
      :aria-hidden="mobile && !drawerOpen ? 'true' : undefined"
    >
      <div class="brand">
        <span class="brand-icon-box"><el-icon :size="17"><School /></el-icon></span>
        <span class="brand-name">劝学路小学智能体</span>
      </div>

      <nav class="nav" aria-label="功能导航">
        <div
          v-for="group in navGroups"
          :key="group.label"
          class="nav-group"
          role="group"
          :aria-label="group.label"
        >
          <div class="nav-group-label" aria-hidden="true">{{ group.label }}</div>
          <router-link
            v-for="t in group.items"
            :key="t.path"
            :to="t.path"
            class="nav-item"
            :class="{ on: isActive(t.path) }"
            :aria-current="isActive(t.path) ? 'page' : undefined"
            :title="compact ? t.name : undefined"
          >
            <el-icon :size="17"><component :is="t.icon" /></el-icon>
            <span class="nav-label">{{ t.name }}</span>
          </router-link>
        </div>
      </nav>

      <div class="sidebar-foot">
        <span class="foot-dot" aria-hidden="true" />
        <span class="foot-text">校园智能体 · v1.0</span>
      </div>
    </aside>

    <div class="main">
      <header class="page-header">
        <button
          v-if="mobile"
          class="icon-btn menu-btn"
          type="button"
          aria-controls="app-sidebar"
          :aria-expanded="drawerOpen"
          :aria-label="drawerOpen ? '关闭导航菜单' : '打开导航菜单'"
          @click="drawerOpen = !drawerOpen"
        >
          <el-icon :size="18"><Menu /></el-icon>
        </button>

        <div class="header-titles">
          <span class="page-title">{{ currentName }}</span>
          <span v-if="currentDesc" class="page-desc">{{ currentDesc }}</span>
        </div>

        <div class="header-actions">
          <span v-if="roleLabel" class="role-chip">{{ roleLabel }}</span>
          <el-dropdown @command="onCommand">
            <button class="user-box" type="button" aria-label="用户菜单">
              <el-avatar :size="28">{{ firstChar }}</el-avatar>
              <span class="user-name">{{ user?.display_name || '未登录' }}</span>
              <el-icon class="caret"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="change-password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- skip-link 的落点：tabindex=-1 保证可被脚本/锚点聚焦 -->
      <main id="main-content" class="content" role="main" tabindex="-1">
        <router-view />
      </main>
    </div>

    <el-dialog v-model="pwdVisible" title="修改密码" width="420px" append-to-body>
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-position="top">
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="pwdForm.old_password" type="password" placeholder="请输入原密码" show-password autocomplete="current-password" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="pwdForm.new_password" type="password" placeholder="至少 6 位" show-password autocomplete="new-password" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input v-model="pwdForm.confirm_password" type="password" placeholder="再次输入新密码" show-password autocomplete="new-password" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdLoading" @click="onChangePassword">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  ChatDotRound,
  Collection,
  DataAnalysis,
  Document,
  Folder,
  House,
  Menu,
  Reading,
  School,
  UserFilled,
} from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { changePassword } from '@/api/modules/auth'

interface Tab {
  name: string
  path: string
  desc: string
  group: string
  icon: Component
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const user = computed(() => userStore.user)
const firstChar = computed(() => (user.value?.display_name || '用')[0])

const allTabs: Tab[] = [
  { name: '工作台', path: '/home', desc: '从这里开始今天的教学工作', group: '总览', icon: House },
  { name: '通用问答', path: '/chat/general', desc: '多轮对话 · 学习辅导 · 知识答疑', group: '教学应用', icon: ChatDotRound },
  { name: '教案一键生成', path: '/lesson', desc: '输入课题与学段，生成结构化教案', group: '教学应用', icon: Document },
  { name: '学校信息问答', path: '/chat/school', desc: '招生 · 作息 · 制度，附引用来源', group: '教学应用', icon: Reading },
  { name: '智能试卷研判', path: '/exam', desc: '逐题解析、知识点标注与学情统计', group: '教学应用', icon: DataAnalysis },
  { name: '电子书 / 试卷', path: '/library', desc: '查阅与下载校内教学资源', group: '资源中心', icon: Collection },
  { name: '知识库管理', path: '/kb', desc: '导入文档，维护检索知识域', group: '管理', icon: Folder },
  { name: '教师审核', path: '/teacher-review', desc: '审核教师注册申请', group: '管理', icon: UserFilled },
]

// 角色可见性：与 router/index.ts 的守卫保持一致
const visibleTabs = computed(() => {
  const role = userStore.role
  return allTabs.filter((t) => {
    if (t.path === '/kb' || t.path === '/teacher-review') return role === 'admin'
    if (role === 'student' || role === 'parent') {
      return t.path !== '/lesson' && t.path !== '/exam'
    }
    return true
  })
})

const navGroups = computed(() => {
  const order = ['总览', '教学应用', '资源中心', '管理']
  return order
    .map((label) => ({ label, items: visibleTabs.value.filter((t) => t.group === label) }))
    .filter((g) => g.items.length > 0)
})

const activeTab = computed(() => visibleTabs.value.find((t) => isActive(t.path)))
const currentName = computed(() => activeTab.value?.name || '')
const currentDesc = computed(() => activeTab.value?.desc || '')

const ROLE_LABELS: Record<string, string> = {
  admin: '管理员',
  teacher: '教师',
  student: '学生',
  parent: '家长',
}
const roleLabel = computed(() => ROLE_LABELS[userStore.role] || '')

function isActive(path: string) {
  return route.path === path
}

/* ---------- 响应式：断点用 matchMedia，比 resize 监听更精确 ---------- */
const mobile = ref(false)
const compact = ref(false)
const drawerOpen = ref(false)
let mediaHandlers: Array<{ mql: MediaQueryList; fn: (e: MediaQueryListEvent) => void }> = []

function syncBreakpoints() {
  mobile.value = window.matchMedia('(max-width: 768px)').matches
  compact.value = window.matchMedia('(min-width: 769px) and (max-width: 1100px)').matches
  if (!mobile.value) drawerOpen.value = false
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && drawerOpen.value) {
    drawerOpen.value = false
    document.querySelector<HTMLElement>('.menu-btn')?.focus()
  }
}

onMounted(() => {
  syncBreakpoints()
  const defs: Array<[string, (v: boolean) => void]> = [
    ['(max-width: 768px)', (v) => { mobile.value = v; if (!v) drawerOpen.value = false }],
    ['(min-width: 769px) and (max-width: 1100px)', (v) => { compact.value = v }],
  ]
  mediaHandlers = defs.map(([query, setter]) => {
    const mql = window.matchMedia(query)
    const fn = (e: MediaQueryListEvent) => setter(e.matches)
    mql.addEventListener('change', fn)
    return { mql, fn }
  })
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  mediaHandlers.forEach(({ mql, fn }) => mql.removeEventListener('change', fn))
  window.removeEventListener('keydown', onKeydown)
})

// 导航后自动收起抽屉，避免遮罩挡住新页面
watch(() => route.fullPath, () => { drawerOpen.value = false })

/* ---------- 用户菜单与修改密码 ---------- */
function onCommand(cmd: string) {
  if (cmd === 'change-password') {
    openPasswordDialog()
    return
  }
  if (cmd === 'logout') {
    userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}

const pwdVisible = ref(false)
const pwdLoading = ref(false)
const pwdFormRef = ref<FormInstance>()
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const pwdRules: FormRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码至少 6 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== pwdForm.new_password) {
          callback(new Error('两次输入的新密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

function openPasswordDialog() {
  pwdForm.old_password = ''
  pwdForm.new_password = ''
  pwdForm.confirm_password = ''
  pwdFormRef.value?.clearValidate()
  pwdVisible.value = true
}

async function onChangePassword() {
  await pwdFormRef.value?.validate()
  pwdLoading.value = true
  try {
    await changePassword({ old_password: pwdForm.old_password, new_password: pwdForm.new_password })
    pwdVisible.value = false
    ElMessage.success('密码修改成功，请重新登录')
    userStore.logout()
    router.push('/login')
  } finally {
    pwdLoading.value = false
  }
}
</script>

<style scoped>
.layout {
  height: 100vh;
  height: 100dvh; /* 移动端浏览器地址栏收起时高度更准确 */
  display: flex;
  background: var(--notion-bg-page);
}

/* ---------------- 侧栏 ---------------- */
.sidebar {
  width: var(--app-sidebar-w);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--notion-bg-page);
  border-right: 1px solid var(--notion-border);
  padding: var(--space-3) var(--space-2);
  transition: width var(--dur-base) var(--ease-out), transform var(--dur-base) var(--ease-out);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px 16px;
  margin-bottom: var(--space-2);
  border-bottom: 1px solid var(--notion-border);
  color: var(--notion-text);
  white-space: nowrap;
  overflow: hidden;
}
.brand-icon-box {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #2f5bd8, #0e8f76);
  border-radius: var(--radius-sm);
  box-shadow: 0 4px 10px rgba(47, 91, 216, 0.25);
}
.brand-name {
  font-size: 14px;
  font-weight: 700;
  font-family: var(--notion-font-display);
  letter-spacing: 0.3px;
}

.nav {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-2) 0;
}
.nav-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-group-label {
  padding: 0 10px 6px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--notion-text-muted);
  white-space: nowrap;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 36px;
  padding: 0 10px;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--notion-text-secondary);
  text-decoration: none;
  border-radius: var(--radius-sm);
  white-space: nowrap;
  transition: background-color var(--dur-fast) ease, color var(--dur-fast) ease;
}
.nav-item .el-icon {
  flex-shrink: 0;
  color: var(--notion-text-muted);
  transition: color var(--dur-fast) ease;
}
.nav-item:hover {
  background: var(--notion-hover);
  color: var(--notion-text);
}
.nav-item:hover .el-icon {
  color: var(--notion-text-secondary);
}
.nav-item.on {
  background: var(--notion-active);
  color: var(--notion-text);
  font-weight: 600;
  box-shadow: inset 2px 0 0 var(--notion-blue);
}
.nav-item.on .el-icon {
  color: var(--notion-blue);
}

.sidebar-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 10px 4px;
  border-top: 1px solid var(--notion-border);
  font-size: 11px;
  color: var(--notion-text-muted);
  white-space: nowrap;
  overflow: hidden;
}
.foot-dot {
  width: 6px;
  height: 6px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--notion-green);
}

/* ---------------- 主区 ---------------- */
.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
}
.page-header {
  height: var(--app-header-h);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--app-gutter);
  border-bottom: 1px solid var(--notion-border);
  background: #fff;
  z-index: var(--z-header);
}
.header-titles {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  min-width: 0;
}
.page-title {
  font-size: 15px;
  font-weight: 700;
  font-family: var(--notion-font-display);
  color: var(--notion-text);
  letter-spacing: 0.3px;
  white-space: nowrap;
}
.page-desc {
  font-size: 12px;
  color: var(--notion-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.header-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}
.role-chip {
  padding: 3px 9px;
  font-size: 11px;
  font-weight: 600;
  color: var(--notion-blue);
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-8);
  border-radius: var(--radius-pill);
}
.user-box {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 4px 6px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background-color var(--dur-fast) ease;
}
.user-box:hover {
  background: var(--notion-hover);
}
.user-name {
  max-width: 100px;
  font-size: 13px;
  color: var(--notion-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.caret {
  color: var(--notion-text-muted);
}
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  color: var(--notion-text-secondary);
  background: transparent;
  border: 1px solid var(--notion-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background-color var(--dur-fast) ease;
}
.icon-btn:hover {
  background: var(--notion-hover);
}

.content {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: var(--app-gutter);
  background: #fff;
  outline: none; /* 作为 skip-link 落点，避免聚焦时出现默认外框 */
}

/* ---------------- 紧凑模式（平板 / 小桌面） ---------------- */
.layout.is-compact .sidebar {
  width: var(--app-sidebar-w-compact);
  padding-left: var(--space-2);
  padding-right: var(--space-2);
}
.layout.is-compact .brand {
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}
.layout.is-compact .brand-name,
.layout.is-compact .nav-label,
.layout.is-compact .nav-group-label,
.layout.is-compact .foot-text {
  display: none;
}
.layout.is-compact .nav-item {
  justify-content: center;
  padding: 0;
}
.layout.is-compact .nav-group {
  gap: 4px;
}
.layout.is-compact .nav-group + .nav-group {
  padding-top: var(--space-3);
  border-top: 1px solid var(--notion-border);
}
.layout.is-compact .sidebar-foot {
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}

/* ---------------- 移动端：侧栏变抽屉 ---------------- */
.sidebar-overlay {
  position: fixed;
  inset: 0;
  z-index: calc(var(--z-sidebar) - 1);
  background: rgba(21, 24, 31, 0.38);
}
.overlay-fade-enter-active,
.overlay-fade-leave-active {
  transition: opacity var(--dur-base) ease;
}
.overlay-fade-enter-from,
.overlay-fade-leave-to {
  opacity: 0;
}

.layout.is-mobile .sidebar {
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  z-index: var(--z-sidebar);
  width: min(280px, 82vw);
  background: var(--notion-bg-page);
  box-shadow: var(--notion-shadow-md);
  transform: translateX(-100%);
}
.layout.is-mobile .sidebar.is-open {
  transform: translateX(0);
}
.layout.is-mobile .page-header {
  padding: 0 var(--space-4);
}
.layout.is-mobile .page-desc,
.layout.is-mobile .user-name,
.layout.is-mobile .role-chip {
  display: none;
}
.layout.is-mobile .content {
  padding: var(--space-4);
}
</style>
