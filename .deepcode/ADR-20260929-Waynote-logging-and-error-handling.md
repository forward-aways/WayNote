# ADR-20260929：前后端统一异常处理与日志机制

- 状态：已完成（Phase 5，2026-09-29，范围 C / stdlib / 保留 14 天）
- 日期：2026-09-29
- 范围：后端结构化日志（含高亮、轮转、留存清理、脱敏、请求追踪）+ 统一异常处理；前端统一异常链路（拦截器收敛 + 全局兜底）+ 彩色日志 +（可选）错误上报
- 不包含：第三方 APM/Sentry 接入、日志写数据库、Web 日志查看面板、多进程部署方案改造（只记录边界与演进路径）
- 生成方式：deepcode-architect-skill 工作流（DeepSeek V4.1 Flash 执行）

---

## 1. 背景与现状取证

用户要求检查"完整异常处理 + 统一日志（打印/高亮/留存/定期清除）"，没有则设计完整方案。

**实测证据（本仓库当前状态）**：

| 检查项 | 结果 | 证据 |
|---|---|---|
| 后端 logging 引用 | 0 处 | 全量扫描 `backend/app/**/*.py`：无 `import logging` / `getLogger` / `dictConfig` |
| 后端异常处理器 / 中间件 | 0 个 | 无 `exception_handler` / `add_middleware` / `middleware(` |
| 后端错误响应 | FastAPI 默认 | 500 = 纯文本/默认 JSON，无 request_id，无服务端日志 |
| 前端全局兜底 | 0 个 | 无 `app.config.errorHandler`、无 `unhandledrejection`、无 `window.onerror` |
| 前端日志设施 | 0 个 | 无 `console.*` 调用、无 logger 模块；`ElMessage.error` 散落 14 处 |
| 日志留存/清理 | 不存在 | 无 logs 目录；`backend/logs/*` **未被 .gitignore 忽略**（隐患） |

**问题定性**：
1. 500 错误对用户是"哑failed"（前端只见到泛化提示），对开发者无任何痕迹 → 线上问题只能靠复现。
2. 无请求 ID → 一次用户报错无法在日志里定位到那一次请求（且当前根本没有日志）。
3. 4xx/5xx 无分级处理，`IntegrityError` 这类数据库异常会以 500 形式裸奔。
4. 前端 14 个 catch 各写各的提示，行为不一致（有的带后端 detail，有的写死），且全部不落痕。
5. 无留存策略 → 一旦加文件日志，磁盘无人管理；敏感信息（password/token）有进日志的风险。

## 2. Phase 1 分析

- **需求复述**：建立"记录（日志）— 分级（异常分类）— 追踪（请求 ID）— 呈现（高亮）— 治理（留存/清理/脱敏）"的完整闭环，前后端一致。
- **隐式约束**：零新增后端依赖优先（`python-json-logger`、`colorlog` 均不引入，stdlib 足够）；不改变现有 API 契约；测试不能污染 logs 目录；个人工具规模（单进程、低流量），方案不能过重；Windows 开发 + Linux 部署双环境（ANSI/UTF-8 兼容）。
- **复杂度分类**：中。难点集中在三处：① `contextvars` 在 ASGI 中间件中的正确传播（BaseHTTPMiddleware 会破坏它）；② 多进程下文件轮转的边界；③ 脱敏与 422 校验错误（其 detail 会携带原始输入值）。
- **风险与边界（≥3）**：
  1. `BaseHTTPMiddleware` 把请求体处理放到独立 task，`contextvars` 不向端点传播 → request_id 会丢；且流式响应/后台任务有已知坑。
  2. uvicorn 自带 access 日志会与本方案访问日志**重复打印**。
  3. 多 worker 或多进程（`--reload` 的 reloader 子进程 + 主进程）同时持有 TimedRotatingFileHandler 会丢行/轮转冲突。
  4. 422 的 `errors[].input` 会包含密码等原始输入 → 直接落日志即泄密。
  5. Windows 控制台 GBK 编码与 ANSI 支持不一致 → 中文日志乱码/高亮失效。

### 2.1 根因分析

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | 错误对用户不可诊断、对开发者不可追踪，敏感信息有落盘风险 | 扫描结果全为 0 处日志/兜底代码 |
| 直接原因 | 后端无 logger/中间件/异常处理器；前端无拦截器收敛与全局兜底 | 同上 |
| 根因 | 项目缺少"日志与异常"这一横切关注点的**唯一边界**：谁记录、记什么级别、如何脱敏、存多久、如何清理，均无定义；每个 catch 各自为政 | 14 处散落 catch + 后端裸 500 |
| 泛化性质 | 属**一类问题**（任何新增端点/页面都会重复缺日志缺兜底），必须以"中间件 + 拦截器 + 常量契约"系统性解决，而非逐处补日志 | — |

