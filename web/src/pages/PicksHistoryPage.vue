<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteSectors, listSectorDates, type SectorDateRow } from '../api/sectors'

const router = useRouter()
const loading = ref(false)
const rows = ref<SectorDateRow[]>([])

async function fetchList() {
  loading.value = true
  try {
    const resp = await listSectorDates()
    if (!resp.success) throw new Error(String(resp.error))
    rows.value = resp.data?.rows || []
  } catch (e: any) {
    const serverMsg = e?.response?.data?.error || e?.response?.data?.message
    ElMessage.error(serverMsg || e?.message || String(e))
  } finally {
    loading.value = false
  }
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return `${date.getFullYear()}年${String(date.getMonth() + 1).padStart(2, '0')}月${String(date.getDate()).padStart(2, '0')}日`
}

function onViewSectors(date: string) {
  router.push({ path: '/sectors', query: { date } })
}

async function onDelete(row: SectorDateRow) {
  try {
    await ElMessageBox.confirm(
      `确定要删除 ${formatDate(row.day)} 的板块总结内容吗？`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
      },
    )
  } catch (e) {
    // cancelled
    return
  }

  try {
    const resp = await deleteSectors(row.day)
    if (!resp.success) throw new Error(String(resp.error))

    const deleted = resp.data?.deleted || 0
    ElMessage.success(`已删除 ${formatDate(row.day)} 的 ${deleted} 条板块总结`)

    // Refresh list
    await fetchList()
  } catch (e: any) {
    const serverMsg = e?.response?.data?.error || e?.response?.data?.message
    ElMessage.error(serverMsg || e?.message || String(e))
  }
}

onMounted(fetchList)
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <el-form inline @submit.prevent>
        <el-form-item>
          <el-text tag="b" size="large">历史选股</el-text>
        </el-form-item>
      </el-form>

      <div class="actions">
        <el-button :loading="loading" @click="fetchList">刷新</el-button>
      </div>
    </div>

    <el-table :data="rows" v-loading="loading" border style="width: 100%">
      <el-table-column prop="day" label="日期" width="180">
        <template #default="scope">
          {{ formatDate(scope.row.day) }}
        </template>
      </el-table-column>
      <el-table-column label="行业列表" min-width="400">
        <template #default="scope">
          <div class="sectors">
            <template v-if="scope.row.sectors?.length">
              <el-tag
                v-for="(sector, idx) in scope.row.sectors"
                :key="idx"
                class="sector-tag"
                type="info"
                effect="plain"
              >
                {{ sector }}
              </el-tag>
              <el-text v-if="scope.row.sector_count > 3" type="info">
                等 {{ scope.row.sector_count }} 个板块
              </el-text>
            </template>
            <el-text v-else type="info">-</el-text>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="scope">
          <el-button type="primary" size="small" @click="onViewSectors(scope.row.day)">
            查看详情
          </el-button>
          <el-button type="danger" size="small" @click="onDelete(scope.row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.page {
  padding: 16px 0;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.sectors {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.sector-tag {
  cursor: pointer;
}

.sector-tag:hover {
  opacity: 0.8;
}
</style>
