<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const title = computed(() => {
  if (route.path.startsWith('/accounts')) return '公众号管理'
  if (route.path.startsWith('/articles')) return '文章管理'
  if (route.path.startsWith('/sectors')) return '板块总结'
  if (route.path.startsWith('/picks-history')) return '历史选股'
  if (route.path.startsWith('/picks')) return '板块选股'
  if (route.path.startsWith('/settings')) return '系统设置'
  return '后台'
})

function onLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <div class="left">
        <div class="brand">WX Admin</div>
        <el-tag type="info" effect="plain">{{ title }}</el-tag>
      </div>
      <div class="right">
        <el-text type="info" v-if="auth.apiBaseUrl">{{ auth.apiBaseUrl }}</el-text>
        <el-divider direction="vertical" />
        <el-text v-if="auth.username">{{ auth.username }}</el-text>
        <el-button type="primary" plain size="small" @click="onLogout">退出</el-button>
      </div>
    </el-header>

    <el-container class="app-body">
      <el-aside class="app-aside" width="200px">
        <el-menu class="app-menu" router :default-active="route.path">
          <el-menu-item index="/articles">文章管理</el-menu-item>
          <el-menu-item index="/sectors">板块总结</el-menu-item>
          <el-menu-item index="/picks-history">历史选股</el-menu-item>
          <el-menu-item index="/picks">板块选股</el-menu-item>
          <el-sub-menu index="settings">
            <template #title>系统设置</template>
            <el-menu-item index="/accounts">公众号管理</el-menu-item>
            <el-menu-item index="/settings/movement">异动规则</el-menu-item>
            <el-menu-item index="/settings/fundamental">基本面判断点</el-menu-item>
            <el-menu-item index="/settings/technical">技术面判断点</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-aside>

      <el-main class="app-main">
        <div class="app-content">
          <router-view />
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--el-border-color);
}

.left,
.right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand {
  font-weight: 700;
  letter-spacing: 0.4px;
}

.app-body {
  flex: 1;
}

.app-aside {
  border-right: 1px solid var(--el-border-color);
}

.app-menu {
  height: 100%;
}

.app-main {
  padding: 0;
}

.app-content {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 16px;
}
</style>
