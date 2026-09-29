# 途笺 WayNote

旅行行程规划工具：规划行程、管理景点、记录备忘与旅途笔记。移动端优先的 Web 应用。

> 域名规划：waynote.cn（ICP 备案中，暂未上线）

## 功能状态

- [x] 用户注册 / 登录（JWT 鉴权）
- [x] 行程（Trip）增删改查
- [x] 行程中的"天"（TripDay）增删改查
- [x] 地点（Place）增删改查，支持按天筛选
- [ ] 笔记（文字 + 图片）
- [ ] 备忘（清单 / 待办 / 提醒）
- [ ] 图片上传（腾讯云 COS）
- [ ] 只读分享链接
- [ ] 地图集成（腾讯位置服务）

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL 16 |
| 前端 | Vue 3 · Vite · TypeScript · Pinia · Element Plus |
| 认证 | JWT（python-jose）+ bcrypt |
| 工具链 | uv · pytest · ruff · ESLint · Prettier |

## 目录结构

```
backend/
  app/
    api/        # 路由与依赖（auth / trips / trip_days / places）
    core/       # 配置（Settings）与安全（JWT / bcrypt）
    db/         # 引擎与会话
    models/     # SQLAlchemy 模型（集中注册于 __init__.py）
    schemas/    # Pydantic 出入参
  alembic/      # 数据库迁移（连接串由 Settings 提供）
  tests/        # pytest 回归测试（事务回滚，不落数据）
frontend/
  src/
    api/         # axios 封装与接口
    components/  # AppIcon / SealTag / EmptyState / FormSheet / AppBar / TripCard / AuthShell
    composables/ # useIsMobile 等组合式函数
    router/      # 路由与登录守卫
    stores/      # Pinia
    styles/      # 设计令牌（tokens.css）与 Element Plus 皮肤（element.css）
    utils/       # 日期/状态/色板/错误提取等纯函数
    views/       # 页面（登录 / 注册 / 行程列表 / 行程详情）
```

## 本地开发

### 前置要求

- Python 3.13（由 uv 管理）
- Node.js `^22.18.0 || >=24.12.0`
- PostgreSQL 16（推荐 Docker）

### 1. 启动数据库

```bash
docker run -d --name waynote-pg \
  -e POSTGRES_USER=waynote \
  -e POSTGRES_PASSWORD=你的密码 \
  -e POSTGRES_DB=waynote \
  -p 5432:5432 \
  -v waynote_pgdata:/var/lib/postgresql/data \
  postgres:16
```

### 2. 启动后端

```bash
cd backend
cp .env.example .env        # Windows: copy .env.example .env
# 编辑 .env，填写 DATABASE_URL 与 SECRET_KEY（见下方"配置说明"）
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

接口文档：http://127.0.0.1:8000/docs

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 （`/api` 已在 `vite.config.ts` 中代理到 `127.0.0.1:8000`）。

## 测试与代码检查

```bash
uv run pytest -q              # 后端回归测试（默认复用本地开发库，事务回滚不落数据）
uv run ruff check backend     # Python 静态检查
cd frontend && npm run type-check   # 类型检查
cd frontend && npm run lint         # 设计令牌守卫 + oxlint + eslint
cd frontend && npm run build        # 生产构建
```

可选：设置 `TEST_DATABASE_URL` 指向独立测试库。

## 配置说明

- 所有后端配置统一由 `backend/.env` 提供（`app/core/config.py` 校验，缺失即启动失败）
- 生成 JWT 密钥：`python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `.env` 已在 `.gitignore` 中，**禁止提交真实值**；示例见 `backend/.env.example`

## 开发方式

本项目采用开源工程技能 [deepcode-architect-skill](https://github.com/forward-aways/deepcode-architect-skill) 的工作流开发：每个问题遵循「分析 → 设计 → ADR 沉淀 → 确认 → 实现 → 验证」闭环。

- 协作模型：DeepSeek V4.1 Flash
- 决策记录：见 [`.deepcode/`](./.deepcode)，ADR 由该工作流生成并持续更新

## 日志与异常处理

- **后端日志**：控制台为人话 + 高亮（级别色 / 状态码 2xx 绿·4xx 黄·5xx 红 / 慢请求黄红），文件为 JSON Lines，默认写入 `backend/logs/waynote.log`；**每日轮转、自动删除过期文件，默认保留 14 天**（`LOG_LEVEL` / `LOG_DIR` / `LOG_RETENTION_DAYS` / `LOG_COLOR` / `LOG_SLOW_REQUEST_MS` 见 `backend/.env.example`）。
- **请求追踪**：每个响应携带 `X-Request-ID`；5xx 的前端提示附带编号后 8 位，可据此直接定位后端日志：

  ```bash
  # 按请求编号检索（示例）
  jq 'select(.request_id == "abc123")' backend/logs/waynote.log
  ```

- **统一异常信封**：`{"detail": str, "request_id": str, "errors"?: [...]}`；422 不回显原始输入，500 不回显堆栈，数据库约束冲突转 409。
- **脱敏**：密码 / token / authorization 等一律置 `***`，邮箱保留前两位（如 `de***@example.com`）。
- **前端**：`src/api/http.ts` 拦截器是唯一错误出口（归一化 `ApiError`、分级留痕、401 处理）；`src/utils/logger.ts` 提供彩色分级日志（开发全量、生产仅 warn/error）；未捕获的 Vue / JS 异常节流提示并上报 `POST /api/v1/client-logs`（限流 10 次/分钟/IP + 指纹去重）。

## 部署（规划）

腾讯云轻量应用服务器（Ubuntu Server 24.04 LTS）：
Nginx 静态托管 `frontend/dist` + 反向代理 `/api` 到 uvicorn（systemd 托管），ICP 备案通过后上线。
