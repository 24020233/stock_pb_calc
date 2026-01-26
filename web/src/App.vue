<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from './layouts/AppLayout.vue'

const route = useRoute()
const isLogin = computed(() => route.path === '/login')
</script>

<template>
  <router-view v-if="isLogin" />
  <AppLayout v-else />
</template>
