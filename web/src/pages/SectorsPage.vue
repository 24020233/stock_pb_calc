<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { generateSectors, listSectors, type SectorRow } from '../api/sectors'

function ymdToday(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

const loading = ref(false)
const generating = ref(false)
const rows = ref<SectorRow[]>([])

const form = reactive({
  date: ymdToday(),
})

const totalMentions = computed(() => rows.value.reduce((acc, r) => acc + Number(r.mention_count || 0), 0))

async function fetchList() {
  loading.value = true
  try {
    const resp = await listSectors({ date: form.date })
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
    const resp = await generateSectors({ date: form.date })
    if (!resp.success) throw new Error(String(resp.error))
    rows.value = resp.data?.rows || []
    ElMessage.success(`已生成：${resp.data?.generated || 0} 个板块；抓取失败：${resp.data?.fetch_failures || 0} 篇`)
  } catch (e: any) {
    const serverMsg = e?.response?.data?.error || e?.response?.data?.message
    ElMessage.error(serverMsg || e?.message || String(e))
  } finally {
    generating.value = false
  }
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
            @change="fetchList"
          />
        </el-form-item>
        <el-form-item>
          <el-button :loading="loading" @click="fetchList">刷新</el-button>
          <el-button type="primary" :loading="generating" @click="onGenerate">生成板块</el-button>
        </el-form-item>
      </el-form>

      <div class="stats">
        <el-text type="info">板块数={{ rows.length }}, 提及总数={{ totalMentions }}</el-text>
      </div>
    </div>

    <el-table :data="rows" v-loading="loading || generating" border style="width: 100%">
      <el-table-column prop="sector" label="板块" min-width="220" />
      <el-table-column prop="mention_count" label="提及(篇)" width="120" />
      <el-table-column label="涉及文章" min-width="520">
        <template #default="scope">
          <div class="articles">
            <template v-if="scope.row.articles?.length">
              <el-tag v-for="a in scope.row.articles" :key="a.id" class="article-tag" effect="plain">
                <el-link :href="a.url" target="_blank" type="primary">#{{ a.id }} {{ a.title || a.url }}</el-link>
              </el-tag>
            </template>
            <el-text v-else type="info">-</el-text>
          </div>
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.stats {
  padding-top: 6px;
}

.articles {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.article-tag {
  max-width: 100%;
}
</style>
