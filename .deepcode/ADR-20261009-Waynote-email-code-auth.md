# ADR-20261009-Waynote-email-code-auth

**状态**：设计已提交，等待用户确认（CHECKPOINT）
**任务**：邮箱验证码登录 / 找回密码（重置）/ 已登录设置或修改密码 / 注册时邮箱验证
**决策来源**：用户答复①发信走 163 邮箱（授权码）②四条流程全做③未注册邮箱用验证码登录时**自动建号（免密）**

---

## 1. Context 与问题陈述

现有认证只有一条路径：`邮箱 + 密码 → JWT`（`backend/app/api/v1/auth.py`，68 行）。
缺少：邮箱验证码通道、密码找回、无密码账号的密码设置、注册时的邮箱归属验证。

需求（用户原话归纳）：

1. **邮箱验证码登录**（辅助登录：保留密码登录不变，新增一条免密通道）
2. **找回密码 / 重置密码**（忘记密码 → 邮箱验证码 → 设置新密码）
3. **已登录修改密码**（在「我的」里改；无密码账号要能「设置密码」）
4. **注册时邮箱验证码**（注册需要验证邮箱归属）
5. 未注册邮箱用验证码登录 → **自动建号（免密）**

---

## 2. 现状评估（已读代码）

| 组件 | 现状 | 对设计的影响 |
|---|---|---|
| `api/v1/auth.py` | 仅 register / login / me | 新端点加在同一 router（`/api/v1/auth`） |
| `models/user.py` | `email` 唯一索引；`password_hash` **NOT NULL** | 免密建号必须改可空 + 迁移 |
| `core/security.py` | bcrypt 哈希密码；JWT HS256、7 天、**无吊销** | 复用 bcrypt 哈希验证码；JWT 限制记为已知限制 |
| `core/config.py` | pydantic-settings，`DATABASE_URL`/`SECRET_KEY` fail-fast | 新增 SMTP/验证码配置项，默认值安全、凭据缺失时**运行期**503 |
| `api/v1/client_logs.py` | 内存滑动窗口限流（单进程语义） | 复用同一范式；**不改该文件**，新建通用模块 |
| `core/net.py` | 统一信任边界解析客户端 IP | 限流 key 用 `resolve_client_ip`，不可被伪造头绕过 |
| `pyproject.toml` | 无 smtplib 之外的发信依赖 | **零新依赖**（`smtplib`/`email` 标准库） |
| `LoginView/RegisterView + AuthPanel` | 玻璃面板 + el-form | 登录页加双模式切换；注册页加验证码行 |
| `deploy/update.sh` | 已含 `alembic upgrade head` | 迁移随既有更新流程自动应用 |

---

## 3. 复杂度分类与风险

**这是一类问题（安全通道），不是一次性小功能。** 天真的实现（生成 6 位码 → 明文入库 → 存在即通过）会一次性引入一整类经典漏洞：

| 风险 | 后果 | 对策（本设计） |
|---|---|---|
| 邮箱枚举 | 探测已注册邮箱 | 发放接口**统一话术**；`login` 用途对任何邮箱都发（自动建号），`register`/`reset` 对未知邮箱不发但同样话术 |
| 暴力猜码 | 6 位=1e6，可穷举 | **单码最多 5 次尝试**（超限即作废）+ 发放频控（60s 冷却 / 5·h⁻¹·邮箱 / 10·d⁻¹·邮箱 / 20·h⁻¹·IP / 100·h⁻¹ 全局） |
| 明文存码 | 库泄露即全失守 | 码以 **bcrypt 哈希**存储（与密码同待遇） |
| 重放 | 一码多用 | **一次性**：校验成功写 `consumed_at` |
| 用途串用 | 登录码拿去改密 | 码带 `purpose ∈ {login, register, reset}`，跨用途校验直接拒绝 |
| 并发 TOCTOU | 并行请求绕过尝试上限 | 校验时 **`SELECT … FOR UPDATE`** 行锁，在同一事务内递增 `attempts` 并提交 |
| 时序侧信道 | 有码/无码响应时长不同 | 无行时执行**假 bcrypt 比对** |
| 阻塞单 worker | 同步 SMTP 卡死唯一进程 | 端点用 `def`（FastAPI 线程池执行），SMTP 设 10s 超时；发信与入库顺序保证"失败不发码" |
| 改密后旧令牌仍有效 | 盗号者 JWT 存续 | **本轮记为已知限制**（需 `users.token_version`，属下一轮） |

