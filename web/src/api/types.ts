export type ApiOk<T> = {
  success: true
  data: T
  [k: string]: unknown
}

export type ApiErr = {
  success: false
  error: string
  [k: string]: unknown
}

export type ApiResp<T> = ApiOk<T> | ApiErr

export type WxMpAccount = {
  id: number
  mp_nickname: string
  mp_wxid: string | null
  mp_ghid: string | null
  enabled: 0 | 1
  last_list_fetch_at: string | null
  created_at: string
  updated_at: string
}

export type WxArticleSeed = {
  id: number
  account_id: number
  fetch_id: number | null
  title: string
  digest: string | null
  url: string
  position: number | null
  post_time: number | null
  post_time_str: string | null
  cover_url: string | null
  original: 0 | 1 | null
  item_show_type: number | null
  types: unknown
  is_deleted: 0 | 1
  msg_status: number | null
  msg_fail_reason: string | null
  first_seen_at: string
  last_seen_at: string
  created_at: string
  updated_at: string
}
