<template>
  <div class="home">
    <el-row :gutter="16">
      <el-col v-for="card in cards" :key="card.path" :span="6">
        <el-card class="feature-card" shadow="hover" @click="router.push(card.path)">
          <div class="feature-icon">
            <el-icon :size="24" color="#15181f"><component :is="card.icon" /></el-icon>
          </div>
          <div class="feature-name">{{ card.name }}</div>
          <div class="feature-desc">{{ card.desc }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="quick-card">
      <template #header>
        <span class="quick-title">快速开始</span>
      </template>
      <el-steps :active="4" align-center>
        <el-step title="1. 启动后端" description="uvicorn app.main:app --reload" />
        <el-step title="2. 启动前端" description="npm run dev" />
        <el-step title="3. 导入知识库" description="python scripts/ingest_kb.py --dir ./kb_docs" />
        <el-step title="4. 开始使用" description="登录后进入各模块" />
      </el-steps>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ChatDotRound, School, Notebook, DocumentChecked } from '@element-plus/icons-vue'

const router = useRouter()
const cards = [
  { name: '通用问答', desc: '多轮对话 · 学习辅导 · 知识答疑', path: '/chat/general', icon: ChatDotRound, bg: '#0ea5e9' },
  { name: '教案一键生成', desc: '输入课题与学段，生成完整教案', path: '/lesson', icon: Notebook, bg: '#10b981' },
  { name: '学校信息问答', desc: '招生 · 作息 · 制度，引用知识库来源', path: '/chat/school', icon: School, bg: '#f59e0b' },
  { name: '智能试卷研判', desc: '上传试卷，逐题解析与学情报告', path: '/exam', icon: DocumentChecked, bg: '#8b5cf6' },
]
</script>

<style scoped>
.feature-card {
  cursor: pointer;
  text-align: center;
  height: 180px;
}
.feature-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 16px auto 8px;
  background: #f5f7fa;
  border: 1px solid #e7eaf0;
}
.feature-name {
  font-size: 15px;
  font-weight: 600;
  color: #15181f;
}
.feature-desc {
  font-size: 12px;
  color: #5b6472;
  margin-top: 6px;
}
.quick-card {
  margin-top: 16px;
}
.quick-title {
  font-weight: 600;
}
</style>
