# ADR-20260929：行程删除级联修复、密钥配置外置与回归测试基建

- 状态：待确认（Phase 2.5 CHECKPOINT）
- 日期：2026-09-29
- 范围：P0-1 删除级联、P0-2 配置/密钥治理、P1 垃圾导入清理、回归测试基建
- 不包含（用户明确不做/本次不做）：Git 提交、日期类型迁移、docker-compose、Nginx/systemd 部署脚本、Note/Memo 功能

---

## 1. 背景与问题陈述

Waynote 后端（FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL 16）已实现用户、行程、天、地点四层 CRUD。
评审中发现两类问题并已在本地真实数据库验证：

1. **删除含子数据的行程会 500**（P0-1，已复现）。
2. **JWT 密钥与数据库口令写在将被 Git 跟踪的文件里**（P0-2，仓库尚无任何 commit，修复成本为零）。

需求复述：在不改变现有 API 契约与数据库结构的前提下，修复这两类问题，并建立防复发机制（回归测试 + 配置单一入口）。

隐式约束：

- 不能改变前端已依赖的 HTTP 行为（204/404/错误码语义保持）。
- 不做数据库结构变更（`ondelete` 约束已存在于迁移）。
- 不能破坏现有本地数据与正在运行的开发环境。
- 仓库未提交，不执行任何 `git add/commit`。

---

## 2. Phase 1：分析

### 2.1 现状评估

- 模型层用 `backref` 隐式建立关系：`Trip.days`、`Trip.places`、`TripDay.places`、`User.trips`。
- 迁移层已正确声明外键行为：`trips.user_id ON DELETE CASCADE`、`trip_days.trip_id ON DELETE CASCADE`、`places.trip_id ON DELETE CASCADE`、`places.day_id ON DELETE SET NULL`。
- ORM 层未声明任何 `cascade` / `passive_deletes`，与迁移层语义脱节。
- 后端无任何测试；无 linter（ruff 等）；存在 IDE 误导入的无关依赖。
- `SECRET_KEY` 硬编码在 `backend/app/core/security.py:8`；`backend/.env`、`backend/alembic.ini` 含明文口令；根 `.gitignore` 未忽略 `.env`、`.idea/`。

### 2.2 复杂度分类

- P0-1：单点逻辑不复杂，但属于**一类问题**（父-子关系级联策略与数据库语义一致性），需要按“类”修，而不是按“这一个接口”修。
- P0-2：结构性配置分离问题，属于“配置单一入口 + 忽略规则”这一类。
- 测试基建：首次引入，必须选择能真实触发数据库级联的执行路径（事务内 flush + 回滚），而不是伪造 ORM 行为。

### 2.3 根因分析（P0-1）

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | `DELETE /api/v1/trips/{id}` 在行程含天/地点时返回 500 | 实测：`RESULT: DELETE FAILED -> IntegrityError` |
| 直接原因 | 提交前 ORM 发出 `UPDATE trip_days SET trip_id=NULL ...`，违反 NOT NULL 约束 | 实测输出中的 SQL 与 `NotNullViolation` 明细 |
| 根因 | 外键的 DB 级 `ondelete` 语义没有对应的 ORM 级关系配置（缺 `cascade`/`passive_deletes`）；两个配置层互不联动，且无测试守卫 | `trip.py:13` 有 `ondelete="CASCADE"`；关系定义处无任何 cascade 参数 |

5 Whys：

1. 为什么 500？→ 提交时抛 `NotNullViolation`。
2. 为什么违反非空？→ ORM 把子行 `trip_id` 置 NULL。
3. 为什么 ORM 置 NULL 而不删子行？→ 关系默认级联不含 delete，默认删除行为是“把子对象外键置 NULL”。
4. 为什么 DB 的 `ON DELETE CASCADE` 没兜住？→ ORM 在发出 `DELETE trips` 之前先处理了子集合（无 `passive_deletes`），子行 UPDATE 失败，DELETE 根本没执行到数据库。
5. 为什么没早发现？→ 没有覆盖“父对象带子数据删除”的测试；手工测试只用过空行程。→ 根因上升为：**级联语义只配置了一半，且缺守卫**。

影响面：`Trip→TripDay`、`Trip→Place`（两者 FK 均 NOT NULL）必然触发；`User→Trip` 同属一类（当前无删用户接口，属于潜伏同类问题）；`TripDay→Place` 属于 SET NULL 语义，是**反例**，不能套用同一策略。

### 2.4 泛化判断（P0-1）

| 问题类型 | 一次性/一类 | 代表输入 | 反例 | 非适用场景 |
|---|---|---|---|---|
| NOT NULL 子 FK + DB CASCADE 时，ORM 级联缺失导致删除父对象失败 | 一类问题 | 删除含 N 天 M 地点的行程 | `places.day_id`：可空 + SET NULL，期望“地点保留、归属置空” | 子 FK 可空且业务要求置空；或 DB 无 FK 约束（如 SQLite 未开 PRAGMA）的测试环境 |

