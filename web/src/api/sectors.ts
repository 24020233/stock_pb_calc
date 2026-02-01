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

export type SectorDateRow = {
  day: string
  sector_count: number
  sectors: string[]
}

export async function listSectorDates() {
  const resp = await http.get<ApiResp<{ rows: SectorDateRow[] }>>('/api/sectors/dates')
  return resp.data
}

export async function deleteSectors(date: string) {
  const resp = await http.delete<ApiResp<{ date: string; deleted: number }>>('/api/sectors', { params: { date } })
  return resp.data
}
