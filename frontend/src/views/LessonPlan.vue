<template>
  <div class="lesson-page">
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card>
          <template #header><span class="card-title">生成条件</span></template>
          <el-form label-position="top">
            <el-form-item label="学科" required>
              <el-select v-model="form.subject" filterable allow-create default-first-option style="width: 100%">
                <el-option v-for="s in subjects" :key="s" :label="s" :value="s" />
              </el-select>
            </el-form-item>
            <el-form-item label="年级/学段" required>
              <el-select v-model="form.grade" filterable allow-create default-first-option style="width: 100%">
                <el-option v-for="g in grades" :key="g" :label="g" :value="g" />
              </el-select>
            </el-form-item>
            <el-form-item label="课题" required>
              <el-input v-model="form.topic" placeholder="例如：分数的初步认识" />
            </el-form-item>
            <el-form-item label="课时数">
              <el-input-number v-model="form.class_hours" :min="1" :max="10" />
            </el-form-item>
            <el-form-item label="课型">
              <el-select v-model="form.course_type" clearable placeholder="选填" style="width: 100%">
                <el-option label="新授课" value="新授课" />
                <el-option label="复习课" value="复习课" />
                <el-option label="练习课" value="练习课" />
                <el-option label="实验课" value="实验课" />
              </el-select>
            </el-form-item>
            <el-form-item label="学情简述">
              <el-input v-model="form.student_profile" type="textarea" :rows="2" placeholder="选填，例如：学生已掌握分数基本概念，理解较慢" />
            </el-form-item>
            <el-form-item label="注入教材参考">
              <el-switch v-model="form.use_textbook_rag" />
              <span class="rag-tip">从知识库教材中检索相关片段辅助生成</span>
            </el-form-item>
            <el-button type="primary" :loading="loading" :disabled="!form.topic.trim()" style="width: 100%" @click="generate">
              一键生成教案
            </el-button>
          </el-form>
        </el-card>

        <el-card style="margin-top: 16px">
          <template #header>
            <div class="card-title-row">
              <span class="card-title">历史教案</span>
              <el-button size="small" text type="primary" @click="loadList">刷新</el-button>
            </div>
          </template>
          <el-table :data="plans" size="small" max-height="320" @row-click="selectPlan">
            <el-table-column prop="topic" label="课题" min-width="120" show-overflow-tooltip />
            <el-table-column prop="subject" label="学科" width="70" />
            <el-table-column prop="grade" label="年级" width="70" />
            <el-table-column label="操作" width="104">
              <template #default="{ row }">
                <DownloadButton label="导出" done-text="已导出" size="small" @click.stop @download="downloadPlan(row, 'docx')" />
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-title-row">
              <span class="card-title">教案内容</span>
              <div v-if="current" class="lesson-actions">
                <DownloadButton label="导出 MD" done-text="已导出" size="small" @download="downloadPlan(current, 'md')" />
                <DownloadButton label="导出 Word" done-text="已导出" size="small" @download="downloadPlan(current, 'docx')" />
              </div>
            </div>
          </template>
          <div v-if="!current" class="empty">填写左侧条件后点击「一键生成教案」</div>
          <div v-else class="lesson-content">
            <div class="lesson-head">
              <h2>{{ current.topic }}</h2>
              <div class="lesson-meta">{{ current.subject }} · {{ current.grade }} · {{ current.class_hours }} 课时 · {{ current.course_type || '常规课' }}</div>
            </div>
            <el-divider />

            <section v-if="content.teaching_objectives">
              <h4>教学目标</h4>
              <div v-for="(v, k) in content.teaching_objectives" :key="String(k)" class="kv-item"><b>{{ k }}：</b>{{ v }}</div>
            </section>

            <section v-if="content.key_points && content.key_points.length">
              <h4>教学重点</h4>
              <ol><li v-for="(x, i) in content.key_points" :key="i">{{ x }}</li></ol>
            </section>

            <section v-if="content.difficult_points && content.difficult_points.length">
              <h4>教学难点</h4>
              <ol><li v-for="(x, i) in content.difficult_points" :key="i">{{ x }}</li></ol>
            </section>

            <section v-if="content.teaching_prep && content.teaching_prep.length">
              <h4>教学准备</h4>
              <ol><li v-for="(x, i) in content.teaching_prep" :key="i">{{ x }}</li></ol>
            </section>

            <section v-if="content.teaching_process && content.teaching_process.length">
              <h4>教学过程</h4>
              <div v-for="(step, i) in content.teaching_process" :key="i" class="step">
                <div class="step-head">
                  <b>{{ step.stage }}</b>
                  <span class="step-dur">{{ step.duration_minutes }} 分钟</span>
                </div>
                <p class="step-content">{{ step.content }}</p>
              </div>
            </section>

            <section v-if="content.board_design">
              <h4>板书设计</h4>
              <p class="plain-text">{{ content.board_design }}</p>
            </section>

            <section v-if="content.homework">
              <h4>作业设计</h4>
              <div v-for="(v, k) in content.homework" :key="String(k)" class="kv-item"><b>{{ k }}：</b>{{ v }}</div>
            </section>

            <section v-if="content.reflection">
              <h4>教学反思（预留）</h4>
              <p class="plain-text">{{ content.reflection }}</p>
            </section>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { generateLesson, listLessons, exportLesson } from '@/api/modules/lesson'
