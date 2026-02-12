<template>
  <el-table :data="topics" style="width: 100%" height="500">
    <el-table-column prop="topic_name" label="Topic" width="150" />
    <el-table-column prop="related_sector" label="Sector" width="120" />
    <el-table-column prop="strength" label="Strength" width="100">
        <template #default="{ row }">
            <el-rate v-model="row.strength" disabled show-score text-color="#ff9900" score-template="{value}" :max="10" />
        </template>
    </el-table-column>
    <el-table-column prop="reason" label="Reason" />
  </el-table>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import http from '@/api/http'

const props = defineProps<{ date: string }>()
const topics = ref([])

const loadData = async () => {
    try {
        const res: any = await http.get('/node_b/topics', { params: { date: props.date } })
        if (res.success) {
            topics.value = res.data
        }
    } catch (e) { console.error(e) }
}

watch(() => props.date, loadData)
onMounted(loadData)
</script>
