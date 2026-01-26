import { http } from './http'
import type { ApiResp, WxArticleSeed } from './types'

export type ListSeedsParams = {
  limit?: number
  offset?: number
  account_id?: number
  q?: string
  is_deleted?: 0 | 1
}

export async function listSeeds(params: ListSeedsParams = {}): Promise<
  ApiResp<WxArticleSeed[]> & { limit?: number; offset?: number }
> {
  const resp = await http.get<ApiResp<WxArticleSeed[]> & { limit?: number; offset?: number }>(
    '/api/seeds',
    { params }
  )
  return resp.data
}