### 2.2 快速补丁 vs 系统方案

| 方案 | 解决根因？ | 防复发？ | 泛化性 |
|---|---|---|---|
| 每个端点/视图里手写 `print`/`console.log` | 否 | 否 | 差（新代码照旧漏） |
| 仅加全局 exception_handler 不建日志体系 | 部分 | 否 | 有 ID 无留痕，问题依旧不可回溯 |
| **中间件 + contextvar + 统一 Formatter/Filter + 前端拦截器** | 是 | 是（横切、自动生效） | 强（新端点/新页面天然纳入） |

## 3. Phase 2 设计（后端）

### 3.1 组件与数据流

```
请求 → RequestContextMiddleware(纯 ASGI)           # 生成/透传 X-Request-ID，contextvar 注入，计时
        → 路由/依赖(get_current_user 注入 user_id)  # 业务日志自动带 request_id/user_id
        → 端点业务日志 get_logger("waynote.api.x")
        → 未捕获异常 → install_exception_handlers  # 分级：422/409/404/5xx
      ← 响应(带 X-Request-ID) ← 访问日志(状态分级+耗时+高亮)
```

### 3.2 日志核心 `app/core/logging.py`

- `setup_logging()`（幂等，`main.py` 导入时调用）：配置 root + `uvicorn`/`uvicorn.error` 走我们的 handler；**禁用 `uvicorn.access`**（避免重复），访问日志由中间件统一输出。
- 双写 Handler：
  - **Console**：人类可读 + ANSI 高亮（仅 TTY 或 `LOG_COLOR=always`；`never` 关闭）。
  - **File**：JSON Lines（`json.dumps(ensure_ascii=False)`，每行一条，便于 `jq`/grep），`TimedRotatingFileHandler(when="midnight", backupCount=log_retention_days, encoding="utf-8", delay=True)` → **每日轮转 + 自动删除过期文件**，即"定期清除"，无需 cron。
- **高亮规则（控制台）**：级别色（DEBUG 灰 / INFO 蓝 / WARNING 黄 / ERROR 红 / CRITICAL 红底）；HTTP 状态码按 2xx 绿 / 4xx 黄 / 5xx 红；耗时超 `log_slow_request_ms` 黄色、2 倍以上红色；`request_id` 青色。
- `MaskingFilter`：对最终输出统一脱敏（正则）——`password/passwd/token/secret/authorization/cookie` 的值 → `***`；邮箱保留前 2 位 `de***@example.com`。同时**原则性禁止**记录请求体与 Authorization 头。
- `get_logger(name)`：统一前缀 `waynote.`，业务模块用 `get_logger("api.trips")`。
- 上下文：`request_id_var` / `user_id_var`（ContextVar，默认 `-`/`None`），由中间件与 `get_current_user` 写入，访问日志与业务日志统一注入。
- Windows 兼容：启动时尝试 `sys.stdout.reconfigure(encoding="utf-8")`；文件显式 `encoding="utf-8"`；ANSI 通过 `LOG_COLOR` 可关。

### 3.3 中间件 `app/core/middleware.py`（**纯 ASGI**）

- 为什么不用 `BaseHTTPMiddleware`：请求被放入独立 task，contextvar 不传播到端点（request_id 丢失），且流式/后台任务有已知问题。纯 ASGI 中间件与端点在**同一调用栈**，contextvar 天然可见。
- 行为：读取 `X-Request-ID`（缺失则 `uuid4().hex[:12]`）→ 设置 contextvar → 包一层 `send` 捕获状态码 → 完成后输出访问日志（method/path/status/duration/user_id/ip）→ 响应头回写 `X-Request-ID`。
- 级别映射：5xx ERROR、4xx WARNING（404 INFO）、2xx INFO；`/api/v1/health` 降为 DEBUG（避免探活刷屏）。
- 边界：中间件内部异常自行兜底记录（`Exception` 处理器无法捕获中间件抛出的异常，这是 FastAPI 的已知边界）；WebSocket/SSE 不在本次范围。

### 3.4 统一异常处理 `app/core/errors.py`

