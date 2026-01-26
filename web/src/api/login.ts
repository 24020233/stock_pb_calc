import { http } from './http'
import type { ApiResp } from './types'

export async function apiLogin(body: {
  username: string
  password: string
}): Promise<ApiResp<{ ok: true }>> {
  const resp = await http.post<ApiResp<{ ok: true }>>('/api/login', body)
  return resp.data
}