## 4. 根因分析（缺口驱动，非缺陷驱动）

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | 没有邮箱验证码相关能力 | 用户请求；`auth.py` 仅 3 个端点 |
| 直接原因 | 后端缺"发信 + 验证码状态机 + 密码找回"三块能力；`users.password_hash` 不可空导致免密账号无法存在 | `models/user.py:20`、`auth.py` 全量 |
| 根因 | 认证被设计为**单通道（密码）**：没有与"邮箱所有权"解耦的、可复用的验证凭据机制 | 任何新流程（登录/找回/改密/注册验证）都需要同一能力，说明缺的是**通道抽象**而非某个端点 |

**泛化判断**：这是"同一能力被四个流程复用"的结构性问题 → 必须以**验证码状态机服务**（单一实现 + 不可绕过的校验入口）落地，而不是在四个端点各写一遍校验。

## 5. 方案选型对比

| 方案 | 解决根因 | 防复发 | 泛化性 | 长期成本 |
|---|---|---|---|---|
| 快速补丁：每端点各自生成/校验码 | ✗（安全逻辑四处漂移） | ✗ | ✗ | 高（每次改动都要审计四处） |
| **验证码状态机服务 + 统一校验入口**（选用） | ✓ | ✓（不变量集中） | ✓（新增流程=加 purpose） | 低 |
| 无状态 JWT 码（码即签名令牌） | 部分 | ✗（无尝试计数、难单次作废） | △ | 中 |

---

## 6. 设计

### 6.1 数据模型

**`users` 变更**（迁移 `alter column`）：

```python
password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

**新表 `email_codes`**：

```python
class EmailCode(Base):
    __tablename__ = "email_codes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255))                 # 归一化小写
    purpose: Mapped[str] = mapped_column(String(16))                # login | register | reset
    code_hash: Mapped[str] = mapped_column(String(255))             # bcrypt
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    request_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("ix_email_codes_lookup", "email", "purpose", "created_at"),)
```

> 时间列用 `timestamptz` + `datetime.now(timezone.utc)`：过期语义必须无歧义（现有表的裸 `created_at` 从不参与比较，不受影响）。

### 6.2 状态机（单一实现，不可绕过）

```
            发码（新码入库前，将同 (email,purpose) 的 pending 行 expires_at=now 作废）
  ∅ ──────────────────────────────────────────────► PENDING
                                                      │
   校验：latest(email,purpose) FOR UPDATE              │
     ├─ consumed_at 非空 ──────────────► CONSUMED（拒绝）
     ├─ now > expires_at ──────────────► EXPIRED（拒绝，提示重新获取）
     ├─ attempts ≥ 5 ──────────────────► BURNED（拒绝，提示重新获取）
     ├─ bcrypt 不匹配 → attempts+=1 提交 ─► PENDING（拒绝，统一话术）
     └─ 匹配 → consumed_at=now 提交 ─────► CONSUMED（放行）
