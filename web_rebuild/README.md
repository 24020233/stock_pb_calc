# 蓝胖子自动选股系统

基于 FastAPI + React 的自动化股票选股系统。

## 功能特性

- **情报源管理**：通过公众号爬取获取实时财经资讯
- **AI 热点提炼**：使用 DeepSeek LLM 智能识别热点板块
- **异动初筛**：通过 akshare 获取东方财富板块成分股
- **深度精选**：可配置的规则引擎（技术面+基本面）
- **可视化流程**：完整的选股流程可追溯

## 技术栈

### 后端
- FastAPI - 异步 Web 框架
- MySQL - 数据库
- aiomysql - 异步 MySQL 驱动
- akshare - 股票数据接口
- OpenAI SDK - DeepSeek API 调用

### 前端
- React 18 + TypeScript
- Vite - 构建工具
- Ant Design - UI 组件库
- React Router - 路由管理
- Axios - HTTP 客户端

## 项目结构

```
web_rebuild/
├── backend/
│   ├── main.py                  # FastAPI 应用入口
│   ├── config.py                # 配置管理
│   ├── database.py              # 数据库连接
│   ├── schema.sql               # 数据库表结构
│   ├── requirements.txt         # Python 依赖
│   ├── migrate_v2_stock_picker.py  # 数据库迁移脚本
│   ├── init_rules.py            # 初始化默认规则
│   ├── api/
│   │   ├── articles.py          # 文章相关 API
│   │   ├── reports.py           # 报告管理 API
│   │   ├── pipeline.py          # 选股流程 API
│   │   ├── settings.py          # 系统设置 API
│   │   └── stocks.py            # 股票数据 API
│   ├── services/
│   │   ├── crawler.py           # 公众号爬虫服务
│   │   ├── llm_service.py       # LLM 服务（DeepSeek）
│   │   ├── stock_service.py     # 股票数据服务（akshare）
│   │   └── pipeline_service.py  # 选股流程编排
│   └── rules/
│       ├── base.py              # 规则基类
│       ├── technical.py         # 技术面规则
│       ├── fundamental.py       # 基本面规则
│       └── registry.py          # 规则注册器
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── App.css
│       ├── router/
│       │   └── index.tsx
│       ├── types/
│       │   └── index.ts
│       ├── services/
│       │   └── api.ts
│       └── pages/
│           ├── HomePage.tsx
│           ├── ReportsPage.tsx
│           ├── ReportDetail.tsx
│           └── SettingsPage.tsx
├── .env                        # 环境配置
└── .env.example                # 环境配置示例
```

## 快速开始

### 1. 环境配置

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cd web_rebuild
cp .env.example .env
```

编辑 `.env` 文件：

```env
# MySQL 配置
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=wechat_crawler

# 大家拉 API 配置
DAJIALA_KEY=your_key_here
DAJIALA_VERIFYCODE=

# DeepSeek API 配置
DEEPSEEK_API_KEY=your_deepseek_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# API 服务器配置
API_HOST=0.0.0.0
API_PORT=8002
```

### 2. 数据库初始化

```bash
cd backend

# 运行数据库迁移
python migrate_v2_stock_picker.py

# 初始化默认规则
python init_rules.py
```

### 3. 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

后端服务将在 http://localhost:8002 启动，API 文档地址：http://localhost:8002/docs

### 4. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 http://localhost:3000 启动。

## 选股流程

系统采用 4 节点流水线设计：

### 节点 1：情报源
- 通过公众号爬虫获取最新财经文章
- 支持手动录入补充情报

### 节点 2：热点风口
- 使用 DeepSeek LLM 分析文章内容
- 智能识别热点板块和题材逻辑

### 节点 3：异动初筛
- 通过 akshare 获取东方财富板块成分股
- 生成股票池 1

### 节点 4：深度精选
- 应用可配置的选股规则（技术面+基本面）
- 生成最终精选股票池 2

## API 接口

### 报告管理 (`/api/reports`)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/` | 获取报告列表 |
| GET | `/:id` | 获取单个报告 |
| POST | `/` | 创建报告 |
| DELETE | `/:id` | 删除报告 |
| POST | `/:id/generate` | 生成报告 |
| GET | `/:id/check` | 检查数据 |
| GET | `/:id/summary` | 获取报告摘要 |

### 选股流程 (`/api/pipeline`)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/:report_id/nodes` | 获取流程节点数据 |
| POST | `/step1-articles` | 添加情报源 |
| POST | `/:report_id/step2-topics` | 提取热点 |
| POST | `/:report_id/step3-pool1` | 异动初筛 |
| POST | `/:report_id/step4-pool2` | 深度精选 |

### 系统设置 (`/api/settings`)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/accounts` | 获取公众号列表 |
| POST | `/accounts` | 添加公众号 |
| PATCH | `/accounts/:id` | 更新公众号 |
| DELETE | `/accounts/:id` | 删除公众号 |
| GET | `/rules` | 获取规则列表 |
| PATCH | `/rules/:key` | 更新规则配置 |

### 股票数据 (`/api/stocks`)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/boards` | 获取板块列表 |
| GET | `/boards/:name/stocks` | 获取板块成分股 |
| GET | `/:code/snapshot` | 获取个股快照 |
| GET | `/search/:keyword` | 搜索股票 |

## 规则引擎

系统采用策略模式实现可插拔的规则引擎：

### 已实现规则

**技术面规则**
- `market_cap` - 市值筛选
- `volume_ratio` - 量比筛选
- `price_change` - 涨跌幅筛选
- `turnover_rate` - 换手率筛选

**基本面规则**
- `pe_ratio` - 市盈率筛选
- `pb_ratio` - 市净率筛选
- `roe` - ROE 筛选

### 添加自定义规则

1. 在 `rules/technical.py` 或 `rules/fundamental.py` 中继承 `BaseRule`
2. 使用 `@register_rule` 装饰器注册
3. 实现 `check()` 方法

```python
from rules.base import BaseRule, RuleResult, register_rule

@register_rule
class MyCustomRule(BaseRule):
    @property
    def rule_key(self) -> str:
        return "my_custom_rule"

    @property
    def rule_name(self) -> str:
        return "我的自定义规则"

    def check(self, stock_context) -> RuleResult:
        # 实现规则逻辑
        return RuleResult(passed=True, score=1.0, reason="通过")
```

## 数据库表结构

- `reports` - 每日报告主表
- `raw_articles` - 情报源表
- `hot_topics` - 热点风口表
- `stock_pool_1` - 异动初筛表
- `stock_pool_2` - 深度精选表
- `target_accounts` - 目标公众号列表
- `strategy_config` - 策略参数配置表
- `wx_mp_account` - 公众号账号表（已有）
- `wx_article_list` - 文章列表表（已有）
- `wx_article_detail` - 文章详情表（已有）

详细表结构请参考 [schema.sql](backend/schema.sql)。

## 开发说明

### 后端开发

```bash
cd backend

# 安装开发依赖
pip install -r requirements.txt

# 代码格式化
black .

# 类型检查
mypy .
```

### 前端开发

```bash
cd frontend

# 代码格式化
npm run format

# 类型检查
npm run type-check

# 构建生产版本
npm run build
```

## 注意事项

1. **公众号爬取**：由于微信限制，无法按日期回溯历史文章，仅支持获取最新文章
2. **DeepSeek API**：需要配置有效的 API Key 才能使用 AI 热点提炼功能
3. **akshare 数据**：获取东方财富数据需要网络连接，部分接口可能有频率限制
4. **数据库**：首次使用需要运行迁移脚本创建表结构

## 许可证

MIT License
