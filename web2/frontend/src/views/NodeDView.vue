<template>
  <el-table :data="stocks" style="width: 100%" height="500">
    <el-table-column prop="stock_code" label="Code" width="100" />
    <el-table-column prop="stock_name" label="Name" width="100" />
    <el-table-column prop="technical_score" label="Tech Score" width="120" />
    <el-table-column prop="fundamental_score" label="Fund Score" width="120" />
    <el-table-column prop="decision_status" label="Status" width="100">
        <template #default="{ row }">
            <el-tag :type="row.decision_status === 1 ? 'success' : 'danger'">
                {{ row.decision_status === 1 ? 'Pass' : 'Fail' }}
            </el-tag>
        </template>
    </el-table-column>
    <el-table-column prop="ai_analysis_text" label="AI Analysis" show-overflow-tooltip />
  </el-table>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import http from '@/api/http'

const props = defineProps<{ date: string }>()
const stocks = ref([])

const loadData = async () => {
    try {
        const res: any = await http.get('/node_d/stocks', { params: { date: props.date } })
        if (res.success) {
            stocks.value = res.data
        }
    } catch (e) { console.error(e) }
}

watch(() => props.date, loadData)
onMounted(loadData)
</script>