```

**不变量**
- I1：同一 (email,purpose) 任一时刻最多一行为 PENDING。
- I2：`attempts` 单调不减；错误尝试必须先于响应落库。
- I3：`consumed_at` 一旦写入不可复用（终态）。
- I4：`purpose` 决定可执行的业务动作，跨用途一律拒绝。
- I5：任何对外响应的措辞与"邮箱是否存在/码是否发出"无关（统一话术）。

### 6.3 算法与复杂度

- 生成：`secrets.randbelow(10**6)` 零填充 6 位（均匀、CSPRNG）。O(1)。
- 校验：索引查找 O(log n) + 一次 bcrypt（≈100ms，成本即防御）+ 行锁临界区 O(1)。
- 爆破可行性（关键论证）：单码 5 次尝试 × 每邮箱每日最多 10 码 = 50 次/日；命中概率 ≤ 50/10⁶ = 0.005%/日 ≈ 每 55 年一次——**频控 + 尝试上限共同构成安全边界**，而非依赖码长。
- 限流：每 key 在窗口内的命中时间戳列表，O(k)、k ≤ limit；超限即 429。

### 6.4 配置（`core/config.py` 新增，全部有安全默认值）

```
smtp_host=""  smtp_port=465  smtp_starttls=False  smtp_timeout_seconds=10
smtp_user=""  smtp_password=""            # 163「客户端授权码」，非登录密码
smtp_from=""(默认=smtp_user)  smtp_from_name="途笺 WayNote"
email_code_ttl_minutes=10  email_code_cooldown_seconds=60  email_code_max_attempts=5
email_code_per_email_hour=5  email_code_per_email_day=10
email_code_per_ip_hour=20  email_code_global_hour=100
```

凭据未配置 → 发码接口返回 **503**（明确报错，绝不静默降级）。

### 6.5 API 契约（全部挂 `/api/v1/auth`）

| 方法 | 路径 | 请求 | 成功 | 失败 |
|---|---|---|---|---|
| POST | `/auth/email-code` | `{email, purpose}` | `200 {ok, cooldown_seconds, ttl_minutes, message}`（统一话术） | 429（含剩余秒数）/ 422 / 503 |
| POST | `/auth/login/email-code` | `{email, code}` | `200 TokenOut`（不存在则**建号后**签发） | 400 统一话术 / 429 |
| POST | `/auth/register` | `{email, password, name?, code}`（code 新增必填） | `201 TokenOut` | 400（码无效 → 先于存在性检查）/ 400 邮箱已被注册（已拥码者才可见，不构成枚举）/ 403 注册关闭 |
| POST | `/auth/password/reset` | `{email, code, new_password}` | `200 TokenOut`（重置即登录） | 400 统一话术 |
| POST | `/auth/password/change` | `{new_password, old_password?, code?}`（需登录） | `200 {ok}` | 400 当前密码错误／需验证码 / 401 |
| GET | `/auth/me` | — | `UserOut` 增 `has_password: bool` | 401 |

**密码变更的两条路径**（由账号状态决定，不可混用）：
- `has_password=true` → 必填 `old_password`；
- `has_password=false`（免密建号）→ 必填 `code`（purpose=reset，先请求）。

**顺序性原则**：所有"码校验"都先于"邮箱是否存在"的语义分支；注册端点因此不构成枚举面（能拿到 register 码即已证明邮箱所有权）。

### 6.6 发信模块（`core/mailer.py`，零新依赖）

```
send_email_code(to, code, purpose, ttl_minutes) -> None
  SMTP_SSL(smtp_host, smtp_port, timeout=10) → login(user, 授权码)
  → EmailMessage(subject=「途笺 WayNote 验证码」, text+html 双段, From=发件人姓名<地址>)