import type { LessonPlan } from '@/types'
import DownloadButton from '@/components/DownloadButton.vue'

const subjects = ['语文', '数学', '英语', '科学', '道德与法治', '音乐', '美术', '体育']
const grades = ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级']

const form = ref({
  subject: '数学',
  grade: '三年级',
  topic: '',
  class_hours: 1,
  course_type: '新授课',
  student_profile: '',
  use_textbook_rag: true,
})
const loading = ref(false)
const current = ref<LessonPlan | null>(null)
const plans = ref<LessonPlan[]>([])

const content = computed(() => (current.value?.content_json as any) || {})

async function generate() {
  loading.value = true
  try {
    const resp = await generateLesson({
      subject: form.value.subject,
      grade: form.value.grade,
      topic: form.value.topic,
      class_hours: form.value.class_hours,
      course_type: form.value.course_type,
      student_profile: form.value.student_profile,
      use_textbook_rag: form.value.use_textbook_rag,
    })
    current.value = resp
    ElMessage.success('教案生成成功')
    await loadList()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '生成失败，请重试')
  } finally {
    loading.value = false
  }
}

async function loadList() {
  plans.value = await listLessons({ limit: 50 })
}

function selectPlan(row: LessonPlan) {
  current.value = row
}

function downloadPlan(plan: LessonPlan, fmt: 'md' | 'docx') {
  exportLesson(plan.id, fmt).then((blob) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${plan.topic}-教案.${fmt === 'docx' ? 'docx' : 'md'}`
    a.click()
    URL.revokeObjectURL(url)
  })
}

onMounted(loadList)
</script>

<style scoped>
.card-title {
  font-weight: 600;
}
.card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.lesson-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.empty {
  text-align: center;
  color: #98a1b0;
  padding: 120px 0;
}
.lesson-head {
  text-align: center;
}
.lesson-meta {
  color: #5b6472;
  font-size: 13px;
}
.lesson-content h4 {
  color: #15181f;
  margin: 16px 0 8px;
}
.lesson-content ol {
  padding-left: 22px;
  line-height: 1.9;
}
.kv-item {
  margin-bottom: 4px;
  line-height: 1.9;
  color: #15181f;
}
.step {
  padding: 10px 12px;
  margin-bottom: 10px;
  background: #f5f7fa;
  border-radius: 6px;
}
.step-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.step-dur {
  font-size: 12px;
  color: #98a1b0;
}
.step-content {
  margin: 0;
  line-height: 1.9;
  color: #15181f;
  white-space: pre-wrap;
}
.rag-tip {
  margin-left: 8px;
  font-size: 12px;
  color: #98a1b0;
}
.plain-text {
  line-height: 1.9;
  color: #15181f;
  white-space: pre-wrap;
}
</style>
