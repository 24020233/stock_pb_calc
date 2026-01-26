<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { createAccount, deleteAccount, fetchAccountArticles, listAccounts, updateAccount } from '../api/accounts'
import type { WxMpAccount } from '../api/types'

const loading = ref(false)
const rows = ref<WxMpAccount[]>([])

const paging = reactive({
  limit: 50,
  offset: 0,
})

const filters = reactive({
  name_like: '',
  enabled: '' as '' | '1' | '0',
})

const dialogOpen = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const currentId = ref<number | null>(null)

const formRef = ref<FormInstance>()
const form = reactive({
  mp_nickname: '',
  mp_wxid: '',
  mp_ghid: '',
  enabled: 1 as 0 | 1,
})

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增公众号' : '编辑公众号'))

const fetchLoadingId = ref<number | null>(null)
const bulkFetching = ref(false)

function ymdNDaysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

function parseYmdFromLastFetch(v: unknown): string | null {
  const s = formatDateTime(v)
  if (!s) return null
  const m = s.match(/^(\d{4}-\d{2}-\d{2})/)
  return m?.[1] ?? null
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function formatDateTime(v: unknown): string {
  if (!v) return ''
  const s = String(v)
  // Already in desired format.
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(s)) return s

  // RFC1123: Tue, 20 Jan 2026 21:07:37 GMT
  const rfc = /^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (\d{2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4}) (\d{2}):(\d{2}):(\d{2})/i
  const m1 = s.match(rfc)
  if (m1) {
    const day = m1[1]
    const monRaw = m1[2]
    const year = m1[3]
    const hh = m1[4]
    const mm = m1[5]
    const ss = m1[6]
    if (!day || !monRaw || !year || !hh || !mm || !ss) return ''
    const mon = monRaw.toLowerCase()
    const monthMap: Record<string, string> = {
      jan: '01',
      feb: '02',
      mar: '03',
      apr: '04',
      may: '05',
      jun: '06',
      jul: '07',
      aug: '08',
      sep: '09',
      oct: '10',
      nov: '11',
      dec: '12',
    }
    const month = monthMap[mon] || '01'
    return `${year}-${month}-${day} ${hh}:${mm}:${ss}`
  }

  // Common ISO formats: 2026-01-20T21:07:37(.sss)(Z)
  if (s.includes('T')) return s.replace('T', ' ').slice(0, 19)
  // Fallback: best-effort keep first 19 chars.
  return s.length >= 19 ? s.slice(0, 19) : s
}

