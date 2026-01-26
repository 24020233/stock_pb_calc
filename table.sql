-- 建议：统一字符集
-- SET NAMES utf8mb4;

-- 1) 公众号表（来自接口返回 mp_nickname/mp_wxid/mp_ghid）
CREATE TABLE IF NOT EXISTS wx_mp_account (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

  mp_nickname VARCHAR(128) NOT NULL,   -- 公众号昵称
  mp_wxid VARCHAR(64) NULL,            -- 微信号（接口返回）
  mp_ghid VARCHAR(64) NULL,            -- gh_xxx（接口返回）

  enabled TINYINT(1) NOT NULL DEFAULT 1,
  last_list_fetch_at DATETIME NULL,

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  UNIQUE KEY uk_mp_wxid (mp_wxid),
  UNIQUE KEY uk_mp_ghid (mp_ghid),
  KEY idx_mp_nickname (mp_nickname)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 2) 列表页抓取记录（一次调用 dajiala post_condition）
-- 作用：记录请求参数、返回 code/msg、原始响应，方便复盘与重试
CREATE TABLE IF NOT EXISTS wx_article_list_fetch (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

  account_id BIGINT UNSIGNED NULL,       -- 可能先按 name 查不到账号信息，允许为空
  query_name VARCHAR(128) NOT NULL,      -- 请求里的 name（--name）
  api_url VARCHAR(255) NOT NULL DEFAULT 'https://www.dajiala.com/fbmain/monitor/v3/post_condition',

  request_json JSON NULL,               -- 可存：{"biz":"","url":"","name":"...","verifycode":"..."}（不要存 key）
  response_code INT NULL,               -- resp["code"]
  response_msg VARCHAR(512) NULL,        -- resp["msg"]
  mp_nickname VARCHAR(128) NULL,         -- resp["mp_nickname"]
  mp_wxid VARCHAR(64) NULL,              -- resp["mp_wxid"]
  mp_ghid VARCHAR(64) NULL,              -- resp["mp_ghid"]

  item_count INT UNSIGNED NULL,          -- len(resp["data"])
  response_json JSON NULL,               -- 原始完整响应（可选：也可只存 data）

  fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  KEY idx_fetch_account_time (account_id, fetched_at),
  KEY idx_fetch_query_time (query_name, fetched_at),
  CONSTRAINT fk_fetch_account
    FOREIGN KEY (account_id) REFERENCES wx_mp_account(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 3) 列表条目（文章种子/列表结果）
-- 字段严格对齐 script.py 输出的 JSONL
CREATE TABLE IF NOT EXISTS wx_article_seed (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

  account_id BIGINT UNSIGNED NOT NULL,
  fetch_id BIGINT UNSIGNED NULL,         -- 来自哪次列表抓取（可选）

  mp_nickname VARCHAR(128) NULL,
  mp_wxid VARCHAR(64) NULL,
  mp_ghid VARCHAR(64) NULL,

  title VARCHAR(256) NULL,
  digest TEXT NULL,
  url VARCHAR(2048) NOT NULL,
  url_hash BINARY(16)
    GENERATED ALWAYS AS (UNHEX(MD5(url))) STORED,

  position INT NULL,                     -- a["position"]
  post_time BIGINT NULL,                 -- a["post_time"]（接口通常是时间戳；单位按实际写入）
  post_time_str VARCHAR(64) NULL,        -- a["post_time_str"]
  cover_url VARCHAR(2048) NULL,

  original TINYINT NULL,                 -- a["original"]（0/1）
  item_show_type INT NULL,               -- a["item_show_type"]
  types JSON NULL,                       -- a["types"]（可能是数组/对象，用 JSON 最稳）
  is_deleted TINYINT NULL,               -- a["is_deleted"]
  msg_status INT NULL,                   -- a["msg_status"]
  msg_fail_reason VARCHAR(512) NULL,     -- a["msg_fail_reason"]

  first_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  UNIQUE KEY uk_account_url (account_id, url_hash),
  KEY idx_account_post_time (account_id, post_time),
  KEY idx_account_last_seen (account_id, last_seen_at),
  KEY idx_fetch (fetch_id),

  CONSTRAINT fk_seed_account
    FOREIGN KEY (account_id) REFERENCES wx_mp_account(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_seed_fetch
    FOREIGN KEY (fetch_id) REFERENCES wx_article_list_fetch(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 4) 文章详情表（后续你抓详情时写入；列表字段对不上也不影响）
-- 这里给一个“通用详情表”，用 url_hash 与 seed/公众号关联
CREATE TABLE IF NOT EXISTS wx_article_detail (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

  account_id BIGINT UNSIGNED NOT NULL,
  seed_id BIGINT UNSIGNED NULL,

  url VARCHAR(2048) NOT NULL,
  url_hash BINARY(16)
    GENERATED ALWAYS AS (UNHEX(MD5(url))) STORED,

  -- 详情字段（按你后续抓取能力扩展）
  content_html MEDIUMTEXT NULL,
  content_text LONGTEXT NULL,

  fetched_at DATETIME NULL,
  status TINYINT NOT NULL DEFAULT 0,     -- 0=未抓 1=成功 2=失败
  error TEXT NULL,
  raw_json JSON NULL,                    -- 若详情接口返回结构化 JSON，可存一份原始

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  UNIQUE KEY uk_account_url (account_id, url_hash),
  KEY idx_seed (seed_id),
  KEY idx_account_status (account_id, status),

  CONSTRAINT fk_detail_account
    FOREIGN KEY (account_id) REFERENCES wx_mp_account(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_detail_seed
    FOREIGN KEY (seed_id) REFERENCES wx_article_seed(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 5) 每日板块总结（由 LLM 从当日文章中抽取）
CREATE TABLE IF NOT EXISTS wx_sector_daily (
  day DATE NOT NULL,
  sector VARCHAR(128) NOT NULL,
  mention_count INT NOT NULL DEFAULT 0,    -- 被多少篇文章提到（按文章去重）
  articles JSON NULL,                      -- [{"id":123,"title":"...","url":"..."}, ...]
  raw_json JSON NULL,                      -- 保存 LLM 原始结构化输出（可选）

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (day, sector),
  KEY idx_day (day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 6) 板块选股结果（由“板块总结” + 东方财富概念板块成分股生成）
CREATE TABLE IF NOT EXISTS wx_sector_stock_pick (
  day DATE NOT NULL,
  sector VARCHAR(128) NOT NULL,
  stock_code VARCHAR(16) NOT NULL,
  stock_name VARCHAR(64) NOT NULL,

  latest_price DECIMAL(18, 4) NULL,
  pct_change DECIMAL(10, 4) NULL,
  open_price DECIMAL(18, 4) NULL,
  prev_close DECIMAL(18, 4) NULL,
  turnover_rate DECIMAL(10, 4) NULL,
  pe_dynamic DECIMAL(18, 4) NULL,
  pb DECIMAL(18, 4) NULL,

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (day, sector, stock_code),
  KEY idx_day (day),
  KEY idx_day_sector (day, sector),
  KEY idx_stock_code (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;