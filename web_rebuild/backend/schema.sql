-- 公众号内容爬取服务数据库表结构
-- Database: wechat_crawler

-- 1. 公众号账号表
CREATE TABLE IF NOT EXISTS wx_mp_account (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  mp_nickname VARCHAR(128) NOT NULL COMMENT '公众号昵称',
  mp_wxid VARCHAR(64) NULL COMMENT '微信号',
  mp_ghid VARCHAR(64) NULL COMMENT '原始ID (gh_xxx)',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_mp_wxid (mp_wxid),
  UNIQUE KEY uk_mp_ghid (mp_ghid),
  KEY idx_mp_nickname (mp_nickname)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='公众号账号表';


-- 2. 文章列表表（存储公众号当天发文情况）
CREATE TABLE IF NOT EXISTS wx_article_list (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  account_id BIGINT UNSIGNED NULL COMMENT '关联公众号ID',
  mp_nickname VARCHAR(128) NOT NULL COMMENT '公众号名称',
  title VARCHAR(512) NOT NULL COMMENT '文章标题',
  url VARCHAR(2048) NOT NULL COMMENT '文章链接',
  url_hash BINARY(16) GENERATED ALWAYS AS (UNHEX(MD5(url))) STORED COMMENT 'URL哈希',
  post_time BIGINT NULL COMMENT '发文时间戳',
  post_time_str VARCHAR(64) NULL COMMENT '发文时间字符串',
  fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_url (url_hash),
  KEY idx_account_time (account_id, post_time),
  KEY idx_nickname_time (mp_nickname, post_time),
  KEY idx_fetched_at (fetched_at),
  CONSTRAINT fk_list_account
    FOREIGN KEY (account_id) REFERENCES wx_mp_account(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文章列表表';


-- 3. 文章详情表（存储文章正文内容）
CREATE TABLE IF NOT EXISTS wx_article_detail (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  article_list_id BIGINT UNSIGNED NULL COMMENT '关联文章列表ID',
  title VARCHAR(512) NULL COMMENT '文章标题',
  url VARCHAR(2048) NOT NULL COMMENT '文章链接',
  url_hash BINARY(16) GENERATED ALWAYS AS (UNHEX(MD5(url))) STORED COMMENT 'URL哈希',
  pubtime BIGINT NULL COMMENT '发文时间戳',
  hashid VARCHAR(64) NULL COMMENT '文章唯一hashid',
  nick_name VARCHAR(128) NULL COMMENT '公众号名字',
  author VARCHAR(128) NULL COMMENT '文章作者',
  content MEDIUMTEXT NULL COMMENT '文章正文内容',
  fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_url (url_hash),
  KEY idx_list (article_list_id),
  KEY idx_hashid (hashid),
  KEY idx_nick_name (nick_name),
  CONSTRAINT fk_detail_list
    FOREIGN KEY (article_list_id) REFERENCES wx_article_list(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文章详情表';


-- 4. reports（每日报告主表）
CREATE TABLE IF NOT EXISTS reports (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  report_date DATE NOT NULL COMMENT '报告日期',
  status VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT '状态: pending, processing, completed, error',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_report_date (report_date),
  KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日报告主表';


-- 5. raw_articles（情报源表 - 节点1产出）
CREATE TABLE IF NOT EXISTS raw_articles (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  report_id BIGINT UNSIGNED NOT NULL COMMENT '关联 reports.id',
  title VARCHAR(512) NULL COMMENT '文章标题',
  content MEDIUMTEXT NULL COMMENT '全文内容',
  source_account VARCHAR(128) NULL COMMENT '公众号名称',
  publish_time BIGINT NULL COMMENT '发布时间戳',
  url VARCHAR(2048) NULL COMMENT '原文链接',
  article_detail_id BIGINT UNSIGNED NULL COMMENT '关联 wx_article_detail.id',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_report_id (report_id),
  KEY idx_article_detail_id (article_detail_id),
  CONSTRAINT fk_raw_articles_report FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='情报源表';


-- 6. hot_topics（热点风口表 - 节点2产出）
CREATE TABLE IF NOT EXISTS hot_topics (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  report_id BIGINT UNSIGNED NOT NULL COMMENT '关联 reports.id',
  topic_name VARCHAR(256) NOT NULL COMMENT 'AI提炼的热点名称',
  related_boards JSON NULL COMMENT '关联的东财板块名数组',
  logic_summary TEXT NULL COMMENT 'AI总结的逻辑摘要',
  source_article_ids JSON NULL COMMENT '关联 raw_articles.id 的数组',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_report_id (report_id),
  CONSTRAINT fk_hot_topics_report FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='热点风口表';


-- 7. stock_pool_1（异动初筛表 - 节点3产出）
CREATE TABLE IF NOT EXISTS stock_pool_1 (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  report_id BIGINT UNSIGNED NOT NULL COMMENT '关联 reports.id',
  stock_code VARCHAR(32) NOT NULL COMMENT '股票代码',
  stock_name VARCHAR(128) NOT NULL COMMENT '股票名称',
  related_topic_id BIGINT UNSIGNED NULL COMMENT '关联 hot_topics.id',
  snapshot_data JSON NULL COMMENT '行情快照: price, change_pct, volume_ratio等',
  match_reason VARCHAR(512) NULL COMMENT '入选理由',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_report_id (report_id),
  KEY idx_topic_id (related_topic_id),
  KEY idx_stock_code (stock_code),
  CONSTRAINT fk_pool1_report FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
  CONSTRAINT fk_pool1_topic FOREIGN KEY (related_topic_id) REFERENCES hot_topics(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='异动初筛表';


-- 8. stock_pool_2（深度精选表 - 节点4产出）
CREATE TABLE IF NOT EXISTS stock_pool_2 (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  report_id BIGINT UNSIGNED NOT NULL COMMENT '关联 reports.id',
  pool_1_id BIGINT UNSIGNED NOT NULL COMMENT '关联 stock_pool_1.id',
  stock_code VARCHAR(32) NOT NULL COMMENT '股票代码',
  stock_name VARCHAR(128) NOT NULL COMMENT '股票名称',
  tech_score DECIMAL(5,2) NULL COMMENT '技术面评分',
  fund_score DECIMAL(5,2) NULL COMMENT '基本面评分',
  total_score DECIMAL(5,2) NULL COMMENT '总分',
  ai_analysis TEXT NULL COMMENT 'AI分析文本',
  rule_results JSON NULL COMMENT '各规则检查结果',
  is_selected BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否最终入选',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_report_id (report_id),
  KEY idx_pool1_id (pool_1_id),
  KEY idx_is_selected (is_selected),
  CONSTRAINT fk_pool2_report FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
  CONSTRAINT fk_pool2_pool1 FOREIGN KEY (pool_1_id) REFERENCES stock_pool_1(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='深度精选表';


-- 9. target_accounts（目标公众号列表）
CREATE TABLE IF NOT EXISTS target_accounts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  account_name VARCHAR(128) NOT NULL COMMENT '公众号名称',
  wx_id VARCHAR(64) NULL COMMENT '微信号',
  status VARCHAR(32) NOT NULL DEFAULT 'active' COMMENT '状态: active, inactive',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='目标公众号列表';


-- 10. strategy_config（策略参数配置）
CREATE TABLE IF NOT EXISTS strategy_config (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  rule_key VARCHAR(128) NOT NULL COMMENT '规则标识',
  rule_name VARCHAR(128) NOT NULL COMMENT '规则名称',
  rule_value JSON NOT NULL COMMENT '规则参数值',
  description TEXT NULL COMMENT '描述',
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '执行顺序',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_rule_key (rule_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='策略参数配置表';