async function fetchList() {
  loading.value = true
  try {
    const resp = await listAccounts({
      limit: paging.limit,
      offset: paging.offset,
      name_like: filters.name_like || undefined,
      enabled: filters.enabled === '' ? undefined : (Number(filters.enabled) as 0 | 1),
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

function openCreate() {
  dialogMode.value = 'create'
  currentId.value = null
  form.mp_nickname = ''
  form.mp_wxid = ''
  form.mp_ghid = ''
  form.enabled = 1
  dialogOpen.value = true
}

function openEdit(row: WxMpAccount) {
  dialogMode.value = 'edit'
  currentId.value = row.id
  form.mp_nickname = row.mp_nickname
  form.mp_wxid = row.mp_wxid || ''
  form.mp_ghid = row.mp_ghid || ''
  form.enabled = row.enabled
  dialogOpen.value = true
}

async function save() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return

    try {
      if (dialogMode.value === 'create') {
        const resp = await createAccount({
          mp_nickname: form.mp_nickname,
          mp_wxid: form.mp_wxid || null,
          mp_ghid: form.mp_ghid || null,
          enabled: form.enabled,
        })
        if (!resp.success) throw new Error(String(resp.error))
        ElMessage.success('创建成功')
      } else {
        if (currentId.value == null) throw new Error('Missing id')
        const resp = await updateAccount(currentId.value, {
          mp_nickname: form.mp_nickname,
          mp_wxid: form.mp_wxid || null,
          mp_ghid: form.mp_ghid || null,
          enabled: form.enabled,
        })
        if (!resp.success) throw new Error(String(resp.error))
        ElMessage.success('更新成功')
      }
      dialogOpen.value = false
      fetchList()
    } catch (e: any) {
      ElMessage.error(e?.message || String(e))
    }
  })
}

async function onDelete(row: WxMpAccount) {
  try {
    await ElMessageBox.confirm(`确认删除公众号：${row.mp_nickname}？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    const resp = await deleteAccount(row.id)
    if (!resp.success) throw new Error(String(resp.error))
    ElMessage.success('删除成功')
    fetchList()
  } catch (e) {
    // cancelled or error
    if (String((e as any)?.message || e).includes('cancel')) return
    if (String(e).includes('cancel')) return
  }
}

async function onFetch(row: WxMpAccount) {
  try {
    const { value } = await ElMessageBox.prompt('如接口要求验证码，可填写；否则留空即可。', `抓取文章：${row.mp_nickname}`, {
      confirmButtonText: '开始抓取',
      cancelButtonText: '取消',
      inputPlaceholder: 'verifycode（可空）',
      inputValue: '',
      type: 'info',
    })

    const verifycode = (value || '').trim() || undefined

    fetchLoadingId.value = row.id
    const resp = await fetchAccountArticles(row.id, { verifycode })
    if (!resp.success) throw new Error(String(resp.error))

    ElMessage.success(`抓取完成：${resp.data.fetched} 条`)
    // Refresh list so 'last_list_fetch_at' updates immediately.
    await fetchList()
  } catch (e: any) {
    // cancelled
    const rawMsg = String(e?.message || e)
    if (rawMsg.includes('cancel')) return
    const serverMsg = e?.response?.data?.error || e?.response?.data?.message
    const finalMsg = serverMsg || e?.message || String(e)
    if (String(finalMsg).includes('missing-env:DAJIALA_KEY')) {
      ElMessage.error('服务端未配置 DAJIALA_KEY：请在后端 .env 设置并重启后端服务。')
    } else {
      ElMessage.error(finalMsg)
    }
  } finally {
    fetchLoadingId.value = null
  }
}

async function fetchAllEnabledAccounts(maxPages = 50) {
  const out: WxMpAccount[] = []
  const limit = 200
  for (let i = 0; i < maxPages; i++) {
    const resp = await listAccounts({ limit, offset: i * limit, enabled: 1 })
    if (!resp.success) throw new Error(String(resp.error))
    const page = resp.data || []
    out.push(...page)
    if (page.length < limit) break
  }
  return out
}

async function onBulkFetch() {
  if (bulkFetching.value) return

  const yesterday = ymdNDaysAgo(1)
  const dayBefore = ymdNDaysAgo(2)

  try {
    await ElMessageBox.confirm(
      `将批量抓取“最后抓取”为昨天(${yesterday})或前天(${dayBefore})的公众号（会串行执行并限速，防止被反爬）。继续？`,
      '批量抓取确认',
      {
        type: 'warning',
        confirmButtonText: '开始',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  bulkFetching.value = true
  const delayMs = 2500
  let okCount = 0
  let failCount = 0
  try {
    const all = await fetchAllEnabledAccounts()
    const candidates = all.filter((a) => {
      const ymd = parseYmdFromLastFetch(a.last_list_fetch_at)
      return ymd === yesterday || ymd === dayBefore
    })

    if (!candidates.length) {
      ElMessage.info('没有需要批量抓取的公众号')
      return
    }

    ElMessage.info(`开始批量抓取：${candidates.length} 个公众号（每次间隔 ${delayMs}ms）`)

    for (let i = 0; i < candidates.length; i++) {
      const acc = candidates[i]!
      fetchLoadingId.value = acc.id
      try {
        const resp = await fetchAccountArticles(acc.id, {})
        if (!resp.success) throw new Error(String(resp.error))
        okCount += 1
      } catch (e: any) {
        failCount += 1
        // Avoid spamming messages; only show one concise error toast.
        if (failCount <= 1) {
          const serverMsg = e?.response?.data?.error || e?.response?.data?.message
          ElMessage.error(serverMsg || e?.message || String(e))
        }
      } finally {
        fetchLoadingId.value = null
      }

      if (i < candidates.length - 1) {
        await sleep(delayMs)
      }
    }

    ElMessage.success(`批量抓取完成：成功 ${okCount}，失败 ${failCount}`)
    await fetchList()
  } finally {
    bulkFetching.value = false
    fetchLoadingId.value = null
  }
}

onMounted(fetchList)
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <el-form inline @submit.prevent>
        <el-form-item label="名称">
          <el-input v-model="filters.name_like" placeholder="模糊搜索" clearable @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item label="启用">
          <el-select v-model="filters.enabled" placeholder="全部" style="width: 120px">
            <el-option label="全部" value="" />
            <el-option label="启用" value="1" />
            <el-option label="禁用" value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onSearch">查询</el-button>
        </el-form-item>
      </el-form>

      <el-button type="primary" @click="openCreate">新增</el-button>
      <el-button
        :loading="bulkFetching"
        :disabled="bulkFetching || fetchLoadingId !== null"
        @click="onBulkFetch"
      >
        批量抓取(前天/昨天)
      </el-button>
    </div>

    <el-table :data="rows" v-loading="loading" border style="width: 100%">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="mp_nickname" label="公众号" min-width="180" />
      <el-table-column prop="mp_wxid" label="wxid" min-width="160" />
      <el-table-column prop="mp_ghid" label="ghid" min-width="160" />
      <el-table-column label="状态" width="90">
        <template #default="scope">
          <el-tag v-if="scope.row.enabled" type="success">启用</el-tag>
          <el-tag v-else type="info">禁用</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最后抓取" min-width="170">
        <template #default="scope">
          {{ formatDateTime(scope.row.last_list_fetch_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="scope">
          <div class="op-row">
          <el-button size="small" @click="openEdit(scope.row)">编辑</el-button>
          <el-button
            size="small"
            type="primary"
            :loading="fetchLoadingId === scope.row.id"
            :disabled="fetchLoadingId !== null && fetchLoadingId !== scope.row.id"
            @click="onFetch(scope.row)"
          >
            抓取
          </el-button>
          <el-button size="small" type="danger" @click="onDelete(scope.row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-button :disabled="paging.offset <= 0" @click="onPrev">上一页</el-button>
      <el-text type="info">offset={{ paging.offset }}, limit={{ paging.limit }}</el-text>
      <el-button :disabled="rows.length < paging.limit" @click="onNext">下一页</el-button>
    </div>

    <el-dialog v-model="dialogOpen" :title="dialogTitle" width="520px">
      <el-form ref="formRef" :model="form" label-position="top">
        <el-form-item
          label="公众号名称"
          prop="mp_nickname"
          :rules="[{ required: true, message: '必填', trigger: 'blur' }]"
        >
          <el-input v-model="form.mp_nickname" placeholder="例如：中国基金报" />
        </el-form-item>

        <el-form-item label="mp_wxid">
          <el-input v-model="form.mp_wxid" placeholder="可空" />
        </el-form-item>

        <el-form-item label="mp_ghid">
          <el-input v-model="form.mp_ghid" placeholder="可空" />
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="form.enabled" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
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

<style scoped>
.op-row {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  align-items: center;
  white-space: nowrap;
}
</style>
