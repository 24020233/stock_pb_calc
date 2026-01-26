import axios from 'axios'
import { getApiBaseUrl } from '../env'

function shouldForceProxy(): boolean {
  // In dev, prefer same-origin + Vite proxy to avoid CORS.
  // Set VITE_FORCE_PROXY=0 to disable.
  const env = (import.meta as any).env || {}
  return Boolean(env.DEV) && String(env.VITE_FORCE_PROXY ?? '1') !== '0'
}

export const http = axios.create({
  baseURL: shouldForceProxy() ? '' : getApiBaseUrl(),
  timeout: 300_000,
})

export function setHttpBaseUrl(baseURL: string) {
  http.defaults.baseURL = shouldForceProxy() ? '' : baseURL
}
