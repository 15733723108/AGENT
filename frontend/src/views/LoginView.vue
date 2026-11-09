<template>
  <div class="login-page">
    <!-- 品牌区：桌面端双栏，小屏自动隐藏 -->
    <aside class="login-brand" aria-hidden="true">
      <div class="deco deco-a"></div>
      <div class="deco deco-b"></div>
      <div class="brand-content">
        <div class="brand-logo"><el-icon :size="26"><School /></el-icon></div>
        <div class="brand-title">沧州市劝学路小学<br />智能体平台</div>
        <p class="brand-sub">把备课、答疑与学情分析，交给一位懂教学的数字助手。</p>
        <ul class="brand-features">
          <li v-for="f in features" :key="f">
            <span class="feature-dot"></span>{{ f }}
          </li>
        </ul>
      </div>
      <div class="brand-foot">校园智能体 · 服务于教与学</div>
    </aside>

    <!-- 表单区：skip-link 在登录页同样有落点 -->
    <section class="login-pane" aria-label="账号登录">
      <el-card id="main-content" class="login-card" tabindex="-1">
        <div class="brand-mark"><el-icon :size="24"><School /></el-icon></div>
        <h1 class="login-title">{{ mode === 'login' ? '欢迎回来' : '创建账户' }}</h1>
        <div class="login-sub">
          {{ mode === 'login' ? '登录后即可使用全部教学能力' : '选择您的使用身份，教师注册需管理员审核' }}
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          :aria-busy="loading"
          @keyup.enter="onSubmit"
        >
          <el-form-item label="账号" prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入账号"
              autocomplete="username"
              :prefix-icon="User"
            />
          </el-form-item>

          <el-form-item v-if="mode === 'register'" label="姓名" prop="display_name">
            <el-input v-model="form.display_name" placeholder="请输入姓名 / 称呼" autocomplete="nickname" />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              show-password
              :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
            />
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
            <button type="button" class="link" @click="switchMode('register')">立即注册</button>
            <div class="tip-line">管理员账号请由系统脚本创建</div>
          </template>
          <template v-else>
            <span>已有账号？</span>
            <button type="button" class="link" @click="switchMode('login')">返回登录</button>
            <div class="tip-line">教师注册后需经管理员审核方可登录</div>
          </template>
        </div>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { School, User } from '@element-plus/icons-vue'
import { login, register } from '@/api/modules/auth'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const features = ['通用问答 · 多轮对话与学习辅导', '教案一键生成 · 结构化可导出', '学校信息问答 · 附引用来源', '智能试卷研判 · 逐题学情分析']

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
  if (loading.value) return
  // validate() 校验失败会 reject，原实现未捕获会产生 unhandled rejection
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

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
  display: flex;
  height: 100vh;
  height: 100dvh;
  background: #fff;
  overflow: hidden;
}

/* ---------------- 左：品牌区 ---------------- */
.login-brand {
  position: relative;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: clamp(32px, 6vw, 72px);
  background: linear-gradient(145deg, #f7f9ff 0%, #ffffff 55%, #f4faf7 100%);
  border-right: 1px solid var(--notion-border);
  overflow: hidden;
}
.brand-content {
  position: relative;
  z-index: 1;
  max-width: 420px;
}
.brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  color: #fff;
  background: linear-gradient(135deg, #2f5bd8, #0e8f76);
  border-radius: var(--radius-lg);
  box-shadow: 0 10px 24px rgba(47, 91, 216, 0.26);
}
.brand-title {
  margin-top: var(--space-8);
  font-family: var(--notion-font-display);
  font-size: clamp(26px, 3vw, 36px);
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: 1px;
  color: var(--notion-text);
}
.brand-sub {
  margin: var(--space-4) 0 0;
  font-size: 14px;
  line-height: 1.8;
  color: var(--notion-text-secondary);
}
.brand-features {
  list-style: none;
  margin: var(--space-8) 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.brand-features li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--notion-text-secondary);
}
.feature-dot {
  width: 6px;
  height: 6px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--notion-green);
  box-shadow: 0 0 0 4px rgba(14, 143, 118, 0.1);
}
.brand-foot {
  position: relative;
  z-index: 1;
  font-size: 11px;
  color: var(--notion-text-muted);
  letter-spacing: 0.05em;
}

.deco {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
}
.deco-a {
  width: 420px;
  height: 420px;
  background: rgba(47, 91, 216, 0.14);
  top: -160px;
  right: -120px;
}
.deco-b {
  width: 360px;
  height: 360px;
  background: rgba(14, 143, 118, 0.12);
  bottom: -140px;
  left: -100px;
}

/* ---------------- 右：表单区 ---------------- */
.login-pane {
  flex: 0 0 clamp(420px, 38vw, 560px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  background: #fff;
}
.login-card {
  width: min(400px, 100%);
  padding: var(--space-4) var(--space-2);
  outline: none;
  animation: cardIn 420ms var(--ease-out);
}
@keyframes cardIn {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}

.brand-mark {
  display: none; /* 桌面端品牌区已展示标识，避免重复 */
  width: 48px;
  height: 48px;
  margin: 0 auto 14px;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #2f5bd8, #0e8f76);
  border-radius: var(--radius-lg);
}
.login-title {
  margin: 0;
  font-size: 23px;
  font-weight: 700;
  font-family: var(--notion-font-display);
  text-align: center;
  color: var(--notion-text);
  letter-spacing: 0.5px;
}
.login-sub {
  text-align: center;
  color: var(--notion-text-secondary);
  font-size: 12.5px;
  line-height: 1.7;
  margin: var(--space-2) 0 var(--space-6);
}
.login-btn {
  width: 100%;
  margin-top: var(--space-2);
  height: 38px;
  font-weight: 600;
}
.tip {
  margin-top: var(--space-4);
  font-size: 12px;
  color: var(--notion-text-muted);
  text-align: center;
}
.tip-line {
  margin-top: 6px;
}
.link {
  padding: 0;
  margin-left: 4px;
  font: inherit;
  color: var(--notion-blue);
  background: transparent;
  border: none;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

@media (max-width: 900px) {
  .login-brand {
    display: none;
  }
  .login-pane {
    flex: 1;
    padding: var(--space-4);
    background: linear-gradient(160deg, #f7f9ff 0%, #ffffff 60%, #f4faf7 100%);
  }
  .brand-mark {
    display: flex;
  }
  .login-card {
    padding: var(--space-5) var(--space-3);
  }
}
</style>
