<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-icon-box"><el-icon :size="16"><School /></el-icon></span>
        <span class="brand-name">劝学路小学智能体</span>
      </div>

      <nav class="nav">
        <router-link
          v-for="t in tabs"
          :key="t.path"
          :to="t.path"
          class="nav-item"
          :class="{ on: isActive(t.path) }"
        >
          <el-icon :size="16"><component :is="t.icon" /></el-icon>
          <span>{{ t.name }}</span>
        </router-link>
      </nav>

      <div class="user">
        <el-dropdown @command="onCommand">
          <span class="user-box">
            <el-avatar :size="24">{{ firstChar }}</el-avatar>
            <span class="user-name">{{ user?.display_name || '未登录' }}</span>
            <el-icon class="caret"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="change-password">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </aside>

    <div class="main">
      <header class="page-header">
        <span class="page-title">{{ currentName }}</span>
      </header>
      <div class="content">
        <router-view />
      </div>
    </div>

    <el-dialog v-model="pwdVisible" title="修改密码" width="400px" append-to-body>
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-position="top">
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="pwdForm.old_password" type="password" placeholder="请输入原密码" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="pwdForm.new_password" type="password" placeholder="至少 6 位" show-password />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input v-model="pwdForm.confirm_password" type="password" placeholder="再次输入新密码" show-password />
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
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { School, ArrowDown, ChatDotRound, Document, Reading, DataAnalysis, Collection, Folder, UserFilled } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { changePassword } from '@/api/modules/auth'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const user = computed(() => userStore.user)
const firstChar = computed(() => (user.value?.display_name || '用')[0])

const allTabs = [
  { name: '通用问答', path: '/chat/general', icon: ChatDotRound },
  { name: '教案一键生成', path: '/lesson', icon: Document },
  { name: '学校信息问答', path: '/chat/school', icon: Reading },
  { name: '智能试卷研判', path: '/exam', icon: DataAnalysis },
  { name: '电子书/试卷', path: '/library', icon: Collection },
  { name: '知识库管理', path: '/kb', icon: Folder },
  { name: '教师审核', path: '/teacher-review', icon: UserFilled },
]

const tabs = computed(() => {
  const role = userStore.role
  return allTabs.filter((t) => {
    if (t.path === '/kb' || t.path === '/teacher-review') return role === 'admin'
    if (role === 'student' || role === 'parent') {
      return t.path !== '/lesson' && t.path !== '/exam'
    }
    return true
  })
})

const currentName = computed(() => tabs.value.find((t) => isActive(t.path))?.name || '')

function isActive(path: string) {
  return route.path === path
}

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
  display: flex;
  background: #f5f7fa;
}
.sidebar {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
  padding: 12px 8px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px 14px;
  margin-bottom: 10px;
  border-bottom: 1px solid #e7eaf0;
  color: #15181f;
}
.brand-icon-box {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  background: linear-gradient(135deg, #2f5bd8, #0e8f76);
  border-radius: 8px;
  box-shadow: 0 4px 10px rgba(47, 91, 216, 0.25);
}
.brand-name {
  font-size: 15px;
  font-weight: 700;
  font-family: var(--notion-font-display);
  color: #15181f;
  white-space: nowrap;
  letter-spacing: 0.5px;
}
.nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 2px;
  padding: 4px 0;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 34px;
  padding: 0 10px;
  font-size: 14px;
  font-weight: 500;
  color: #5b6472;
  text-decoration: none;
  border-radius: 6px;
  transition: background-color 150ms ease, color 150ms ease;
}
.nav-item .el-icon {
  color: #98a1b0;
  transition: color 150ms ease;
}
.nav-item:hover {
  background: #f2f4f7;
  color: #15181f;
}
.nav-item:hover .el-icon {
  color: #5b6472;
}
.nav-item.on {
  background: #e9edf3;
  color: #15181f;
  font-weight: 600;
  box-shadow: inset 2px 0 0 #2f5bd8;
}
.nav-item.on .el-icon {
  color: #15181f;
}
.user {
  padding: 8px;
  border-top: 1px solid #e7eaf0;
}
.user-box {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 6px;
  transition: background-color 150ms ease;
}
.user-box:hover {
  background: #f2f4f7;
}
.user-name {
  flex: 1;
  font-size: 13px;
  color: #15181f;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.caret {
  color: #98a1b0;
}
.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}
.page-header {
  height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid #e7eaf0;
}
.page-title {
  font-size: 16px;
  font-weight: 700;
  font-family: var(--notion-font-display);
  color: #15181f;
  letter-spacing: 0.3px;
}
.content {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 20px;
  background: #ffffff;
}
</style>