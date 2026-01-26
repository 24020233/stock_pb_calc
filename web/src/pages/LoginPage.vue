<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getApiBaseUrl } from '../env'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const loading = ref(false)
const errorMsg = ref('')

const form = reactive({
  username: auth.username || 'admin',
  password: '',
})

async function onSubmit() {
  errorMsg.value = ''
  loading.value = true
  try {
    await auth.login({
      apiBaseUrl: auth.apiBaseUrl || getApiBaseUrl(),
      username: form.username,
      password: form.password,
    })
    const next = typeof route.query.next === 'string' ? route.query.next : '/accounts'
    router.replace(next)
  } catch (e: any) {
    const serverMsg = e?.response?.data?.error || e?.response?.data?.message
    errorMsg.value = serverMsg || e?.message || String(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="wrap">
    <el-card class="card" shadow="never">
      <template #header>
        <div class="header">
          <div>
            <div class="title">登录</div>
            <div class="sub">连接你的 API 服务并进入后台</div>
          </div>
        </div>
      </template>

      <el-form label-position="top" @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="admin" />
        </el-form-item>

        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入后台密码" />
        </el-form-item>

        <el-alert v-if="errorMsg" type="error" :closable="false" :title="errorMsg" class="mb" />

        <el-button type="primary" :loading="loading" style="width: 100%" @click="onSubmit">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%);
}

.card {
  width: 420px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title {
  font-size: 20px;
  font-weight: 700;
}

.sub {
  margin-top: 6px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.mb {
  margin-bottom: 12px;
}
</style>
