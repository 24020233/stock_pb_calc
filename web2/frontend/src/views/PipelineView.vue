<template>
  <div class="pipeline-view">
    <h1>Pipeline Execution</h1>
    <!-- Calendar/Date Picker -->
    <div style="margin-bottom: 20px;">
        <el-date-picker
            v-model="currentDate"
            type="date"
            placeholder="Select Date"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            @change="fetchStatus"
        />
        <el-button type="primary" @click="fetchStatus" style="margin-left: 10px;">Refresh</el-button>
    </div>

    <!-- Status Cards -->
    <el-row :gutter="20">
      <el-col :span="6" v-for="(node, key) in nodes" :key="key">
        <el-card shadow="hover">
            <template #header>
                <div class="card-header">
                    <span>{{ node.title }}</span>
                    <el-tag :type="getStatusType(node.status)">{{ getStatusText(node.status) }}</el-tag>
                </div>
            </template>
            <div class="card-body">
                <p v-if="node.msg" class="msg">{{ node.msg }}</p>
                <el-button type="primary" size="small" :loading="node.loading" @click="runNode(key)">Run</el-button>
                <el-button size="small" @click="viewNode(key)">View Data</el-button>
            </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Node Views (Placeholder for now, implementation in next steps) -->
    <el-divider />
    <div v-if="activeNode">
        <h2>{{ nodes[activeNode].title }} Data</h2>
        <!-- Simple dynamic component loading or v-if blocks for now -->
        <component :is="activeNodeComponent" :date="currentDate" />
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, defineAsyncComponent } from 'vue'
import http from '@/api/http'
import { ElMessage } from 'element-plus'

const currentDate = ref(new Date().toISOString().slice(0, 10))
const activeNode = ref('')

// Async components for node details to avoid circle deps or large bundle
const NodeAView = defineAsyncComponent(() => import('./NodeAView.vue'))
const NodeBView = defineAsyncComponent(() => import('./NodeBView.vue'))
const NodeCView = defineAsyncComponent(() => import('./NodeCView.vue'))
const NodeDView = defineAsyncComponent(() => import('./NodeDView.vue'))

const activeNodeComponent = computed(() => {
    if (activeNode.value === 'node_a') return NodeAView
    if (activeNode.value === 'node_b') return NodeBView
    if (activeNode.value === 'node_c') return NodeCView
    if (activeNode.value === 'node_d') return NodeDView
    return null
})

const nodes = ref<any>({
    node_a: { title: 'Node A: Info Gathering', status: 0, msg: '', loading: false },
    node_b: { title: 'Node B: Topic Extraction', status: 0, msg: '', loading: false },
    node_c: { title: 'Node C: Abnormal Scan', status: 0, msg: '', loading: false },
    node_d: { title: 'Node D: Deep Dive', status: 0, msg: '', loading: false },
})

const getStatusType = (s: number) => {
    if (s === 1) return 'warning'
    if (s === 2) return 'success'
    if (s === 3) return 'danger'
    return 'info'
}

const getStatusText = (s: number) => {
    const map = ['Pending', 'Running', 'Success', 'Error']
    return map[s] || 'Unknown'
}

const fetchStatus = async () => {
    try {
        const res: any = await http.get('/pipeline/status', { params: { date: currentDate.value } })
        if (res.success && res.data) {
            const d = res.data
            nodes.value.node_a.status = d.node_a_status
            nodes.value.node_a.msg = d.node_a_msg
            nodes.value.node_b.status = d.node_b_status
            nodes.value.node_b.msg = d.node_b_msg
            nodes.value.node_c.status = d.node_c_status
            nodes.value.node_c.msg = d.node_c_msg
            nodes.value.node_d.status = d.node_d_status
            nodes.value.node_d.msg = d.node_d_msg
        }
    } catch (e) {
        console.error(e)
    }
}

const runNode = async (key: string) => {
    nodes.value[key].loading = true
    try {
        const res: any = await http.post('/pipeline/run_node', { date: currentDate.value, node: key })
        if (res.success) {
            ElMessage.success(`Node ${key} started`)
            // Poll for status or just refresh after a delay? 
            // Real implementation should poll. For now just refresh immediately + delay.
            setTimeout(fetchStatus, 1000)
        } else {
            ElMessage.error(res.error || 'Failed')
        }
    } catch (e) {
        console.error(e)
    } finally {
        nodes.value[key].loading = false
    }
}

const viewNode = (key: string) => {
    activeNode.value = key
}

onMounted(() => {
    fetchStatus()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.msg {
    font-size: 12px;
    color: #666;
    height: 40px; 
    overflow: hidden;
    text-overflow: ellipsis;
}
</style>
