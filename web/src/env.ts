export function getEnv(key: string, defaultValue = ''): string {
  const v = (import.meta as any).env?.[key]
  if (typeof v === 'string' && v.length > 0) return v
  return defaultValue
}

export function getApiBaseUrl(): string {
  // Prefer explicit config.
  const configured = getEnv('VITE_API_BASE_URL', '')
  if (configured) return configured

  // In dev, use same-origin + Vite proxy (/api -> target).
  if ((import.meta as any).env?.DEV) return ''

  // In production, default to same-origin and let the web server proxy /api to backend.
  return ''
}
