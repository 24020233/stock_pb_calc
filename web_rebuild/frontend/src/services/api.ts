import axios from 'axios';
import type {
  ApiResponse,
  Report,
  ReportSummary,
  RawArticle,
  HotTopic,
  StockPool1,
  StockPool2,
  TargetAccount,
  StrategyRule,
  PipelineNodes,
} from '@/types';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Reports API
export const reportsApi = {
  list: (params?: { limit?: number; offset?: number; status?: string }) =>
    api.get<ApiResponse<{ reports: Report[]; total: number }>>('/reports', { params }),
  get: (id: number) => api.get<ApiResponse<Report>>(`/reports/${id}`),
  create: (data: { report_date: string }) => api.post<ApiResponse<Report>>('/reports', data),
  delete: (id: number) => api.delete<ApiResponse<{ deleted: number }>>(`/reports/${id}`),
  generate: (id: number) => api.post<ApiResponse<any>>(`/reports/${id}/generate`),
  checkData: (id: number) => api.get<ApiResponse<any>>(`/reports/${id}/check`),
  summary: (id: number) => api.get<ApiResponse<ReportSummary>>(`/reports/${id}/summary`),
};

// Pipeline API
export const pipelineApi = {
  getNodes: (reportId: number) =>
    api.get<ApiResponse<PipelineNodes>>(`/pipeline/${reportId}/nodes`),
  step1Articles: (data: { report_id: number; articles: RawArticle[] }) =>
    api.post<ApiResponse<{ added_count: number }>>('/pipeline/step1-articles', data),
  step2Topics: (reportId: number) =>
    api.post<ApiResponse<{ topics: HotTopic[] }>>(`/pipeline/${reportId}/step2-topics`),
  step3Pool1: (reportId: number) =>
    api.post<ApiResponse<{ stock_count: number }>>(`/pipeline/${reportId}/step3-pool1`),
  step4Pool2: (reportId: number) =>
    api.post<ApiResponse<{ selected_count: number }>>(`/pipeline/${reportId}/step4-pool2`),
};

// Settings API
export const settingsApi = {
  listAccounts: () => api.get<ApiResponse<{ accounts: TargetAccount[] }>>('/settings/accounts'),
  createAccount: (data: { account_name: string; wx_id?: string; status?: string; sort_order?: number }) =>
    api.post<ApiResponse<{ id: number }>>('/settings/accounts', data),
  updateAccount: (id: number, data: Partial<TargetAccount>) =>
    api.patch<ApiResponse<{ updated: number }>>(`/settings/accounts/${id}`, data),
  deleteAccount: (id: number) =>
    api.delete<ApiResponse<{ deleted: number }>>(`/settings/accounts/${id}`),
  listRules: () => api.get<ApiResponse<{ rules: StrategyRule[] }>>('/settings/rules'),
  updateRule: (key: string, data: Partial<StrategyRule>) =>
    api.patch<ApiResponse<{ updated: string }>>(`/settings/rules/${key}`, data),
};

// Stocks API
export const stocksApi = {
  listBoards: () => api.get<ApiResponse<{ boards: any[] }>>('/stocks/boards'),
  getBoardStocks: (boardName: string) =>
    api.get<ApiResponse<{ stocks: any[]; count: number }>>(`/stocks/boards/${encodeURIComponent(boardName)}/stocks`),
  getSnapshot: (code: string) => api.get<ApiResponse<any>>(`/stocks/${code}/snapshot`),
  search: (keyword: string) =>
    api.get<ApiResponse<{ stocks: any[]; count: number }>>(`/stocks/search/${encodeURIComponent(keyword)}`),
};

// Health API
export const healthApi = {
  check: () => api.get('/health'),
};

export default api;