| 异常 | HTTP | 响应体（统一信封） | 日志级别 | 要点 |
|---|---|---|---|---|
| `HTTPException` / `StarletteHTTPException` | 原状态码 | `{detail, request_id}` | 404→INFO；401/403/409/422/429→WARNING | 保留原始 `headers`（如 `WWW-Authenticate`） |
| `RequestValidationError` | 422 | `{detail: "请求参数校验失败", errors:[{loc,msg}], request_id}` | WARNING | **只记录 loc/msg，绝不记录 input 值**（防密码入日志） |
| `IntegrityError`（SQLAlchemy） | 409 | `{detail: "数据冲突或不满足约束", request_id}` | ERROR | 记录约束名；不回传数据库细节 |
| 未捕获 `Exception` | 500 | `{detail: "服务器内部错误，请稍后重试", request_id}` | ERROR + 完整堆栈 | 绝不泄露堆栈给客户端 |

（响应体保持 `detail` 为字符串 → 与前端现有 `apiErrorMessage` 兼容，属向后兼容的增强。）

### 3.5 业务审计日志（INFO）

- 认证：注册成功、登录成功/失败（失败含邮箱脱敏 + IP）。
- 变更：行程/天/地点的创建/更新/删除（含 id 与关键字段名，不含内容全量）。
- 目的：个人工具最实用的场景是"我误删了什么/什么时候改的"。
- 实现：`get_logger("waynote.api.x")` + ~12 处显式调用；`user_id` 从 contextvar 自动注入，无需逐处传。

### 3.6 配置（`Settings` 新增，均有默认值）

```python
log_level: str = "INFO"
log_to_file: bool = True                     # 测试置 false，不污染仓库
log_dir: Path = <backend>/logs
log_retention_days: int = 14                 # 文件保留天数（自动清理）
log_color: Literal["auto","always","never"] = "auto"
log_slow_request_ms: int = 800
```
同步更新 `.env.example`、`.gitignore`（`backend/logs/`）、README。

## 4. Phase 2 设计（前端）

### 4.1 统一异常链路（唯一漏斗：axios 拦截器）

- `http.ts` 响应拦截器 → 统一构造 `ApiError`：
  `{ status, code, detail, requestId(from X-Request-ID 或响应体), isNetwork, isTimeout, isCanceled }`；
  网络错误/超时给出人话（"网络异常，请检查网络连接"/"请求超时"）。
- **提示策略（实现定稿，替换原设计）**：拦截器只做归一化/分级留痕/401；提示仍由调用方经 `apiErrorMessage` 输出，**5xx 文案自动附带编号后 8 位**。原因：自动 toast 会造成双层提示与多模块 `silent` 连锁改造（见 §11 偏差 1）。
- 5xx 提示附带 `（编号 xxxx）`（request_id 后 8 位）→ 用户报错时可直接 grep 后端日志，闭环。
- 401 延续现状（清 token → /login），日志走 logger。
- 视图重构：删除多余的 catch-toast，保留业务分支（422 表单内联错误、404 重定向）。

### 4.2 全局兜底（`main.ts` 注册）

- `app.config.errorHandler`（Vue 渲染/生命周期异常）→ logger.error + 节流 toast +（可选）上报。
- `window.unhandledrejection` / `window.error` → 同上。
- `router.onError`（如分包加载失败）→ logger + 提示刷新。

### 4.3 日志与高亮 `src/utils/logger.ts`

- `logger.debug/info/warn/error`，`%c` 彩色前缀（与品牌一致：朱砂红=error、赭金=warn、黛青=info）。
- 级别策略：dev 全量；prod 仅 warn/error（避免控制台噪音）。`import.meta.env.DEV` 判定。
- Lambda 化输出：对象参数结构化打印，避免 `[object Object]`。

### 4.4（可选）错误上报 `POST /api/v1/client-logs`

- 前端 `reportError()`：指纹去重（相同 message+url 60s 内只报一次，单会话上限 20 条），body ≤8KB，截断 stack。
- 后端：Pydantic 限长校验 + 内存令牌桶限流（10 次/分钟/IP）+ 写入 `waynote.frontend` WARNING；有 token 时可关联 user_id。
- 风险与妥协：未认证写接口存在刷日志风险 → 限流 + 体积上限 + 日志保留兜底；**个人工具接受此权衡**；若后续开放注册需升级（签名/鉴权）。
- 前端"留存与清除"：console 日志天然无留存；上报日志的留存/清除由后端文件策略统一负责（避免两层 retention 复杂度）。

## 5. 防复发机制