### 2.5 快速补丁 vs. 设计修复

| 方案 | 解决根因？ | 防复发？ | 泛化性 | 长期成本 |
|---|---|---|---|---|
| A1 在 `delete_trip` 里手动先删子表 | 否（只修一个端点） | 否 | 差 | 每个删除路径都要记得写；未来分享/清理任务必踩 |
| A2 删除 DB 约束、纯靠 ORM | 否（方向反了） | 否 | 差 | 绕过 ORM 的写入（迁移/运维 SQL/其他服务）产生孤儿数据 |
| A3 `cascade` 不加 `passive_deletes` | 部分 | 弱 | 中 | 每个子集合先加载再删，N+1 往返；语义仍与 DB 重复实现 |
| A4 捕获 IntegrityError 返回 409 | 否（掩盖数据完整性 Bug） | 否 | 无 | 用户依然删不掉行程 |

结论：采用「**显式关系 + ORM 级联策略与 DB `ondelete` 一一对齐 + 回归测试守卫**」。

### 2.6 根因分析（P0-2）

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | 密钥/口令将随 Git 进入版本历史 | 仓库无提交；`.env` 未被忽略；`security.py`/`alembic.ini` 明文 |
| 直接原因 | 代码中硬编码密钥；配置分别存在于 `.env`、`alembic.ini`、源码三处 | `config.py`、`security.py`、`alembic.ini` |
| 根因 | 配置没有单一入口与忽略规则；“代码仓库”与“环境配置”边界缺失 | 三处配置互不知晓，任意新增项都会重复犯错 |

泛化边界：适用于所有“本地/生产环境不同的配置项”（密钥、连接串、未来 COS/地图的 AppKey）。
反例/非适用：前端 `vite.config.ts` 的 dev proxy 目标属于代码级常量，不在本次范围。

一次性的快速补丁（只把当前 key 移走）无法防复发，因为 alembic.ini 与 .env 的重复来源仍在；因此设计为：
**`Settings` 是唯一配置入口，`.env` 是唯一本地来源，其余文件不得出现真实值。**

---

## 3. Phase 2：设计

### 3.1 关系级联策略（P0-1）

数据模型变更（仅关系配置，无表结构变更）：

```python
# user.py
class User(Base):
    trips: Mapped[list["Trip"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

# trip.py
class Trip(Base):
    user: Mapped["User"] = relationship(back_populates="trips")
    days: Mapped[list["TripDay"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan", passive_deletes=True,
        order_by="TripDay.day_index",
    )
    places: Mapped[list["Place"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan", passive_deletes=True
    )

# trip_day.py
class TripDay(Base):
    trip: Mapped["Trip"] = relationship(back_populates="days")
    places: Mapped[list["Place"]] = relationship(back_populates="day")  # SET NULL 语义：保持默认（由 ORM 置空）

# place.py
class Place(Base):
    trip: Mapped["Trip"] = relationship(back_populates="places")
    day: Mapped["TripDay | None"] = relationship(back_populates="places")
```

**不变量**（写入 ADR 与代码注释）：

1. 子 FK 为 NOT NULL 且 DB `ondelete=CASCADE` → ORM 关系必须 `cascade="all, delete-orphan", passive_deletes=True`。
2. 子 FK 可空且 DB `ondelete=SET NULL` → ORM 关系不得设置 delete 级联；允许默认由 ORM 置空。
3. `passive_deletes=True` 的成立前提：数据库外键约束真实存在且被启用（PostgreSQL 满足）。

前置条件：迁移已建立 FK 约束（现状满足，无需新迁移）。
后置条件：删除父对象只产生 1 条 `DELETE`，子行由数据库级联清理（子 FK NOT NULL）或置空（SET NULL）。
异常契约：API 层行为不变（204/404），不再出现 500。
复杂度：级联删除由数据库单语句完成，时间 O(1) 次往返；若不使用 `passive_deletes`，往返数 O(k)（k=子集合大小）。

替代方案与被否决理由见 §4；反例与边界见 §2.4 与 §5.3。

### 3.2 配置单一入口（P0-2）

`app/core/config.py`：

```python
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",  # 固定指向 backend/.env，不受 CWD 影响
        extra="ignore",
    )

    database_url: str          # 必填：缺失即启动失败（fail-fast）
    secret_key: str            # 必填：不再有默认值，杜绝已知默认密钥
    app_name: str = "Waynote API"


settings = Settings()
```

