<template>
  <div class="resource-grid">
    <el-skeleton v-if="loading" :rows="4" animated />
    <el-empty v-else-if="!docs.length" description="暂无资源" />
    <div v-else class="grid">
      <div v-for="d in docs" :key="d.id" class="cell" @click="$emit('read', d)">
        <div class="cell-top">
          <span class="badge" :class="'badge-' + typeKey(d.file_type)">
            {{ typeLabel(d.file_type) }}
          </span>
          <span class="ext">{{ (d.file_type || '').toUpperCase() }}</span>
        </div>
        <div class="cell-name" :title="d.doc_name">{{ displayName(d.doc_name) }}</div>
        <div class="cell-meta">{{ d.created_at || '' }}</div>
        <div class="cell-actions">
          <el-button size="small" text type="primary" @click.stop="$emit('read', d)">阅读</el-button>
          <DownloadButton size="small" @click.stop @download="$emit('download', d)" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { KbDocument } from '@/api/modules/kb'
import DownloadButton from '@/components/DownloadButton.vue'

defineProps<{ docs: KbDocument[]; loading?: boolean }>()
defineEmits<{ (e: 'read', d: KbDocument): void; (e: 'download', d: KbDocument): void }>()

function displayName(n: string) {
  return (n || '').replace(/^\d{9,}_/, '')
}

function typeKey(ft: string) {
  const f = (ft || '').toLowerCase()
  if (f === 'pdf') return 'pdf'
  if (f.includes('doc')) return 'word'
  if (f.includes('xls')) return 'excel'
  if (['png', 'jpg', 'jpeg'].includes(f)) return 'img'
  return 'text'
}

function typeLabel(ft: string) {
  const f = (ft || '').toLowerCase()
  if (f === 'pdf') return 'PDF'
  if (f.includes('doc')) return '文档'
  if (f.includes('xls')) return '表格'
  if (['png', 'jpg', 'jpeg'].includes(f)) return '图片'
  return '文本'
}
</script>

<style scoped>
.resource-grid {
  min-height: 120px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}
.cell {
  border: 1px solid #e7eaf0;
  border-radius: 8px;
  padding: 14px;
  cursor: pointer;
  background: #fff;
  transition: box-shadow 150ms ease, border-color 150ms ease;
}
.cell:hover {
  border-color: #d9d8d4;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
.cell-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  color: #fff;
}
.badge-pdf {
  background: #e5484d;
}
.badge-word {
  background: #2f5bd8;
}
.badge-excel {
  background: #21a366;
}
.badge-img {
  background: #f0a035;
}
.badge-text {
  background: #98a1b0;
}
.ext {
  font-size: 11px;
  color: #98a1b0;
}
.cell-name {
  font-size: 14px;
  font-weight: 600;
  color: #15181f;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  min-height: 40px;
  line-height: 1.4;
}
.cell-meta {
  font-size: 12px;
  color: #98a1b0;
  margin-top: 6px;
}
.cell-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 12px;
}
</style>