异常统一抛 MailerError（端点映射 502）
```

发码端点的**执行顺序（关键）**：①限流 → ②发信（失败即返回，**不落码**）→ ③校验通过才插入 PENDING 行 → ④返回统一话术。保证"用户收不到码时，系统里不存在可用码"。

### 6.7 前端

| 文件 | 变更 |
|---|---|
| `LoginView.vue` | 顶部双模式切换「密码登录 / 验证码登录」；验证码模式=邮箱 + 验证码输入 + 「获取验证码」（60s 倒计时，`from` 服务端 cooldown）+ 登录；密码模式加「忘记密码？」链接；**始终保留** `autocomplete=username/current-password` 与整页跳转（密码管理器友好，见既有 ADR） |
| `ForgotPasswordView.vue`（新） | 两步面板：①邮箱 → 发码 ②验证码+新密码+确认 → 提交 → 自动登录 → `/trips` |
| `RegisterView.vue` | 新增验证码行（邮箱 + 验证码 + 密码 + 昵称），提交前必填 |
| `MeView.vue` | 安全区：「修改密码」（有密码）/「设置密码」（无密码）→ `FormSheet` 表单 |
| `api/auth.ts`、`stores/auth.ts` | 新增 `sendEmailCode / loginWithCode / resetPassword / changePassword`；`User.has_password` |

### 6.8 防复发机制（四层）

1. **不变量集中**：状态机与限流只在 `core/email_code.py` 实现，端点不得自行比对码。
2. **回归测试**：用途隔离、单次作废、尝试 burn、并发计数、统一话术一致性各有一条断言（见 §8）。
3. **守卫测试**：断言所有发码响应体中**不含验证码本身**（防调试期把码带出去）。
4. **文档沉淀**：本 ADR + `.env.example` 的 SMTP 注释（含 163 授权码获取步骤）。

### 6.9 泛化边界与反例

| 维度 | 说明 |
|---|---|
| 适用 | 单实例部署（内存限流）、6 位数字码、SMTP 通道、purpose 集合固定为三类 |
| 不适用 | 多进程/多副本（需 Redis 或表级限流）；短信/多通道（需通道抽象）；需要会话吊销（需 `token_version`） |
| 反例 1 | 邮件进垃圾箱 → 用户重复点「获取」：冷却期返回剩余秒数，且新码会作废旧码，用户最终持有最新码 |
| 反例 2 | 服务器→163 网络抖动：返回 502 且**无可用码**，用户可立即重试（不计入"码已发"） |
| 反例 3 | 163 对新账号限发/日配额：接口如实报错，不静默成功（运维可见） |
| 反例 4 | 并发重复提交同一正确码：行锁 + `consumed_at` 保证只有一次成功签发 |

### 6.10 已知限制与演进

- JWT 无吊销：改密/重置后旧令牌在 7 天内仍有效（**记录**；下一轮加 `users.token_version` 并在签发时校验）。
- 限流内存态：重启清零、不跨进程（与 `client_logs` 同一已记录边界）。
- 免密账号 `name` 默认取邮箱 @ 前缀（≤50 字符）。
- 演进路径：`core/ratelimit.py` 可回灌给 `client_logs`；mailer 可换成 HTTP 邮件推送 API（163 → 阿里云/腾讯云 SES）。

---

## 7. 迁移与部署

1. 手写 alembic 迁移：`users.password_hash` 改可空 + 建 `email_codes` 表与索引（additive & nullable，线上安全）。
2. `backend/.env` 增 SMTP 段（163 预填 host/port，账号与授权码留空由用户填）；`.env.example` 同步。
3. 无新增依赖 → 服务器 `deploy/update.sh` 一次完成（uv sync 会核对、迁移自动跑、服务重启 + 健康检查）。
4. 上线后**真实发信验证**：请求一次 login 码 → 查 `backend/logs` 无错误 → 用户查收 163 邮件。

---

## 8. 测试计划（Phase 4 落地，pytest + monkeypatch mailer）

| ID | 类型 | 场景 | 期望 | 覆盖根因/防复发 |
|---|---|---|---|---|
| T1 | 正常 | login 码 → 登录（新邮箱） | 201/200，自动建号，`has_password=false` | 自动建号 + 免密 |
| T2 | 正常 | 已注册邮箱 login 码 → 登录 | 200，不重复建号 | 幂等 |
| T3 | 错误 | 错码 | 400 统一话术；`attempts+1` 已落库 | I2 |
| T4 | 边界 | 连错 5 次后正确码 | 400（BURNED） | 尝试上限 |
| T5 | 边界 | 过期码（冻结时间） | 400 | TTL |
| T6 | 边界 | 60s 内重复发码 | 429 且含剩余秒数 | 冷却 |
| T7 | 边界 | 同邮箱第 6 次/小时 | 429 | 每小时配额 |
| T8 | 边界 | 同 IP 第 21 次/小时 | 429 | IP 配额（不可伪造头绕过） |
| T9 | 回归 | login 码用于 reset | 400 | **用途隔离（I4）** |
| T10 | 回归 | 同一码用两次 | 第二次 400 | **单次作废（I3）** |
| T11 | 回归 | 发码响应体含码 | 断言失败（不得含码） | 守卫测试 |
| T12 | 正常 | 注册：register 码 + 密码 | 201，密码可登录 | 注册验证 |
| T13 | 错误 | 注册：无码 / 错码 | 422 / 400，且**不泄露邮箱是否存在** | 顺序性原则 |
| T14 | 错误 | 注册：邮箱已存在（持有效码） | 400 邮箱已被注册 | 语义正确 |
| T15 | 正常 | 重置：reset 码 + 新密码 | 200，新密码可登录、旧密码失败 | 找回闭环 |
| T16 | 错误 | 重置：未注册邮箱 | 200 统一话术 + **未发信** | 防枚举 |
| T17 | 正常 | 改密：有密码（旧密码正确）；无密码（reset 码） | 200 / 200 且码被消费 | 两条路径 |
| T18 | 错误 | 改密：旧密码错 / 免密账号缺码 | 400 / 400 | 状态判定 |
| T19 | 错误 | SMTP 未配置 | 503 | 明确失败 |
| T20 | 错误 | SMTP 抛错 | 502 且**库中无可用码** | 发信顺序原则 |
| T21 | 回归 | 既有密码登录/注册测试 | 全绿（注册用例补 code） | 不破坏既有契约 |

---

## 9. Checkpoint

- 待用户确认后进入 Phase 3 实现。
- 实现顺序：`config` → `models/migration` → `core/ratelimit` → `core/mailer` → `core/email_code` → `api/v1/auth` → 前端（api/store → 三个视图）→ 测试 → 本地联调（真发信）→ 服务器（update.sh）→ 线上验证。

---

## 10. Phase 5 交付记录（2026-10-10）

### 10.1 实现清单

| 层 | 文件 | 说明 |
|---|---|---|
| 配置 | `backend/app/core/config.py` | SMTP + 验证码策略（全部有安全默认值）+ `smtp_configured` / `mail_from` |
| 模型 | `backend/app/models/user.py` | `password_hash` 可空 + `has_password` 属性 |
| 模型 | `backend/app/models/email_code.py`（新） | 验证码表（哈希、attempts、consumed_at、purpose、timestamptz） |
| 迁移 | `backend/alembic/versions/9d1f4c7b2a58_*.py`（新） | 可空 + 建表 + 复合索引；downgrade 注明免密账号会导致回滚失败 |
| 基础 | `backend/app/core/ratelimit.py`（新） | 通用滑动窗口（窗口按调用传入） |
| 基础 | `backend/app/core/mailer.py`（新） | smtplib 发信（465 SSL / 587 STARTTLS）；**永不记录验证码** |
| 服务 | `backend/app/core/email_code.py`（新） | 状态机唯一实现 + 四层频控 + FOR UPDATE + 时序对齐 |
| 接口 | `backend/app/api/v1/auth.py` | 5 个新/改端点（见 §6.5） |
| 契约 | `backend/app/schemas/user.py` | `code` 字段、`EmailCode*`、`PasswordReset/Change`、`has_password` |
| 前端 | `api/auth.ts`、`stores/auth.ts`、`composables/useCountdown.ts`（新） | 四个新 API、两个新 store 动作、倒计时 |
| 前端 | `LoginView.vue`（双模式）、`ForgotPasswordView.vue`（新）、`RegisterView.vue`（+验证码）、`MeView.vue`（设置/修改密码）、`router/index.ts`（+`/forgot`） | UI 全部沿用既有玻璃面板与错误提示规范 |
| 文档 | `backend/.env.example`、`deploy/DEPLOY.md` | 163 授权码获取步骤；503 排障行 |

### 10.2 与设计的偏差（均已验证）

1. **邮箱查找改为大小写不敏感**：`func.lower(User.email) == 归一化输入`。原因：历史注册数据未归一化，直接比对会让大写邮箱账号登录失败。代价：`users.email` 索引不再被该查询命中（用户量级可忽略），已在代码注释与本表记录。
2. **登录失败话术**：在统一话术（不泄露账号是否存在）前提下补充可行动指引「若你从未设置过密码，请用『验证码登录』」——对所有人一致，不构成枚举差异。
3. **测试数量 21 → 25**：额外补了「哈希列可空（迁移前置）」「索引存在」「密码登录回归」「免密账号密码登录话术」4 条。
4. **本地验证环境**：本机开发库是 Docker 容器 `waynote-pg`（已停止 42h），已启动它跑迁移与测试；测试全程事务回滚，不落数据。

### 10.3 验证结果

- `uv run pytest -q` → **51 passed**（原 26 + 新增 25），含 T1-T21 全部场景
- `uv run ruff check backend` → All checks passed
- 前端：`type-check` / `oxlint` / `eslint` / `check:tokens`（102 令牌）/ `build` → 全绿
- 真实进程冒烟（uvicorn 8021）：未配置 SMTP → **503**；非法 purpose / 非法码格式 → **422**；未知邮箱密码登录 → 400 统一话术；演示账号 `/me` → `has_password: true`
- 迁移：本地库 `51c4b56128a3 → 9d1f4c7b2a58 (head)`

### 10.4 收尾（2026-10-10）

- ✅ **163 授权码已配置**（本地与服务器 `backend/.env`），真实发信验证通过：
  `/auth/email-code` → 200；日志 `auth.email_code.delivered`；163 已接收；DB 落码（pending/valid、attempts=0）
- ✅ **用户实机试用「验证码登录」通过**（免密建号并进入 `/trips`）——本 ADR 的主路径闭环
- 明确不做：全站默认按钮（落地页「我已有账号」、弹窗「取消」）**保留** element-plus 的 1px 描边
  —— 它们不承担"必做步骤"语义，不构成误导；取码按钮已单独修好（见 §10.5）
- 已知遗留（见 §6.10）：JWT 无吊销；限流是单进程内存态

### 10.5 验收反馈修正（2026-10-10 第二轮）

用户验收提出四点，其中两点确为缺口：

| 反馈 | 判定 | 处置 |
|---|---|---|
| 注册页未体现必填/可选 | **缺口**（全站此前没有必填约定，"可选"只写在标签里） | 邮箱/验证码/密码加 `required`（红点标记）；昵称保持「（可选）」；线上实测 `is-required` 正确 |
| 注册页未体现"验证码可直接登录" | **缺口** | 加提示「不想设密码？可以直接用「验证码登录」…」并**深链** `/login?mode=code`（登录页新增 mode 解析，直达免密模式）；线上实测跳转后模式=验证码登录 |
| 有没有输入验证 | 有，但**发现两处服务端缺口** | 前端：邮箱非空、码 `^\d{6}$`、密码 ≥6 且两次一致、昵称 maxlength=50；后端（权威）：`EmailStr`、`code` 6 位数字 pattern、`purpose` Literal、`new_password` 6-72、**新增** `UserRegister.password` 6-72 与 `name` ≤50（此前缺失，超长昵称会撞 DB String(50) 报 409） |
| 防攻击策略 | 已有（见 §3/§6），需给证据 | 线上实测：同一邮箱连续发码 → 第 2、3 次 **429「请 60 秒后再试」**；非法码 → 422；单码尝试上限/用途隔离/单次作废/发信失败不留码由测试 T3/T4/T9/T10/T20 覆盖 |

新增测试：T22（服务端校验 + **校验失败不消耗验证码**，证明校验在业务逻辑之前）。全套 52 passed。
