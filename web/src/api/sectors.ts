import { http } from './http'
import type { ApiResp } from './types'

export type SectorArticleRef = {
  id: number
  title: string
  url: string
}

export type SectorRow = {
  day: string
  sector: string
  mention_count: number
  articles: SectorArticleRef[]
}

export async function listSectors(params?: { date?: string }) {
  const resp = await http.get<ApiResp<{ date: string; rows: SectorRow[] }>>('/api/sectors', { params })
  return resp.data
}

export async function generateSectors(body?: { date?: string; force?: 0 | 1 }) {
  const resp = await http.post<ApiResp<{ date: string; generated: number; fetch_failures: number; rows: SectorRow[] }>>(
    '/api/sectors/generate',
    body || {},
  )
  return resp.data
}
