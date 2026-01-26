<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listAccounts } from '../api/accounts'
import { listSeeds } from '../api/seeds'
import type { WxArticleSeed, WxMpAccount } from '../api/types'

const loading = ref(false)
const rows = ref<WxArticleSeed[]>([])

const accountNameById = ref<Record<number, string>>({})

const paging = reactive({
  limit: 50,
  offset: 0,
})

const filters = reactive({
  account_id: '' as '' | string,
  q: '',
  is_deleted: '' as '' | '1' | '0',
})

async function fetchAccountsMap() {
  try {
    // Best-effort: pull a reasonably large page for mapping.
    const resp = await listAccounts({ limit: 500, offset: 0 })
    if (!resp.success) throw new Error(String(resp.error))

    const map: Record<number, string> = {}
    for (const a of resp.data as WxMpAccount[]) {
      map[a.id] = a.mp_nickname
    }
    accountNameById.value = map
  } catch (e: any) {
    // Non-fatal: list can still render using account_id.
    const serverMsg = e?.response?.data?.error || e?.response?.data?.message
    ElMessage.error(serverMsg || e?.message || String(e))
  }
}

function accountName(accountId: number): string {
  return accountNameById.value[accountId] || `#${accountId}`
}

async function fetchList() {
  loading.value = true
  try {
    const accountId = filters.account_id.trim()
    const resp = await listSeeds({
      limit: paging.limit,
      offset: paging.offset,
      q: filters.q || undefined,
      account_id: accountId ? Number(accountId) : undefined,
      is_deleted: filters.is_deleted === '' ? undefined : (Number(filters.is_deleted) as 0 | 1),
    })
    if (!resp.success) throw new Error(String(resp.error))
    rows.value = resp.data
  } catch (e: any) {
    const serverMsg = e?.response?.data?.error || e?.response?.data?.message
    const msg = serverMsg || e?.message || String(e)
    ElMessage.error(msg)
  } finally {
    loading.value = false
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
onMounted(fetchAccountsMap)
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <el-form inline @submit.prevent>
        <el-form-item label="account_id">
          <el-input v-model="filters.account_id" placeholder="可空" style="width: 140px" @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filters.q" placeholder="标题/摘要" clearable @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item label="删除">
          <el-select v-model="filters.is_deleted" placeholder="全部" style="width: 120px">
            <el-option label="全部" value="" />
            <el-option label="正常" value="0" />
            <el-option label="已删除" value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onSearch">查询</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-table :data="rows" v-loading="loading" border style="width: 100%">
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column label="公众号" min-width="160">
        <template #default="scope">
          <el-text>{{ accountName(scope.row.account_id) }}</el-text>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="320" show-overflow-tooltip />
      <el-table-column prop="post_time_str" label="发布时间" width="170" />
      <el-table-column label="状态" width="100">
        <template #default="scope">
          <el-tag v-if="scope.row.is_deleted" type="info">已删除</el-tag>
          <el-tag v-else type="success">正常</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="链接" min-width="220">
        <template #default="scope">
          <el-link :href="scope.row.url" target="_blank" type="primary">打开</el-link>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-button :disabled="paging.offset <= 0" @click="onPrev">上一页</el-button>
      <el-text type="info">offset={{ paging.offset }}, limit={{ paging.limit }}</el-text>
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

.pager {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
}
</style>