- `security.py`：删除硬编码 `SECRET_KEY`，改为 `settings.secret_key`。
- `alembic.ini`：`sqlalchemy.url` 改为占位符 + 注释；`env.py` 直接 `create_engine(settings.database_url)`（online）与 `context.configure(url=settings.database_url, ...)`（offline），彻底去掉 ini 中的连接串，单一来源。
- `.env`（本地，gitignored）：`DATABASE_URL` 保留，新增 `SECRET_KEY`（本次生成全新随机值，旧值作废 → 现有登录态失效，需重新登录）。
- 新增 `backend/.env.example`：占位值 + 生成密钥的命令示例。
- 根 `.gitignore` 增补：`.env`、`**/.env`、`!.env.example`、`.idea/`、`.pytest_cache/`、`.ruff_cache/`。

### 3.3 垃圾导入清理（P1）

| 文件 | 处理 | 风险说明 |
|---|---|---|
| `app/db/session.py` | 删除 `from idlelib import autocomplete` | 精简 Python 环境无 idlelib，生产启动即 ImportError |
| `app/api/v1/auth.py` | 删除 `from sqlalchemy.testing import ...`、未用的 `status` | 引用测试库，纯污染 |
| `app/main.py` | 删除未用的 `auth_router` 导入 | 无 |
| `alembic/env.py` | 只 `from app.models import Base`，去掉重复导入 | 无 |

防复发：引入 `ruff`（dev 依赖，`select=["F"]`），一个命令即可拦截 F401 类问题。不引入 CI（超范围）。

### 3.4 回归测试设计（防复发核心）

**执行路径选择**：需求要求“测试必须真实触发数据库级联”。采用「连接级事务 + 回滚」模式：

```python
# conftest.py 核心
connection = engine.connect()
transaction = connection.begin()
session = Session(bind=connection)
# FastAPI get_db 依赖覆盖为同一个 session
yield client, connection
session.close(); transaction.rollback(); connection.close()
```

- 级联删除在 `flush()` 时由 PostgreSQL 真实执行；测试结束整体回滚 → 不污染开发库。
- 断言使用**原生 SQL 计数**（绕过 ORM identity map），避免 `passive_deletes` 下会话内状态导致的假阳性/假阴性。
- 依赖：`pytest`、`httpx`（TestClient 需要）、`ruff`（dev 依赖，`uv add --dev`）。
- 数据库：默认复用 `DATABASE_URL`（本地开发库，事务回滚）；可选 `TEST_DATABASE_URL` 覆盖。

测试矩阵（≥5）：

| ID | 类型 | 场景 | 期望结果 | 覆盖 |
|---|---|---|---|---|
| T1 | 回归（旧代码必失败） | 删除含 1 天 + 1 地点的行程 | 204；raw SQL 三表 0 行 | 根因 |
| T2 | Happy | 删除空行程 | 204；其他行程不受影响 | 泛化 |
| T3 | 反例守卫 | 删除某一天（地点归属该天） | 天删除；**地点保留且 `day_id IS NULL`** | 防止错套 delete-orphan |
| T4 | 边界 | A、B 两用户各有行程；删 A 的 | B 的行程/天/地点计数不变 | 隔离不变量 |
| T5 | 安全 | B 请求删除 A 的行程 | 404；A 的数据完好 | 权限 |
| T6 | 泛化 | 行程含 3 天、5 地点（含 1 个 `day_id=NULL`） | 全部清理，无孤儿行（JOIN 计数为 0） | 一类问题 |
| T7 | 配置 fail-fast | 清空环境变量且 `_env_file=None` 实例化 Settings | 抛 ValidationError | P0-2 根因 |
| T8 | 冒烟（手动命令） | `alembic current`、`python -c "import app.main"` | 正常输出 | 集成不破 |

### 3.5 根因→方案映射

| 根因 | 证据 | 针对性方案 | 防复发 | 验证 |
|---|---|---|---|---|
| ORM 级联策略与 DB `ondelete` 脱节 | 实测 IntegrityError + SQL | 四个关系显式配置并按不变量对齐 | T1/T3/T4/T6 + 不变量写入代码注释与 ADR | pytest 全绿；手动 probe 复跑 |
| 配置三处分散、含硬编码密钥 | 三个文件 | Settings 单一入口 + ini 去连接串 + 忽略规则 | T7 + `.env.example` + gitignore | T7 + `alembic current` |
| 无 lint 导致垃圾导入 | idlelib/sqlalchemy.testing | 清理 + ruff(F) | ruff 可重复执行 | `uv run ruff check` |

### 3.6 交付物清单（Phase 3 预览）

修改：`app/models/{user,trip,trip_day,place}.py`、`app/core/{config,security}.py`、`app/db/session.py`、`app/api/v1/auth.py`、`app/main.py`、`alembic/env.py`、`alembic.ini`、`.env`、`.gitignore`、`pyproject.toml`（dev 依赖与工具配置）。
新增：`backend/.env.example`、`backend/tests/conftest.py`、`backend/tests/test_trip_cascade.py`、`backend/tests/test_config.py`。
不动：表结构与迁移文件、前端、API 契约、`uv.lock` 由 uv 自动更新。

