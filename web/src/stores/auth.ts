import { defineStore } from 'pinia'
import { setHttpBaseUrl } from '../api/http'
import { apiHealth } from '../api/health'
import { apiLogin } from '../api/login'

const LS_KEY = 'wxmp_admin_auth_v1'

type AuthState = {
  authed: boolean
  username: string
  apiBaseUrl: string
}

function loadState(): AuthState {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (!raw) return { authed: false, username: '', apiBaseUrl: '' }
    const v = JSON.parse(raw) as Partial<AuthState>
    return {
      authed: Boolean(v.authed),
      username: typeof v.username === 'string' ? v.username : '',
      apiBaseUrl: typeof v.apiBaseUrl === 'string' ? v.apiBaseUrl : '',
    }
  } catch {
    return { authed: false, username: '', apiBaseUrl: '' }
  }
}

function persistState(s: AuthState) {
  localStorage.setItem(LS_KEY, JSON.stringify(s))
}

export const useAuthStore = defineStore('auth', {
  state: () => loadState(),
  getters: {
    isAuthed: (s) => s.authed,
  },
  actions: {
    async login(opts: { apiBaseUrl: string; username: string; password: string }) {
      // Login gates UI; backend validates password via /api/login.
      // Allow empty base URL to use same-origin (useful with Vite proxy in dev).
      const apiBaseUrl = opts.apiBaseUrl.trim().replace(/\/+$/, '')

      setHttpBaseUrl(apiBaseUrl)

      const loginResp = await apiLogin({ username: opts.username, password: opts.password })
      if (!loginResp.success) throw new Error(String(loginResp.error))

      const health = await apiHealth()
      if (!health.success) throw new Error(`API health failed: ${health.error}`)
      if (!health.data?.db) throw new Error('API DB not healthy')

      this.authed = true
      this.username = opts.username.trim() || 'admin'
      this.apiBaseUrl = apiBaseUrl
      persistState({ authed: this.authed, username: this.username, apiBaseUrl: this.apiBaseUrl })
    },
    logout() {
      this.authed = false
      this.username = ''
      this.apiBaseUrl = ''
      persistState({ authed: false, username: '', apiBaseUrl: '' })
    },
    hydrateToHttp() {
      if (this.apiBaseUrl) setHttpBaseUrl(this.apiBaseUrl)
    },
  },
})
