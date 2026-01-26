<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { generatePicks, listPicks, type PickRow } from '../api/picks'

function ymdToday(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

function fmt(v: unknown, digits = 2): string {
  if (v == null) return '-'
  const n = Number(v)
  if (!Number.isFinite(n)) return '-'
  return n.toFixed(digits)
}

const loading = ref(false)
const generating = ref(false)
const rows = ref<PickRow[]>([])

const paging = reactive({
  limit: 200,
  offset: 0,
})

const form = reactive({
  date: ymdToday(),
  sector: '',
  minMention: 4,
  minChange: 5,
  minTurnover: 5,
  maxSectors: 30,
})

const stats = computed(() => {
  const sectors = new Set(rows.value.map((r) => r.sector))
  return {
    rows: rows.value.length,
    sectors: sectors.size,
  }
})

function _safeFilenamePart(v: string): string {
  return (v || '')
    .trim()
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\s+/g, '_')
    .slice(0, 80)
}

async function onExportExcel() {
  if (!rows.value.length) {
    ElMessage.warning('当前没有可导出的数据')
    return
  }
  try {
    const XLSX = await import('xlsx')
    const data = rows.value.map((r) => ({
      日期: r.day,
      板块: r.sector,
      代码: r.stock_code,
      名称: r.stock_name,
      最新价: r.latest_price ?? '',
      涨跌幅: r.pct_change ?? '',
      换手率: r.turnover_rate ?? '',
      今开: r.open_price ?? '',
      昨收: r.prev_close ?? '',
      'PE(动)': r.pe_dynamic ?? '',
      PB: r.pb ?? '',
    }))

    const ws = XLSX.utils.json_to_sheet(data)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '选股')

    const datePart = _safeFilenamePart(form.date)
    const sectorPart = form.sector.trim() ? `_${_safeFilenamePart(form.sector)}` : ''
    const filename = `板块选股_${datePart}${sectorPart}.xlsx`
    XLSX.writeFile(wb, filename)
  } catch (e: any) {
    ElMessage.error(e?.message || String(e))
  }
}

async function fetchList() {
  loading.value = true
  try {
    const resp = await listPicks({
      date: form.date,
      sector: form.sector.trim() || undefined,
      limit: paging.limit,
      offset: paging.offset,
    })
    if (!resp.success) throw new Error(String(resp.error))
    rows.value = resp.data?.rows || []
  } catch (e: any) {
    const serverMsg = e?.response?.data?.error || e?.response?.data?.message
    ElMessage.error(serverMsg || e?.message || String(e))
  } finally {
    loading.value = false
  }
}

async function onGenerate() {
  generating.value = true
  try {
    const resp = await generatePicks({
      date: form.date,
      minMention: form.minMention,
      minChange: form.minChange,
      minTurnover: form.minTurnover,
      maxSectors: form.maxSectors,
    })
    if (!resp.success) throw new Error(String(resp.error))
    rows.value = resp.data?.rows || []
    ElMessage.success(
      `已生成：${resp.data?.generated || 0} 条；板块匹配：${resp.data?.sectors_matched || 0}/${resp.data?.sectors_total || 0}`,
    )
  } catch (e: any) {
    const serverMsg = e?.response?.data?.error || e?.response?.data?.message
    ElMessage.error(serverMsg || e?.message || String(e))
  } finally {
    generating.value = false
  }
}

function onSearch() {
  paging.offset = 0
  fetchList()
}

function onPrev() {
  paging.offset = Math.max(0, paging.offset - paging.limit)
  fetchList()
}

function onNext() {
  paging.offset = paging.offset + paging.limit
  fetchList()
}

onMounted(fetchList)
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <el-form inline @submit.prevent>
        <el-form-item label="日期">
          <el-date-picker
            v-model="form.date"
            type="date"
            value-format="YYYY-MM-DD"
            format="YYYY-MM-DD"
            style="width: 160px"
            @change="onSearch"
          />
        </el-form-item>

        <el-form-item label="板块(可空)">
          <el-input v-model="form.sector" placeholder="精确匹配" style="width: 220px" clearable @keyup.enter="onSearch" />
        </el-form-item>

        <el-form-item label="提及>=">
          <el-input-number v-model="form.minMention" :min="1" :max="99" />
        </el-form-item>

        <el-form-item label="涨幅%>=">
          <el-input-number v-model="form.minChange" :min="-50" :max="50" :step="0.5" />
        </el-form-item>

        <el-form-item label="换手%>=">
          <el-input-number v-model="form.minTurnover" :min="0" :max="100" :step="0.5" />
        </el-form-item>

        <el-form-item label="最多板块">
          <el-input-number v-model="form.maxSectors" :min="1" :max="200" />
        </el-form-item>

        <el-form-item>
          <el-button :loading="loading" @click="fetchList">刷新</el-button>
          <el-button type="primary" :loading="generating" @click="onGenerate">生成选股</el-button>
          <el-button :disabled="!rows.length" @click="onExportExcel">导出Excel</el-button>
        </el-form-item>
      </el-form>

      <div class="stats">
        <el-text type="info">记录={{ stats.rows }}, 板块={{ stats.sectors }}, offset={{ paging.offset }}, limit={{ paging.limit }}</el-text>
      </div>
    </div>

    <el-table :data="rows" v-loading="loading || generating" border style="width: 100%">
      <el-table-column prop="sector" label="板块" min-width="160" show-overflow-tooltip />
      <el-table-column prop="stock_code" label="代码" width="110" />
      <el-table-column prop="stock_name" label="名称" min-width="140" show-overflow-tooltip />
      <el-table-column label="最新价" width="110">
        <template #default="scope">
          {{ fmt(scope.row.latest_price, 2) }}
        </template>
      </el-table-column>
      <el-table-column label="涨跌幅%" width="110">
        <template #default="scope">
          <el-text :type="Number(scope.row.pct_change) >= 0 ? 'danger' : 'success'">{{ fmt(scope.row.pct_change, 2) }}</el-text>
        </template>
      </el-table-column>
      <el-table-column label="换手%" width="110">
        <template #default="scope">
          {{ fmt(scope.row.turnover_rate, 2) }}
        </template>
      </el-table-column>
      <el-table-column label="今开" width="110">
        <template #default="scope">
          {{ fmt(scope.row.open_price, 2) }}
        </template>
      </el-table-column>
      <el-table-column label="昨收" width="110">
        <template #default="scope">
          {{ fmt(scope.row.prev_close, 2) }}
        </template>
      </el-table-column>
      <el-table-column label="PE(动)" width="110">
        <template #default="scope">
          {{ fmt(scope.row.pe_dynamic, 2) }}
        </template>
      </el-table-column>
      <el-table-column label="PB" width="100">
        <template #default="scope">
          {{ fmt(scope.row.pb, 2) }}
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-button :disabled="paging.offset <= 0" @click="onPrev">上一页</el-button>
      <el-button :disabled="rows.length < paging.limit" @click="onNext">下一页</el-button>
    </div>
  </div>
</template>

<style scoped>
.page {
  padding: 16px 0;
}

.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.stats {
  padding-top: 6px;
}

.pager {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
}
</style>