---

## 4. 被否决的替代方案

| 方案 | 否决理由 |
|---|---|
| 端点内手动删除子表（A1） | 症状级补丁，只覆盖一个调用路径，未来必然复发 |
| 去掉 DB 约束（A2） | 削弱数据完整性最后防线，无约束环境产生孤儿数据 |
| 只加 cascade 不加 passive_deletes（A3） | 可行但每次删除产生 O(k) 次加载/更新；且掩盖“与 DB 语义重复实现”的问题 |
| 捕获 IntegrityError 转 409（A4） | 把数据完整性缺陷伪装成业务错误，用户依然不能删除 |
| `SECRET_KEY` 保留但设默认值 | 默认密钥等价于硬编码；必须 fail-fast |
| 引入 python-dotenv 手动加载 | pydantic-settings 已存在，双机制增加认知负担 |
| 仅 gitignore alembic.ini 而不去连接串 | 配置继续双源，漂移风险仍在 |

---

## 5. 测试计划与验证步骤

### 5.1 自动化

```
uv run pytest -q                     # T1–T7
uv run ruff check backend            # F 类规则
```

### 5.2 手动/集成

```
cd backend && uv run alembic current            # 迁移链不受影响
uv run python -c "import app.main"              # 导入无副作用
# 复跑本次评审的 probe 脚本：含子数据 → 删除成功，计数归零
```

### 5.3 泛化边界与已知反例（写入 ADR 供后续维护者）

- 适用：任何“子 FK NOT NULL + DB CASCADE”的新关系（例如未来 Note 属于 Trip 时）。
- 不适用：`TripDay→Place`（可空 + SET NULL），业务语义是“地点保留”。T3 即为该反例守卫。
- 前提失效条件：若未来迁移移除 FK 约束或改成 RESTRICT，`passive_deletes=True` 会静默产生孤儿/报错，需同步修改本 ADR 与测试。
- 已知限制：测试使用开发库连接做事务回滚（无独立测试库）；CI 未引入。

---

## 6. 最终结果（Phase 5）

- 状态：已完成（**未执行任何 Git 提交**，按要求仓库操作留给用户）。
- 实际变更：
  - 模型层：4 个关系全部显式化（`back_populates`），`User.trips`/`Trip.days`/`Trip.places` 配 `delete-orphan + passive_deletes=True`；`TripDay.places` 保持默认置空（不变量 + 反例注释已写入代码）。
  - 配置层：`Settings` 成为唯一入口（`database_url`/`secret_key` 必填 fail-fast；`env_file` 绝对路径指向 `backend/.env`）；`alembic.ini` 去除连接串，`env.py` 只读 settings；`.env` 新增随机 `SECRET_KEY`（旧密钥作废）；新增 `.env.example`；`.gitignore` 忽略 `.env`/`.idea`/缓存。
  - 清理：移除 `idlelib`、`sqlalchemy.testing`、未用导入；`app/models/__init__.py` 增加 `__all__`。
  - 测试基建：新增 `backend/tests/`（conftest + helpers + 8 个用例），dev 依赖 pytest/httpx/ruff，`pyproject.toml` 配置 pytest 与 ruff(F)。
- 测试结果：
  - `uv run pytest -q` → **8 passed**（T1 即旧行为回归，修复前已用独立 probe 复现 IntegrityError）。
  - `uv run ruff check backend` → All checks passed。
  - `uv run alembic current` → `51c4b56128a3 (head)`；`alembic check` → No new upgrade operations detected（模型与库无漂移）。
  - 独立 probe 复跑 → `RESULT: DELETE OK (cascade works)`，计数归零；`import app.main` OK。
- 偏差与经验（重要）：
  1. 首次在 `alembic.ini` 写入中文注释导致 Windows 下 configparser 以 GBK 解码 UTF-8 失败、`alembic current` 崩溃；已改回纯 ASCII 注释。**规则：`.ini` 等由 configparser 读取的文件在 Windows 上必须保持 ASCII。**
  2. venv 中 bcrypt 实际为 5.0.0，与 pyproject 锁定 4.0.1 不一致且残留 dist-info，uv 每次运行都会重装；已 `uv sync` 对齐。
  3. `.env` 将 `SECRET_KEY` 轮换 → 所有旧登录态失效，需重新登录一次（本地开发无影响）。
  4. 为让 `uv` 更新环境，曾临时停止用户本地的 uvicorn 开发服务器，验证完成后已重新拉起并通过 `/api/v1/health` 检查。
- 遗留（未做，保持最小范围）：前端未改动；`main.py` PyCharm 样板与空 README 未处理；浏览器端 Token 仅 7 天有效，无刷新机制。
