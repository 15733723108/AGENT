<template>
  <div class="exam-page">
    <el-card>
      <template #header>
        <div class="card-title-row">
          <span class="card-title">智能试卷研判</span>
          <el-button size="small" text type="primary" @click="loadExams">刷新列表</el-button>
        </div>
      </template>

      <el-tabs v-model="tab">
        <el-tab-pane label="上传试卷" name="upload">
          <div class="upload-area">
            <el-upload
              drag
              :auto-upload="false"
              :limit="1"
              accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md,.png,.jpg,.jpeg"
              :on-change="onFileChange"
            >
              <el-icon size="40" color="#98a1b0"><UploadFilled /></el-icon>
              <div class="el-upload__text">拖拽试卷到此处，或 <em>点击选择文件</em></div>
              <div class="el-upload__tip">支持 PDF / Word / Excel / 图片（扫描件 OCR）</div>
            </el-upload>
            <el-form inline class="upload-form">
              <el-form-item label="试卷名称">
                <el-input v-model="uploadMeta.exam_name" placeholder="留空取文件名" style="width: 220px" />
              </el-form-item>
              <el-form-item label="学科">
                <el-input v-model="uploadMeta.subject" placeholder="如：数学" style="width: 140px" />
              </el-form-item>
              <el-form-item label="年级">
                <el-input v-model="uploadMeta.grade" placeholder="如：三年级" style="width: 140px" />
              </el-form-item>
              <el-button type="primary" :loading="uploading" :disabled="!selectedFile" @click="doUpload">上传并解析</el-button>
            </el-form>
          </div>
          <el-divider><span class="or">或</span></el-divider>
          <div class="paste-area">
            <el-input v-model="pasteText" type="textarea" :rows="4" placeholder="直接粘贴试卷全文（题目之间用空行分隔）" />
            <div class="paste-row">
              <el-input v-model="pasteMeta.exam_name" placeholder="试卷名称" style="width: 200px" />
              <el-input v-model="pasteMeta.subject" placeholder="学科" style="width: 130px" />
              <el-input v-model="pasteMeta.grade" placeholder="年级" style="width: 130px" />
              <el-button type="success" :loading="creating" :disabled="pasteText.trim().length < 10" @click="doPaste">创建试卷</el-button>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="试卷列表" name="list">
          <el-table :data="exams" @row-click="openExam">
            <el-table-column prop="exam_name" label="试卷名称" min-width="160" show-overflow-tooltip />
            <el-table-column prop="subject" label="学科" width="90" />
            <el-table-column prop="grade" label="年级" width="90" />
            <el-table-column prop="question_count" label="题数" width="70" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="170" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 试卷详情 -->
    <el-card v-if="detail" style="margin-top: 16px">
      <template #header>
        <div class="card-title-row">
          <span class="card-title">{{ detail.exam.exam_name }}（{{ detail.exam.question_count }} 题）</span>
          <div>
            <el-button size="small" type="primary" :loading="analyzing" @click="doAnalyze">逐题智能分析</el-button>
            <el-button size="small" type="success" @click="openReport">查看研判报告</el-button>
            <el-button size="small" @click="closeDetail">关闭</el-button>
          </div>
        </div>
      </template>
      <el-collapse>
        <el-collapse-item v-for="q in detail.questions" :key="q.question_no" :name="q.question_no">
          <template #title>
            <div class="q-title">
              <span class="q-no">{{ q.question_no }}.</span>
              <span class="q-text">{{ q.question_text.slice(0, 80) }}</span>
              <el-tag v-if="q.question_type" size="small" type="info">{{ q.question_type }}</el-tag>
            </div>
          </template>
          <div class="q-body">
            <div class="q-field"><b>题干：</b>{{ q.question_text }}</div>
            <div v-if="q.answer" class="q-field"><b>参考答案：</b>{{ q.answer }}</div>
            <div v-if="q.analysis" class="q-field"><b>解析：</b>{{ q.analysis }}</div>
            <div v-if="q.knowledge_points?.length" class="q-field">
              <b>知识点：</b>
              <el-tag v-for="(kp, i) in q.knowledge_points" :key="i" size="small" style="margin-right: 6px">{{ kp }}</el-tag>
            </div>
            <div v-if="q.difficulty" class="q-field"><b>难度：</b>{{ '★'.repeat(q.difficulty) }}{{ '☆'.repeat(5 - q.difficulty) }}</div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- 研判报告 -->
    <el-drawer v-model="reportVisible" title="研判报告" size="55%">
      <div class="report-body">
        <div v-if="reportMd" class="report-md" v-html="renderMd(reportMd)"></div>
        <el-empty v-else description="暂无报告，请先执行逐题智能分析" />
      </div>
      <template #footer>
        <DownloadButton label="导出" done-text="已导出" @download="downloadReport" />
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DownloadButton from '@/components/DownloadButton.vue'
import { analyzeExam, exportExamReport, getExamDetail, getExamReport, listExams, uploadExam, createExamWithText } from '@/api/modules/exam'
import type { ExamItem } from '@/types'

