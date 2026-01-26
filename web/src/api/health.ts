import { http } from './http'
import type { ApiResp } from './types'

export async function apiHealth(): Promise<ApiResp<{ db: boolean; select: number | null }>> {
  const resp = await http.get<ApiResp<{ db: boolean; select: number | null }>>('/api/health')
  return resp.data
}
