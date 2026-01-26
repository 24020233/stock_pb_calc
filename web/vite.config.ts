import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget =
    env.VITE_API_PROXY_TARGET || env.VITE_API_BASE_URL || 'http://43.134.90.115:8001'

  const publicBaseRaw = env.VITE_PUBLIC_BASE || '/'
  const publicBase = publicBaseRaw.endsWith('/') ? publicBaseRaw : `${publicBaseRaw}/`

  return {
    base: publicBase,
    plugins: [vue()],
    server: {
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
