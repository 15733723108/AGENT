<template>
  <div class="login-page">
    <div class="deco deco-a"></div>
    <div class="deco deco-b"></div>

    <el-card class="login-card">
      <div class="brand-mark">
        <el-icon :size="26"><School /></el-icon>
      </div>
      <div class="login-title">劝学路小学智能体</div>
      <div class="login-sub">{{ mode === 'login' ? '通用问答 · 教案生成 · 学校信息 · 试卷研判' : '创建账户，选择您的使用身份' }}</div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @keyup.enter="onSubmit">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" placeholder="请输入账号" />
        </el-form-item>

        <el-form-item v-if="mode === 'register'" label="姓名" prop="display_name">
          <el-input v-model="form.display_name" placeholder="请输入姓名 / 称呼" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>

        <el-form-item v-if="mode === 'register'" label="身份" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio value="teacher">教师</el-radio>
            <el-radio value="student">学生</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-button type="primary" class="login-btn" :loading="loading" @click="onSubmit">
          {{ mode === 'login' ? '登 录' : '注册并登录' }}
        </el-button>
      </el-form>

      <div class="tip">
        <template v-if="mode === 'login'">
          <span>没有账号？</span>
          <a class="link" @click="switchMode('register')">立即注册</a>
          <div class="tip-line">管理员账号请由系统 / scripts/create_admin.py 创建</div>
        </template>
        <template v-else>
          <span>已有账号？</span>
          <a class="link" @click="switchMode('login')">返回登录</a>
          <div class="tip-line">教师注册后需经管理员审核方可登录</div>
        </template>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { School } from '@element-plus/icons-vue'
import { login, register } from '@/api/modules/auth'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const mode = ref<'login' | 'register'>('login')
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  display_name: '',
  role: 'student' as 'teacher' | 'student',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  display_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
}

function switchMode(m: 'login' | 'register') {
  mode.value = m
  formRef.value?.clearValidate()
}

async function onSubmit() {
  await formRef.value?.validate()
  loading.value = true
  try {
    if (mode.value === 'login') {
      const resp = await login({ username: form.username, password: form.password })
      userStore.setToken(resp.access_token)
      userStore.setUser(resp.user)
      ElMessage.success(`欢迎，${resp.user.display_name}`)
      router.push((route.query.redirect as string) || '/')
      return
    }
    const resp = await register({
      username: form.username,
      password: form.password,
      display_name: form.display_name,
      role: form.role,
    })
    if (resp.pending) {
      ElMessage.warning(resp.message || '注册成功，请等待管理员审核')
      switchMode('login')
      return
    }
    if (resp.access_token && resp.user) {
      userStore.setToken(resp.access_token)
      userStore.setUser(resp.user)
      ElMessage.success('注册成功')
      router.push((route.query.redirect as string) || '/')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  overflow: hidden;
}

.deco {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
  pointer-events: none;
}
.deco-a {
  width: 420px;
  height: 420px;
  background: rgba(47, 91, 216, 0.16);
  top: -140px;
  right: -100px;
}
.deco-b {
  width: 360px;
  height: 360px;
  background: rgba(14, 143, 118, 0.12);
  bottom: -120px;
  left: -80px;
}

.login-card {
  position: relative;
  width: 400px;
  padding: 12px 8px;
  animation: cardIn 420ms cubic-bezier(0.22, 1, 0.36, 1);
}

@keyframes cardIn {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.brand-mark {
  width: 52px;
  height: 52px;
  margin: 0 auto 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  background: linear-gradient(135deg, #2f5bd8, #0e8f76);
  border-radius: 14px;
  box-shadow: 0 8px 20px rgba(47, 91, 216, 0.28);
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  font-family: var(--notion-font-display);
  text-align: center;
  color: #15181f;
  letter-spacing: 0.5px;
}
.login-sub {
  text-align: center;
  color: #5b6472;
  font-size: 13px;
  margin: 8px 0 24px;
}
.login-btn {
  width: 100%;
  margin-top: 8px;
  font-weight: 600;
}
.tip {
  margin-top: 16px;
  font-size: 12px;
  color: #98a1b0;
  text-align: center;
}
.tip-line {
  margin-top: 6px;
}
.link {
  color: #2f5bd8;
  cursor: pointer;
  margin-left: 4px;
}
</style>