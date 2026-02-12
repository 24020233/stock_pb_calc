-- 复用现有的 wx_mp_account, wx_article_seed, wx_article_detail 等表
-- 这里只定义 V2 新增的表

-- 1) 每日策略执行任务表 (Pipeline Run)
CREATE TABLE IF NOT EXISTS task_run_log (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  day DATE NOT NULL,
  
  -- 节点状态: 0=未开始, 1=进行中, 2=完成, 3=失败
  node_a_status TINYINT NOT NULL DEFAULT 0,
  node_b_status TINYINT NOT NULL DEFAULT 0,
  node_c_status TINYINT NOT NULL DEFAULT 0,
  node_d_status TINYINT NOT NULL DEFAULT 0,
  
  node_a_msg VARCHAR(255) NULL,
  node_b_msg VARCHAR(255) NULL,
  node_c_msg VARCHAR(255) NULL,
  node_d_msg VARCHAR(255) NULL,

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  UNIQUE KEY uk_day (day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 2) 热点/风口分析表 (Node B Output)
-- 替代/增强原有的 wx_sector_daily，支持更结构化的热点描述
CREATE TABLE IF NOT EXISTS topic_analysis (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  day DATE NOT NULL,
  
  topic_name VARCHAR(128) NOT NULL,    -- 热点名称（如“低空经济”）
  related_sector VARCHAR(128) NULL,    -- 关联板块（如“通航”）
  strength FLOAT NULL,                 -- 预期强度
  
  article_ids JSON NULL,               -- 关联的文章ID列表 [1, 2, 3]
  reason TEXT NULL,                    -- AI 提取理由
  
  is_deleted TINYINT NOT NULL DEFAULT 0, -- 人工删除标记

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  KEY idx_day (day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 3) 股票池 1 (Node C Output - 异动初筛)
CREATE TABLE IF NOT EXISTS stock_pool_1 (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  day DATE NOT NULL,
  
  stock_code VARCHAR(16) NOT NULL,
  stock_name VARCHAR(64) NOT NULL,
  
  source_topic_id BIGINT UNSIGNED NULL, -- 关联的热点ID
  
  -- 扫描时刻的快照数据
  snapshot_price DECIMAL(18, 4) NULL,
  snapshot_pct_change DECIMAL(10, 4) NULL,
  snapshot_vol_ratio DECIMAL(10, 4) NULL, -- 量比
  snapshot_turnover DECIMAL(10, 4) NULL,  -- 换手率
  
  reason VARCHAR(255) NULL,             -- 入选理由（如“放量、板块效应”）

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  PRIMARY KEY (id),
  KEY idx_day (day),
  KEY idx_topic (source_topic_id),
  CONSTRAINT fk_pool1_topic FOREIGN KEY (source_topic_id) REFERENCES topic_analysis(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 4) 股票池 2 (Node D Output - 深度精选)
CREATE TABLE IF NOT EXISTS stock_pool_2 (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  pool1_id BIGINT UNSIGNED NOT NULL, -- 来自哪个初筛记录
  
  technical_score FLOAT NULL,
  fundamental_score FLOAT NULL,
  
  ai_analysis_text TEXT NULL,        -- LLM 对其唯一性/地位的评价
  
  decision_status TINYINT NOT NULL DEFAULT 0, -- 0=待定, 1=入选(Pass), 2=淘汰(Fail)
  fail_reason VARCHAR(255) NULL,             -- 淘汰原因

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  UNIQUE KEY uk_pool1 (pool1_id),
  CONSTRAINT fk_pool2_pool1 FOREIGN KEY (pool1_id) REFERENCES stock_pool_1(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
