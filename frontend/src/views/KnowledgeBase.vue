<template>
  <div class="kb-page">
    <el-card>
      <template #header>
        <div class="card-title-row">
          <span class="card-title">知识库导入</span>
          <span class="card-hint">导入内容将用于「学校信息问答 / 通用问答」的检索</span>
        </div>
      </template>

      <el-tabs v-model="tab">
        <el-tab-pane label="粘贴文本导入" name="text">
          <el-form label-width="80px" class="import-form">
            <el-form-item label="标题">
              <el-input v-model="textForm.title" placeholder="如：作息时间表（2026 年秋季）" maxlength="255" />
            </el-form-item>
            <el-form-item label="知识域">
              <el-select v-model="textForm.category" filterable allow-create default-first-option style="width: 240px">
                <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
            <el-form-item label="内容">
              <el-input
                v-model="textForm.content"
                type="textarea"
                :rows="10"
                placeholder="将需要录入知识库的文本粘贴到此处…"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="textLoading"
                :disabled="!textForm.title.trim() || !textForm.content.trim()"
                @click="doImportText"
              >
                导入知识库
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="上传 Word 文档" name="file">
          <el-upload
            drag
            :auto-upload="false"
            :limit="1"
            accept=".docx,.doc,.txt,.md,.pdf"
            :file-list="fileList"
            :on-change="onFileChange"
            :on-remove="onFileRemove"
          >
            <el-icon size="32" color="#98a1b0"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽 Word 文档到此处，或 <em>点击选择</em></div>
          </el-upload>
          <el-form label-width="80px" class="import-form">
            <el-form-item label="知识域">
              <el-select v-model="fileCategory" filterable allow-create default-first-option style="width: 240px">
                <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="fileLoading" :disabled="!selectedFile" @click="doImportFile">
                导入知识库
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-card class="list-card">
      <template #header>
        <div class="card-title-row">
          <span class="card-title">知识库文档</span>
          <el-button size="small" text type="primary" @click="loadDocs">刷新</el-button>
        </div>
      </template>
      <el-table :data="docs" v-loading="loading" size="small" empty-text="暂无文档，请先导入">
        <el-table-column prop="doc_name" label="名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="category" label="知识域" width="100" />
        <el-table-column prop="file_type" label="类型" width="80" />
        <el-table-column prop="chunk_count" label="分块" width="70" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '有效' : '已废弃' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button v-if="row.is_active" size="small" text type="danger" @click="doDeactivate(row)">废弃</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { deactivateDocument, importText, listDocuments, uploadDocument } from '@/api/modules/kb'
import type { KbDocument } from '@/api/modules/kb'

const CATEGORIES = ['招生', '作息', '制度', '通知', '教材', '试卷', '其他']

const tab = ref('text')
const docs = ref<KbDocument[]>([])
const loading = ref(false)

const textForm = reactive({ title: '', category: '制度', content: '' })
const textLoading = ref(false)

const fileCategory = ref('制度')
const selectedFile = ref<File | null>(null)
const fileList = ref<{ name: string }[]>([])
const fileLoading = ref(false)

function onFileChange(file: any) {
  selectedFile.value = file.raw || null
}

function onFileRemove() {
  selectedFile.value = null
}

async function loadDocs() {
  loading.value = true
  try {
    docs.value = await listDocuments({ active_only: false, limit: 500 })
  } finally {
    loading.value = false
  }
}

async function doImportText() {
  if (!textForm.title.trim() || !textForm.content.trim()) return
  textLoading.value = true
  try {
    const r = await importText({
      title: textForm.title.trim(),
      category: textForm.category,
      content: textForm.content,
    })
    ElMessage.success(`已导入「${r.doc_name}」，共 ${r.chunk_count} 个分块`)
    textForm.title = ''
    textForm.content = ''
    await loadDocs()
  } finally {
    textLoading.value = false
  }
}

async function doImportFile() {
  if (!selectedFile.value) return
  fileLoading.value = true
  try {
    const r = await uploadDocument(selectedFile.value, fileCategory.value)
    ElMessage.success(`已导入「${r.doc_name}」，共 ${r.chunk_count} 个分块`)
    selectedFile.value = null
    fileList.value = []
    await loadDocs()
  } finally {
    fileLoading.value = false
  }
}

async function doDeactivate(row: KbDocument) {
  await deactivateDocument(row.id)
  ElMessage.success('已废弃该文档')
  await loadDocs()
}

onMounted(loadDocs)
</script>

<style scoped>
.kb-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card-title {
  font-weight: 600;
}
.card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-hint {
  font-size: 12px;
  color: #98a1b0;
}
.import-form {
  margin-top: 8px;
  max-width: 720px;
}
.list-card {
  margin-top: 0;
}
</style>