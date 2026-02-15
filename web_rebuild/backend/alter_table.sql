-- 数据库表结构修改脚本
-- 用于将旧的 wx_article_detail 表结构更新为新的表结构

-- 创建备份表（可选，用于数据迁移）
CREATE TABLE IF NOT EXISTS wx_article_detail_old
AS SELECT * FROM wx_article_detail;

-- 删除旧的外键约束（如果存在）
SET FOREIGN_KEY_CHECKS = 0;

-- 修改 wx_article_detail 表结构

-- 1. 重命名列
-- 旧字段名 -> 新字段名
-- article_url -> url
-- post_time -> pubtime
-- wxid -> hashid
-- html -> content

-- 先检查列是否存在，然后修改
SELECT column_name
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'wx_article_detail'
  AND column_name IN ('article_url', 'post_time', 'wxid', 'html');

-- 重命名列（注意：MySQL 8.0+ 支持 ALTER TABLE ... RENAME COLUMN）
-- 如果是 MySQL 5.x，需要先添加新列，复制数据，再删除旧列

-- 方法 1: 使用 ALTER TABLE RENAME COLUMN (MySQL 8.0+)
ALTER TABLE wx_article_detail
CHANGE COLUMN article_url url VARCHAR(2048) NOT NULL COMMENT '文章链接' FIRST;

ALTER TABLE wx_article_detail
CHANGE COLUMN post_time pubtime BIGINT NULL COMMENT '发文时间戳';

ALTER TABLE wx_article_detail
CHANGE COLUMN wxid hashid VARCHAR(64) NULL COMMENT '文章唯一hashid';

ALTER TABLE wx_article_detail
CHANGE COLUMN html content MEDIUMTEXT NULL COMMENT '文章正文内容';

-- 2. 添加新列
-- 如果 nick_name 列不存在，则添加
SELECT COUNT(*) INTO @has_nick_name
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'wx_article_detail'
  AND column_name = 'nick_name';

SET @sql = NULL;
SET @sql = CONCAT('
ALTER TABLE wx_article_detail
ADD COLUMN nick_name VARCHAR(128) NULL COMMENT ''公众号名字''
AFTER hashid
');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 3. 更新 url_hash 生成表达式
-- 需要删除旧的生成列，然后重新添加
-- 注意：不能直接修改生成列的表达式，只能删除后重新添加

ALTER TABLE wx_article_detail
DROP COLUMN url_hash;

ALTER TABLE wx_article_detail
ADD COLUMN url_hash BINARY(16) GENERATED ALWAYS AS (UNHEX(MD5(url))) STORED COMMENT 'URL哈希'
AFTER url;

-- 4. 重新创建索引
-- 删除旧的索引
DROP INDEX IF EXISTS uk_article_url ON wx_article_detail;
DROP INDEX IF EXISTS idx_wxid ON wx_article_detail;

-- 创建新的索引
CREATE UNIQUE INDEX uk_url ON wx_article_detail (url_hash);
CREATE INDEX idx_hashid ON wx_article_detail (hashid);
CREATE INDEX idx_nick_name ON wx_article_detail (nick_name);

-- 5. 更新数据（如果需要）
-- 如果 nick_name 列为空，可以从关联的账号表中填充
UPDATE wx_article_detail d
JOIN wx_article_list l ON d.article_list_id = l.id
JOIN wx_mp_account a ON l.account_id = a.id
SET d.nick_name = a.mp_nickname
WHERE d.nick_name IS NULL;

-- 6. 恢复外键约束
SET FOREIGN_KEY_CHECKS = 1;

-- 验证修改后的表结构
DESCRIBE wx_article_detail;

-- 检查数据完整性
SELECT COUNT(*) as total_records,
       COUNT(DISTINCT url_hash) as unique_urls,
       COUNT(nick_name) as have_nick_name,
       COUNT(content) as have_content
FROM wx_article_detail;

-- 注意：
-- 1. 此脚本假设你使用的是 MySQL 8.0 或更高版本
-- 2. 如果是 MySQL 5.x，需要使用不同的方法来修改表结构
-- 3. 修改前建议先备份数据
-- 4. 如果是新数据库（还没有数据），建议直接使用 schema.sql 重新创建表
