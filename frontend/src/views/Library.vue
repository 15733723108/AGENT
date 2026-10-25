<template>
  <div class="library-page">
    <el-card>
      <template #header>
        <div class="card-title-row">
          <span class="card-title">电子书 / 试卷查阅</span>
          <div class="actions">
            <el-button v-if="isAdmin" size="small" type="primary" @click="openUpload">
              <el-icon style="margin-right: 4px"><Upload /></el-icon>添加资源
            </el-button>
            <el-button size="small" text type="primary" @click="loadAll">刷新</el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="tab" @tab-change="loadCurrent">
        <el-tab-pane label="电子书" name="book">
          <ResourceGrid :docs="books" :loading="loading" @read="openRead" @download="doDownload" />
        </el-tab-pane>
        <el-tab-pane label="电子试卷" name="paper">
          <ResourceGrid :docs="papers" :loading="loading" @read="openRead" @download="doDownload" />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 在线查阅抽屉 -->
    <el-drawer v-model="readVisible" :title="current?.doc_name" size="60%">
      <div class="read-meta">
        <el-tag size="small" type="info">{{ current?.file_type }}</el-tag>
        <el-tag v-if="current" size="small" type="success">{{ categoryLabel(current.category) }}</el-tag>
      </div>
      <div class="read-body">
        <el-skeleton v-if="reading" :rows="12" animated />
        <img v-else-if="imageUrl" :src="imageUrl" class="read-image" alt="资源图片" />
        <pre v-else-if="content" class="read-content">{{ content }}</pre>
        <el-empty v-else description="该文档暂无预览内容，可下载原文件查看" />
      </div>
      <template #footer>
        <DownloadButton @download="doDownload(current!)" />
      </template>
    </el-drawer>

    <!-- 管理员上传 -->
    <el-dialog v-model="uploadVisible" title="添加资源" width="480px">
      <el-form label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="uploadName" placeholder="请输入资源名称" maxlength="255" />
        </el-form-item>
        <el-form-item label="分类">
          <el-radio-group v-model="uploadCategory">
            <el-radio value="教材">电子书</el-radio>
            <el-radio value="试卷">电子试卷</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="图片">
          <el-upload
            drag
            :auto-upload="false"
            :limit="1"
            accept=".png,.jpg,.jpeg"
            :on-change="onFileChange"
          >
            <el-icon size="32" color="#98a1b0"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽图片到此处，或 <em>点击选择</em></div>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="!selectedFile || !uploadName.trim()" @click="doUpload">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, UploadFilled } from '@element-plus/icons-vue'
import ResourceGrid from '@/components/ResourceGrid.vue'
import DownloadButton from '@/components/DownloadButton.vue'
import { downloadDocument, getDocumentContent, libraryUpload, listDocuments } from '@/api/modules/kb'
import type { KbDocument } from '@/api/modules/kb'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.role === 'admin')

const tab = ref('book')
const books = ref<KbDocument[]>([])
const papers = ref<KbDocument[]>([])
const loading = ref(false)

const readVisible = ref(false)
const reading = ref(false)
const content = ref('')
const imageUrl = ref('')
const current = ref<KbDocument | null>(null)

const uploadVisible = ref(false)
const uploading = ref(false)
const uploadName = ref('')
const uploadCategory = ref('教材')
const selectedFile = ref<File | null>(null)

const CATEGORIES = { book: '教材', paper: '试卷' } as const

function categoryLabel(c: string) {
  return c === '试卷' ? '电子试卷' : '电子书'
}

async function loadCurrent() {
  loading.value = true
  try {
    const category = CATEGORIES[tab.value as keyof typeof CATEGORIES]
    const docs = await listDocuments({ category, active_only: true, limit: 500 })
    if (tab.value === 'book') books.value = docs
    else papers.value = docs
  } finally {
    loading.value = false
  }
}

function loadAll() {
  return loadCurrent()
}

function isImageType(ft?: string) {
  return ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes((ft || '').toLowerCase())
}

function onFileChange(file: any) {
  selectedFile.value = file.raw || null
}

function openUpload() {
  uploadCategory.value = CATEGORIES[tab.value as keyof typeof CATEGORIES]
  uploadName.value = ''
  selectedFile.value = null
  uploadVisible.value = true
}

async function doUpload() {
  if (!selectedFile.value || !uploadName.value.trim()) return
  uploading.value = true
  try {
    await libraryUpload(selectedFile.value, uploadName.value.trim(), uploadCategory.value)
    ElMessage.success('资源已保存')
    uploadVisible.value = false
    selectedFile.value = null
    await loadAll()
  } finally {
    uploading.value = false
  }
}

async function openRead(doc: KbDocument) {
  current.value = doc
  readVisible.value = true
  reading.value = true
  content.value = ''
  imageUrl.value = ''
  try {
    if (isImageType(doc.file_type)) {
      const blob = await downloadDocument(doc.id)
      imageUrl.value = URL.createObjectURL(blob)
    } else {
      const res = await getDocumentContent(doc.id)
      content.value = res.content || ''
    }
  } finally {
    reading.value = false
  }
}

async function doDownload(doc: KbDocument) {
  const blob = await downloadDocument(doc.id)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = (doc.doc_name || '资源').replace(/^\d{9,}_/, '')
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(loadAll)
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
.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.read-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.read-body {
  min-height: 200px;
}
.read-image {
  max-width: 100%;
  border-radius: 6px;
  border: 1px solid #e7eaf0;
}
.read-content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.8;
  font-size: 14px;
  color: #15181f;
  background: #f5f7fa;
  border: 1px solid #e7eaf0;
  border-radius: 6px;
  padding: 16px;
  max-height: 70vh;
  overflow: auto;
}
</style>