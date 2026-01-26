import { http } from './http'
import type { ApiResp, WxMpAccount } from './types'

export type ListAccountsParams = {
  limit?: number
  offset?: number
  enabled?: 0 | 1
  name_like?: string
}

export async function listAccounts(params: ListAccountsParams = {}): Promise<
  ApiResp<WxMpAccount[]> & { limit?: number; offset?: number }
> {
  const resp = await http.get<ApiResp<WxMpAccount[]> & { limit?: number; offset?: number }>(
    '/api/accounts',
    { params }
  )
  return resp.data
}

export type CreateAccountBody = {
  mp_nickname: string
  mp_wxid?: string | null
  mp_ghid?: string | null
  enabled?: 0 | 1
}

export async function createAccount(body: CreateAccountBody): Promise<ApiResp<{ id: number }>> {
  const resp = await http.post<ApiResp<{ id: number }>>('/api/accounts', body)
  return resp.data
}

export type UpdateAccountBody = Partial<CreateAccountBody>

export async function updateAccount(accountId: number, body: UpdateAccountBody): Promise<ApiResp<{ updated: number }>> {
  const resp = await http.patch<ApiResp<{ updated: number }>>(`/api/accounts/${accountId}`, body)
  return resp.data
}

export async function deleteAccount(accountId: number): Promise<ApiResp<{ deleted: number }>> {
  const resp = await http.delete<ApiResp<{ deleted: number }>>(`/api/accounts/${accountId}`)
  return resp.data
}

export async function fetchAccountArticles(
  accountId: number,
  body: { verifycode?: string } = {}
): Promise<ApiResp<{ account_id: number; fetched: number; stored_account_id?: number; fetch_id?: number }>> {
  const resp = await http.post<
    ApiResp<{ account_id: number; fetched: number; stored_account_id?: number; fetch_id?: number }>
  >(`/api/accounts/${accountId}/fetch`, body)
  return resp.data
}
