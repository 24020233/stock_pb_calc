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
