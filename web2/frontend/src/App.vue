<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <el-container>
    <el-header style="text-align: right; font-size: 12px; background-color: #f5f7fa; border-bottom: 1px solid #e6e6e6;">
      <div style="display: flex; align-items: center; justify-content: space-between; height: 100%;">
        <div style="font-size: 18px; font-weight: bold; color: #409EFF;">蓝胖子 AI 选股系统 V2</div>
        <div>
           <router-link to="/">看板</router-link> | 
           <router-link to="/pipeline">Pipeline</router-link>
        </div>
      </div>
    </el-header>
    <el-main>
      <RouterView />
    </el-main>
  </el-container>
</template>

<style>
body {
  margin: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
}
</style>