const tab = ref('upload')
const exams = ref<ExamItem[]>([])
const detail = ref<{ exam: ExamItem; questions: any[] } | null>(null)
const reportVisible = ref(false)
const reportMd = ref('')
const analyzing = ref(false)
const uploading = ref(false)
const creating = ref(false)

const selectedFile = ref<File | null>(null)
const uploadMeta = ref({ exam_name: '', subject: '数学', grade: '三年级' })
const pasteText = ref('')
const pasteMeta = ref({ exam_name: '三年级数学期中试卷', subject: '数学', grade: '三年级' })

function onFileChange(file: any) {
  selectedFile.value = file.raw || null
}

async function doUpload() {
  if (!selectedFile.value) return
  uploading.value = true
  try {
    await uploadExam(selectedFile.value, uploadMeta.value)
    ElMessage.success('上传解析成功')
    tab.value = 'list'
    await loadExams()
  } finally {
    uploading.value = false
  }
}

async function doPaste() {
  creating.value = true
  try {
    const exam = await createExamWithText({ ...pasteMeta.value, paper_text: pasteText.value })
    ElMessage.success(`创建成功，共 ${exam.question_count} 题`)
    tab.value = 'list'
    pasteText.value = ''
    await loadExams()
  } finally {
    creating.value = false
  }
}

async function loadExams() {
  exams.value = await listExams({ limit: 100 })
}

async function openExam(row: ExamItem) {
  detail.value = await getExamDetail(row.id)
}

async function doAnalyze() {
  if (!detail.value) return
  analyzing.value = true
  try {
    await analyzeExam(detail.value.exam.id)
    ElMessage.success('分析完成')
    detail.value = await getExamDetail(detail.value.exam.id)
    await loadExams()
  } finally {
    analyzing.value = false
  }
}

async function openReport() {
  if (!detail.value) return
  const rep = await getExamReport(detail.value.exam.id)
  reportMd.value = rep.report_md
  reportVisible.value = true
}

function downloadReport() {
  if (!detail.value) return
  exportExamReport(detail.value.exam.id).then((blob) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${detail.value!.exam.exam_name}-研判报告.docx`
    a.click()
    URL.revokeObjectURL(url)
  })
}

function closeDetail() {
  detail.value = null
}

function renderMd(text: string) {
  return marked.parse(text || '') as string
}

function statusText(s: string) {
  return ({ pending: '待分析', analyzing: '分析中', done: '已完成', failed: '失败' } as Record<string, string>)[s] || s
}
function statusType(s: string) {
  return ({ pending: 'info', analyzing: 'warning', done: 'success', failed: 'danger' } as Record<string, any>)[s] || 'info'
}

onMounted(loadExams)
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
.upload-area {
  padding: 20px 0 10px;
}
.upload-form {
  margin-top: 16px;
}
.or {
  color: #98a1b0;
  font-size: 12px;
}
.paste-area {
  margin-top: 4px;
}
.paste-row {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  align-items: center;
}
.q-title {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.q-no {
  font-weight: 600;
  color: #15181f;
}
.q-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.q-body {
  line-height: 1.8;
  font-size: 14px;
}
.q-field {
  margin-bottom: 6px;
}
.report-md :deep(h1), .report-md :deep(h2), .report-md :deep(h3) {
  color: #15181f;
}
.report-md :deep(p) {
  line-height: 1.8;
}
.report-md :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
}
.report-md :deep(td), .report-md :deep(th) {
  border: 1px solid #e7eaf0;
  padding: 6px 10px;
}
</style>
