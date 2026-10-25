<template>
  <div class="review-page">
    <el-card>
      <template #header>
        <div class="card-title-row">
          <span class="card-title">教师注册审核</span>
          <el-button size="small" text type="primary" @click="loadList">刷新</el-button>
        </div>
      </template>

      <el-table :data="list" v-loading="loading" size="small" empty-text="暂无待审核的教师注册">
        <el-table-column prop="username" label="账号" min-width="140" show-overflow-tooltip />
        <el-table-column prop="display_name" label="姓名" width="120" />
        <el-table-column prop="phone" label="手机号" width="140">
          <template #default="{ row }">{{ row.phone || '—' }}</template>
        </el-table-column>
        <el-table-column label="申请时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="doApprove(row)">通过</el-button>
            <el-button size="small" type="danger" plain @click="doReject(row)">拒绝</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { approveTeacher, listPendingTeachers, rejectTeacher } from '@/api/modules/auth'
import type { PendingTeacher } from '@/api/modules/auth'

const list = ref<PendingTeacher[]>([])
const loading = ref(false)

function formatTime(v?: string) {
  if (!v) return '—'
  return String(v).replace('T', ' ').slice(0, 19)
}

async function loadList() {
  loading.value = true
  try {
    list.value = await listPendingTeachers()
  } finally {
    loading.value = false
  }
}

async function doApprove(row: PendingTeacher) {
  const r = await approveTeacher(row.id)
  ElMessage.success(r.message || '已通过审核')
  await loadList()
}

async function doReject(row: PendingTeacher) {
  await ElMessageBox.confirm(`确认拒绝并删除「${row.display_name}（${row.username}）」的教师注册申请？`, '拒绝申请', {
    type: 'warning',
    confirmButtonText: '拒绝',
    cancelButtonText: '取消',
  })
  const r = await rejectTeacher(row.id)
  ElMessage.success(r.message || '已拒绝')
  await loadList()
}

onMounted(loadList)
</script>

<style scoped>
.review-page {
  display: flex;
  flex-direction: column;
}
.card-title {
  font-weight: 600;
}
.card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>