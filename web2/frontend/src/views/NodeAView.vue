<template>
  <el-table :data="articles" style="width: 100%" height="500">
    <el-table-column prop="id" label="ID" width="60" />
    <el-table-column prop="mp_nickname" label="Account" width="120" />
    <el-table-column prop="title" label="Title">
        <template #default="{ row }">
            <a :href="row.url" target="_blank">{{ row.title }}</a>
        </template>
    </el-table-column>
    <el-table-column prop="post_time_str" label="Time" width="160" />
  </el-table>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import http from '@/api/http'

const props = defineProps<{ date: string }>()
const articles = ref([])

const loadData = async () => {
    try {
        const res: any = await http.get('/node_a/articles', { params: { date: props.date } })
        if (res.success) {
            articles.value = res.data
        }
    } catch (e) { console.error(e) }
}

watch(() => props.date, loadData)
onMounted(loadData)
</script>
