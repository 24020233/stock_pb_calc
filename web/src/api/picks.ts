import { http } from './http'
import type { ApiResp } from './types'

export type PickRow = {
  day: string
  sector: string
  stock_code: string
  stock_name: string
  latest_price: number | null
  pct_change: number | null
  open_price: number | null
  prev_close: number | null
  turnover_rate: number | null
  pe_dynamic: number | null
  pb: number | null
  updated_at?: string
}

export async function listPicks(params?: { date?: string; sector?: string; limit?: number; offset?: number }) {
  const resp = await http.get<ApiResp<{ date: string; rows: PickRow[] }>>('/api/picks', { params })
  return resp.data
}

export async function generatePicks(body?: {
  date?: string
  minMention?: number
  minChange?: number
  minTurnover?: number
  maxSectors?: number
}) {
  const resp = await http.post<
    ApiResp<{
      date: string
      generated: number
      sectors_total: number
      sectors_matched: number
      skipped: any[]
      rows: PickRow[]
      params: { minMention: number; minChange: number; minTurnover: number; maxSectors: number }
    }>
  >('/api/picks/generate', body || {})
  return resp.data
}
