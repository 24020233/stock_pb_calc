<template>
  <el-table :data="stocks" style="width: 100%" height="500">
    <el-table-column prop="stock_code" label="Code" width="100" />
    <el-table-column prop="stock_name" label="Name" width="100" />
    <el-table-column prop="topic_name" label="Source Topic" width="150" />
    <el-table-column prop="related_sector" label="Sector" width="120" />
    <el-table-column prop="snapshot_price" label="Price" width="100" />
    <el-table-column prop="snapshot_pct_change" label="Change %" width="100">
        <template #default="{ row }">
            <span :style="{ color: row.snapshot_pct_change > 0 ? 'red' : 'green' }">
                {{ row.snapshot_pct_change }}%
            </span>
        </template>
    </el-table-column>
    <el-table-column prop="snapshot_vol_ratio" label="Vol Ratio" width="100" />
    <el-table-column prop="reason" label="Scan Reason" />
  </el-table>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import http from '@/api/http'

const props = defineProps<{ date: string }>()
const stocks = ref([])

const loadData = async () => {
    try {
        const res: any = await http.get('/node_c/stocks', { params: { date: props.date } })
        if (res.success) {
            stocks.value = res.data
        }
    } catch (e) { console.error(e) }
}

watch(() => props.date, loadData)
onMounted(loadData)
</script>
