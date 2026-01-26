# stock_pb_calc

一个面向“公众号文章 → 板块总结 → 板块选股”的小型工具集：

- 后端：Flask API + 数据抓取/LLM 分析（统一在 `script.py`）
- 前端：Vue 3 + Vite 管理后台（`web/`）
- 数据：MySQL（表结构见 `table.sql`）

> 说明：仓库里还保留了一个早期的 PB 查询静态页服务（`server.py`），与管理后台无强耦合。

---
# stock_pb_calc

一个面向“公众号文章 → 板块总结 → 板块选股”的小型工具集：

- 后端：Flask API + 数据抓取/LLM 分析（统一在 `script.py`）
- 前端：Vue 3 + Vite 管理后台（`web/`）
- 数据：MySQL（表结构见 `table.sql`）

> 说明：仓库里还保留了一个早期的 PB 查询静态页服务（`server.py`），与管理后台无强耦合。

---

## 功能

- 公众号管理：增删改查、单个抓取、批量抓取（昨天/前天，内置限速）
- 文章种子入库：把列表数据写入 `wx_article_seed`
- 板块总结：从当日文章抽取板块（DeepSeek，严格 JSON 输出；支持“先取行业板块清单 → 只允许从清单中选”）
- 板块选股：根据板块热度拉取东方财富板块成分股并筛选，结果入库 `wx_sector_stock_pick`
- 前端展示：Sectors / Picks 页面，并支持 Picks 导出 Excel

---

## 目录结构

- `script.py`：主逻辑（CLI + Flask API 的单一事实来源）
- `api_server.py`：API 启动入口（包装 `create_app`）
- `wsgi.py`：生产部署入口（给 gunicorn 用）
- `table.sql`：MySQL 表结构（包含公众号/文章/板块总结/选股等）
- `clear_today_sectors.py`：清理指定日期的板块总结/选股
- `web/`：Vue 3 管理后台
- `deploy/`：Linux 部署示例（systemd + nginx）

---

## 快速开始（本地开发）

### 1) 准备 MySQL

创建数据库并导入表结构：

```bash
mysql -h 127.0.0.1 -u root -p -e "CREATE DATABASE IF NOT EXISTS test DEFAULT CHARSET utf8mb4;"
mysql -h 127.0.0.1 -u root -p test < table.sql
```

> 你也可以换库名，记得同步 `.env` 的 `MYSQL_DATABASE`。

### 2) 后端（Flask API）

创建虚拟环境并安装依赖：

```bash
cd /path/to/stock_pb_calc
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

创建本地配置：

```bash
cp .env.example .env
```

必填/常用配置项（在 `.env` 中设置）：

- `PASSWORD`：管理后台登录密码
- `MYSQL_HOST`/`MYSQL_PORT`/`MYSQL_USER`/`MYSQL_PASSWORD`/`MYSQL_DATABASE`
- `DAJIALA_KEY`：公众号列表抓取所需 key
- `DEEPSEEK_API_KEY`：板块总结所需 key

启动 API：

```bash
python3 api_server.py
# 或：python3 script.py  (如你更喜欢直接跑主文件)
```

默认监听：`http://127.0.0.1:8001`

### 3) 前端（Vue 管理后台）

```bash
cd web
npm install
npm run dev
```

访问：`http://127.0.0.1:5173`

前端 API 地址配置：

- 推荐开发态用 Vite 代理（同源请求 `/api/*`），减少 CORS 问题
- 也可在 `web/.env` 设置 `VITE_API_BASE_URL=http://127.0.0.1:8001`

（前端更详细说明见 `web/README.md`）

---

## 生产部署（简版）

仓库提供了一个可直接参考的部署方案：

- `deploy/stock_pb_calc.service`：systemd 启动 gunicorn
- `deploy/nginx.stock_pb_calc.conf`：nginx 静态站点 + `/api/*` 反向代理
- 说明文档：`deploy/README.md`

生产启动示例（仅供参考）：

```bash
gunicorn -w 2 -b 127.0.0.1:8001 wsgi:app
```

---

## API 概览

> 返回格式统一为：`{ success: boolean, data?: any, error?: string }`

- `POST /api/login`：后台登录（验证 `.env` 的 `PASSWORD`）
- `GET /api/health`：健康检查（含 DB 连通性）

板块：

- `GET /api/sectors?date=YYYY-MM-DD`：查询当天板块总结
- `POST /api/sectors/generate`：生成板块总结（支持 `force/maxArticles/fetchConcurrency`）

选股：

- `GET /api/picks?date=YYYY-MM-DD`：查询当天板块选股
- `POST /api/picks/generate`：生成板块选股（基于板块总结）

公众号/文章：

- `GET /api/accounts`、`POST /api/accounts`、`PATCH /api/accounts/:id`、`DELETE /api/accounts/:id`
- `POST /api/accounts/:id/fetch`：抓取该公众号文章列表并入库
- `GET /api/seeds`：文章种子列表
- `GET /api/fetches`：抓取日志（每次请求 dajiala 的记录）

---

## 常用脚本

清理某天数据（默认今天）：

```bash
python3 clear_today_sectors.py
# 清理指定日期
python3 clear_today_sectors.py --date 2026-01-26
# 只清理 picks 或 sectors
python3 clear_today_sectors.py --only picks
python3 clear_today_sectors.py --only sectors
```

---

## 排障（常见问题）

- **MySQL 连不上/超时**：检查 `MYSQL_*` 配置、远端安全组/防火墙；必要时调大 `MYSQL_TIMEOUT/MYSQL_READ_TIMEOUT/MYSQL_WRITE_TIMEOUT`。
- **本机系统代理影响抓取**：部分环境（如 ClashX）会让 requests/AkShare 走代理导致不稳定；后端对部分东方财富接口已做“proxy 失败 → 直连重试”的兜底。
- **生成板块太慢**：降低 `SECTOR_MAX_ARTICLES` 或 `SECTOR_ARTICLE_MAX_CHARS`，并适当提高 `SECTOR_FETCH_CONCURRENCY`。

---

## License

Private / internal use (no explicit license yet).