1. 日志级别/格式/脱敏集中在 `logging.py`，业务代码只允许 `get_logger()` + `%s` 占位符（禁止 f-string 直接拼敏感值；占位符延迟求值也利于性能）。
2. `MaskingFilter` 是最后防线，即使业务代码写错也不落明文。
3. 前端只有 `http.ts` 一个错误漏斗 + `logger.ts` 一个日志出口，新增页面无需重复实现。
4. 测试守卫：脱敏、422 不含 input、request_id 贯通、轮转清理、级别映射（见 §6）。
5. `.gitignore` 防日志入库；`log_to_file=false` 测试隔离。

## 6. 测试与验收计划

| ID | 类型 | 内容 | 期望 |
|---|---|---|---|
| L1 | 回归 | 触发未捕获异常（临时测试端点/直接调用 handler） | 500 + `request_id`；caplog 有 ERROR 与堆栈；响应无堆栈 |
| L2 | 安全 | 日志内容含 `password=abc123`、`token=xx`、邮箱 | 输出为 `password=***`、`token=***`、`de***@example.com` |
| L3 | 安全 | 422 校验失败（密码字段非法） | 响应与日志均不含原始密码值；含 loc/msg |
| L4 | 追踪 | 任意请求 | 响应头 `X-Request-ID` 与响应体 request_id 一致；访问日志同 ID |
| L5 | 分级 | 200 / 404 / 500 各一次 | 访问日志分别 INFO / INFO(404) / ERROR；耗时与状态色（人工目视） |
| L6 | 留存 | 临时目录 + retention=2，`doRollover()` 两次 | 只保留最近 2 个备份文件（自动清除生效） |
| L7 | 隔离 | 运行 pytest | 仓库不产生 `backend/logs` 文件 |
| L8 | 前端 | type-check / lint / build | 全绿 |
| L9 | 前端手动 | 断网请求、5xx、401、表单 422 | 提示文案正确；5xx 含编号；console 彩色且 dev/prod 分级正确 |

## 7. 被否决的替代方案

| 方案 | 否决理由 |
|---|---|
| loguru / colorlog / python-json-logger | 体验更好但引入依赖；stdlib 三件套（Formatter/Filter/Handler）已能覆盖本需求，遵循零依赖原则 |
| 第三方 APM（Sentry） | 个人工具过重、需外部服务与密钥；自建上报 + 文件日志足够 |
| 日志写数据库 | 写放大影响主库、增加迁移与查询复杂度；grep/jq 对当前规模更高效 |
| `BaseHTTPMiddleware` | contextvar 不传播（request_id 丢失）+ 流式/后台任务坑 |
| 前端 localStorage 环形日志 | 无消费方、隐私与容量问题（反例：只有在"需要用户回放操作"场景才值得做） |
| 每个视图各自 try/catch + toast | 现状方案，行为不一致且零留痕，已证明不可维护 |
| systemd/journald 托管日志 | 部署阶段更优雅，但本地开发无 systemd；本方案开发/生产一致，journald 列为上线演进项 |

## 8. 泛化边界与反例

- **适用**：本项目 HTTP 请求链路（FastAPI + axios）；单进程部署（systemd 单 worker）。
- **不适用/反例**：
  1. **多进程/多 worker**：TimedRotatingFileHandler 非多进程安全（会丢行/轮转竞争）→ 该场景需换 journald、logrotate 或集中式采集，本方案明确不支持；
  2. WebSocket/SSE 长连接不在中间件覆盖内，需独立接入点；
  3. Alembic 迁移日志走其自身 `fileConfig`，与本体系并行（互不干扰，也不统一）；
  4. 本方案**不是合规级审计**（可被清理、无签名、无防篡改），不能用于法律用途；
  5. 中间件自身抛出的异常不被 `exception_handler` 捕获（FastAPI 边界），由中间件内部兜底。

## 9. 实现清单（Phase 3 预览）

后端新增：`app/core/logging.py`、`app/core/errors.py`、`app/core/middleware.py`、`app/api/v1/client_logs.py`（可选）、`backend/tests/test_logging.py`、`backend/tests/test_error_handlers.py`。
后端修改：`app/main.py`、`app/core/config.py`、`app/api/deps.py`（注入 user_id）、业务端点加审计日志（auth/trips/trip_days/places）、`backend/tests/conftest.py`（测试隔离环境变量）、`.env.example`、`.gitignore`、README。
前端新增：`src/utils/logger.ts`、`src/api/clientLog.ts`（可选）。
前端修改：`src/api/http.ts`（ApiError + 唯一漏斗）、`src/main.ts`（全局兜底）、4 个视图（去重复 toast）、`src/utils/error.ts`（并入 ApiError）。
无新依赖；无数据库变更；无 API 契约破坏（仅新增字段/新端点）。

