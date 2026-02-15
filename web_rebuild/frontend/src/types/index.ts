export interface ApiResponse<T = any> {
  code: number;
  msg: string;
  data?: T;
}

export interface Report {
  id: number;
  report_date: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  created_at: string;
  updated_at?: string;
}

export interface ReportSummary extends Report {
  article_count: number;
  topic_count: number;
  pool1_count: number;
  pool2_count: number;
}

export interface RawArticle {
  id: number;
  title?: string;
  content?: string;
  source_account?: string;
  publish_time?: number;
  url?: string;
}

export interface HotTopic {
  id: number;
  topic_name: string;
  related_boards: string[];
  logic_summary?: string;
}

export interface StockPool1 {
  id: number;
  stock_code: string;
  stock_name: string;
  related_topic_id?: number;
  snapshot_data?: Record<string, any>;
  match_reason?: string;
}

export interface StockPool2 {
  id: number;
  pool_1_id: number;
  stock_code: string;
  stock_name: string;
  tech_score?: number;
  fund_score?: number;
  total_score?: number;
  ai_analysis?: string;
  is_selected: boolean;
}

export interface TargetAccount {
  id: number;
  account_name: string;
  wx_id?: string;
  status: 'active' | 'inactive';
  sort_order: number;
  created_at: string;
  updated_at?: string;
}

export interface StrategyRule {
  id: number;
  rule_key: string;
  rule_name: string;
  rule_value: Record<string, any>;
  description?: string;
  is_enabled: boolean;
  sort_order: number;
}

export interface PipelineNodes {
  step1: {
    name: string;
    data: RawArticle[];
  };
  step2: {
    name: string;
    data: HotTopic[];
  };
  step3: {
    name: string;
    data: StockPool1[];
  };
  step4: {
    name: string;
    data: StockPool2[];
  };
}