## 10. 待确认问题

1. 实现范围：A 仅后端 / B 后端 + 前端链路（推荐）/ C 全量含错误上报。
2. 日志实现：stdlib（推荐，零依赖）/ loguru（+1 依赖，写法更简洁）。
3. 留存默认 14 天、文件 JSON Lines，是否可接受（可通过环境变量调整）。

## 11. 最终结果（Phase 5）

- 状态：已完成（范围 C：后端 + 前端 + 上报），stdlib 实现，保留 14 天。
- 实际变更：
  - 后端新增：`core/logging.py`（上下文变量 / 脱敏 / 高亮控制台 / JSON Lines / 轮转留存 / 启动清扫 / uvicorn 收敛）、`core/middleware.py`（纯 ASGI 请求追踪 + 访问日志 + 未捕获异常兜底 500）、`core/errors.py`（HTTP/校验/约束统一信封）、`api/v1/client_logs.py`（前端上报，限流 + 体积上限）。
  - 后端修改：`main.py` 装配、`config.py` 新增 6 个日志配置、`deps.py` 注入 user_id、四个业务路由加审计日志、`conftest.py` 测试隔离、`.gitignore`、`.env.example`、README。
  - 前端新增：`api/error.ts`（ApiError + 归一化）、`api/clientLog.ts`（上报：指纹去重 / 会话上限 / keepalive fetch）、`utils/logger.ts`（彩色分级，颜色从设计令牌读取）。
  - 前端修改：`api/http.ts`（唯一漏斗：归一化 + 分级留痕 + 401 防抖）、`utils/error.ts`（5xx 自动附编号后 8 位）、`main.ts`（Vue/window/router 三处全局兜底）。
- 测试结果：
  - 后端：**20 passed**（新增 11：脱敏 2、高亮 1、轮转装配 1、留存清扫 1、uvicorn 收敛 1、422 防泄漏 1、404 信封/追踪 1、500 统一信封 1、访问级别映射 1、上报限流/审计 1）；ruff 通过；测试不产生 `backend/logs`。
  - 实机（真实 HTTP + 真实日志文件）17 项全过：401/404/422 信封与 `X-Request-ID` 贯通、422 不回显输入、登录失败/成功审计、前端上报 204、健康检查 DEBUG 降噪、JSON Lines 合法、访问日志无重复、邮箱掩码、无明文口令。
  - 控制台高亮 10 项全过（ANSI 序列、级别色、状态码色、request_id、掩码、级别过滤）。
  - 前端：type-check / lint（含令牌守卫）/ build 全绿。
- 偏差与经验：
  1. **实现偏差（重要）**：原设计"拦截器默认自动 toast、silent 交调用方"在实现时改为「**拦截器只做归一化/留痕/401，提示仍由调用方经 `apiErrorMessage` 输出，5xx 自动附编号**」。原因：自动 toast 会造成双层提示与"静默开关"在 3 个 API 模块的连锁改造；现方案改动面小且用户可见效果一致（编号闭环保留）。已同步 §4.1 描述以此节为准。
  2. logger 颜色原计划硬编码，被 `check-tokens` 守卫拦截 → 改为**从 tokens.css 的 CSS 变量读取**（延迟到首次输出并缓存），使前端日志颜色也遵循设计令牌单一来源。
  3. 测试自身 bug：留存清扫用例硬编码 2023 时间戳导致"新鲜文件"实际过期；改用 `time.time()`。
  4. 验证脚本 bug：HTTP 头大小写不敏感，而脚本用字典精确匹配导致误报 `X-Request-ID` 缺失；产品侧无问题（curl 已证实回显）。
  5. 404（未匹配路由）的 `detail` 为 Starlette 默认 "Not Found"（英文）；如需全中文可后续为 404 增加映射，不影响信封结构。
  6. 未捕获异常在中间件兜底时不走 FastAPI 的 `exception_handler(Exception)`（Starlette 会 re-raise 并让 uvicorn 再打一份堆栈）；本实现直接在中间件捕获并返回信封，避免了重复堆栈与丢失追踪头。
- 遗留/边界：多进程部署下文件轮转不安全（需 journald/logrotate）；WebSocket 不在覆盖内；前端上报为未认证写接口（限流 + 体积上限兜底），开放注册后需升级签名/鉴权。
