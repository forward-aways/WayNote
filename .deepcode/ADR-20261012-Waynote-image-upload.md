# ADR-20261012：图片上传（行程封面 + 地点照片）· 本地存储先行

- 状态：待确认（Phase 1/2 完成，等待用户 ACK 后进入 Phase 3）
- 日期：2026-10-12
- 关联：ADR-20261012-Waynote-backup.md（同批交付，备份覆盖 media）、ADR-20260929-Waynote-cascade-and-secrets.md（级联清理）、ADR-20260929-Waynote-deployment-systemd.md（nginx/端口纪律）

---

## 1. 需求与背景（Phase 1）

用户需求：给产品加图片能力，但**暂时没有腾讯云 COS**，先落到服务器本地文件夹；产出的图片将来要能无痛迁到 COS。
用户已抉择：
- v1 范围：**行程封面 + 地点照片**（每处单图，不做多图相册）
- 行程列表卡：**顶部封面条**（有封面显示、无封面保持现状）
- 同批把**每日自动备份（含图片）**补上（→ 独立 ADR-20261012-Waynote-backup.md）

隐式约束：
- 2C2G 单机：磁盘有限（实测 26G 空闲 ≈ 约 5 万张压缩图）；图片必须压缩+有上限+有频控。
- 图片不能进 git 工作区（update.sh 以 `git status` 判定可更新性）。
- 备案合规：本站是中国大陆备案站点，UGC 图片需要"可追溯+可删"（本设计提供"本人归属校验 + 实体删除联动清理"的最小闭环；内容审核列为已知限制）。
- 视觉纪律：不使用新色值/新令牌（check:tokens 守卫）。

## 2. 现状评估（缺什么）

| 层 | 现状 | 差距 |
|---|---|---|
| 数据 | `trips.cover String(500)` 字段已存在但**无任何写入入口**（TripUpdate 无 cover）；`places` 无图片字段 | 缺 place 字段；缺写入路径 |
| 接口 | 无上传端点；`python-multipart` 已在依赖 ✓ | 缺 `POST /uploads/images`；缺 Pillow |
| 静态服务 | nginx `client_max_body_size 2m`；无 `/media/` location；dev 无 `/media` 代理 | 上传会 413；图片无直供通道 |
| 前端 | 无图片组件；表单无图片选择 | 缺压缩工具/上传 API/三处展示 |
| 运维 | **无任何备份**（见备份 ADR） | 图片入本地盘前必须先有备份 |

## 3. 根因/差距分析

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | 产品"看不见旅行"（README 待办第 3 项：图片上传） | README 功能状态 |
| 直接原因 | 没有"文件存储"这一层：无存储抽象、无上传管线、无静态直供 | 上表 |
| 根因 | 缺少**内容与位置的分离**：一旦把绝对路径/URL 写进数据库，域名、存储后端、CDN 任一变化都会让存量引用失效 | 设计决策 §4.2 |

## 4. 设计（Phase 2）

### 4.1 存储抽象（迁移缝）

`backend/app/core/storage.py`（本地实现；契约即为将来 COS 实现的接口）：

```python
def build_key(user_id: int, now: datetime) -> str           # "{uid}/{YYYY}/{MM}/{uuid32hex}.jpg"
def validate_key(key: str, user_id: int) -> str             # 返回规范化 key；非法/非本人 → MediaKeyInvalid
def save_image(key: str, data: bytes, thumb: bytes) -> None # 原子写（tmp + os.replace），mkdir -p
def delete_image(key: str) -> None                          # 主图+缩略图；不存在不报错
def path_of(key: str) -> Path                               # 校验后拼 media_root 内绝对路径（防穿越）
def thumb_key(key: str) -> str                              # {stem}.thumb.jpg（约定推导，不入库）
def public_url(key: str) -> str                             # f"{settings.media_url_prefix}/{key}"（将来换 CDN 只改这里）
```

**不变量 I1**：`media_root` 之外的任何路径都不可写/不可读（`validate_key` 正则 + `path_of` 的 `resolve().is_relative_to(root)` 双重防护）
**不变量 I2**：缩略图由 key 推导（同目录、`.thumb.jpg`），数据库只存主图 key，永不存两个 key
**不变量 I3**：key 第一段 = 用户 id ⇒ 归属校验天然成立（PATCH 引用他人 key → 400）

### 4.2 为什么 key 而不存 URL（根因对应）

- 存 URL：换域名/换存储/CDN 全部失效 ✗
- 存 key：域名由前端 `mediaUrl()` 拼、存储由 `storage.public_url()` 决定 ⇒ **迁移 COS = 换实现 + 搬文件 + 改前缀，数据库零改动** ✓

### 4.3 数据层

```sql
-- 新迁移（down_revision = c4a7d92b6e15）
ALTER TABLE places ADD COLUMN photo VARCHAR(500) NULL;   -- 相对 key；NULL=无照片
-- trips.cover 复用，无需迁移
```
- `TripUpdate` 增加 `cover: str | None`；`PlaceUpdate` 增加 `photo: str | None`；`PlaceOut` 增加 `photo: str | None`
- 语义：传合法 key=设置（并删旧文件）；传 `null`=清除（并删文件）；**不传=不改**（沿用 exclude_unset 模式）

### 4.4 上传管线（唯一入口）

`POST /api/v1/uploads/images`（需登录；multipart `file`）

| 阶段 | 规则 | 失败 |
|---|---|---|
| 体积 | ≤ `media_max_bytes`（默认 4MB） | 400「图片过大（≤4MB）」 |
| 解码 | `Image.open + verify()` → 重开（Pillow 反解压炸弹：`MAX_IMAGE_PIXELS` 超限抛错） | 400「图片已损坏或无法识别」 |
| 格式 | 仅 Pillow 可解且 ∈ {JPEG,PNG,WebP,BMP,TIFF,GIF 首帧}（HEIC 由前端转码，服务端明确拒绝） | 400「不支持的文件类型（请用 JPG/PNG/WebP）」 |
| 规范化 | `exif_transpose`（先纠正方向）→ 等比缩放至最长边 ≤2000 → 合成白底 RGB → JPEG(quality=85, progressive, optimize)（**EXIF 全丢**，含 GPS 隐私） | — |
| 缩略图 | 最长边 ≤640 → JPEG(quality=80) | — |
| 落盘 | `{uid}/{Y}/{M}/{uuid}.jpg` + `.thumb.jpg`（原子写） | 500 |
| 频控 | `upload:user:{id}` 滑动窗口 **100 次/日**（复用 core/ratelimit.py） | 429 |

响应：`201 {"key": "...", "width": 1600, "height": 1200, "bytes": 312004}`
不变量 **I4**：产物统一 JPEG、最长边 ≤ `media_max_edge`、无 EXIF。
复杂度：单张 O(P)（P=像素数，解码+重采样），P ≤ 2000×2000=4M 像素量级；内存峰值 ≈ 单帧 + 重采样缓冲（< 50MB @2000px）；无并发共享状态。

### 4.5 清理策略（尽力而为，正确性无关）

- 替换/清空封面、照片 → **DB 提交成功之后**删旧文件（提交失败绝不能先删）
- 删除 trip/place → 提交前收集 keys（trip.cover + 其 places.photo）→ 提交后批量删
- 已知残留：上传后未被引用的孤儿（用户选了图又放弃保存）——量级小，记入已知限制；后续可加 TTL 清理任务

### 4.6 静态直供

| 环境 | 通道 |
|---|---|
| 生产 | nginx `location /media/ { alias <media_root>/; expires 30d; add_header Cache-Control "public, immutable"; add_header X-Content-Type-Options nosniff; access_log off; }`（**两个 server 块都要加**）；`client_max_body_size 6m` |
| 开发 | backend `app.mount("/media", StaticFiles(..., check_dir=False))` + vite `server.proxy['/media'] → 127.0.0.1:8000` |
| 隐私模型 | uuid 随机名 = "能力 URL"（不可枚举）；不鉴权直供（nginx 性能）；将来需要严格时可换签名 URL（storage.public_url 一个函数的事） |

### 4.7 前端设计

- `utils/media.ts`：`mediaUrl(key)` / `thumbUrl(key)`（后者按 I2 推导）
- `utils/imageCompress.ts`：canvas 压缩（≤2000px、q0.85）——顺带解决 **iPhone HEIC**（浏览器解码后统转 JPEG）与弱网大图；解码失败时原样上交由服务端裁决
- `api/uploads.ts`：`uploadImage(file)`（FormData；继承 axios 拦截器/401 处理）
- UI：
  1. 编辑行程 sheet → 封面选择器（预览 16:7 / 更换 / 移除；选中即上传，保存时 PATCH cover）
  2. 地点 sheet → 照片选择器（96px 预览 / 更换 / 移除）
  3. 展示三处：TripCard 顶部封面条（thumb、`aspect-ratio: 16/7`、圆角随卡）；详情 hero 头图（负 margin 抵消 padding，可点开大图预览）；地点行 **44px 圆角缩略图**（位于 `.place-main` 与 `.place-actions` 之间；点击用 `el-image` 预览大图）
- 无障碍：[图片] 均为装饰性 `alt=""`（信息主体仍是文字）；预览支持键盘 Esc 关闭（EP 自带）

### 4.8 边界、反例与非适用

- 输入域：任何 Pillow 可解格式 ≤4MB；**反例（明确拒绝）**：HEIC/AVIF 直传、伪扩展名、解压炸弹、>4MB、动图（取首帧，静帧化）、多图/相册、跨用户共享同一 key、视频/文档。
- 通用性论证：key 规则不绑定"行程/地点"实体 ⇒ 将来的游记照片可直接复用同一条上传链路与清理模式（不泛化到"任意文件管理"——那是另一个产品）。
- 反例测试：`../../etc/passwd`、`{他人uid}/…`、`zz.jpg`、纯文本伪装 jpg、1×1、20000×20000（炸弹）。

## 5. 被否决的替代方案

| 方案 | 否决理由 |
|---|---|
| 数据库存绝对 URL / 本地绝对路径 | 域名/存储/CDN 任一变化 ⇒ 存量引用全失效（本 ADR 的根因） |
| 图片走 FastAPI 直供（StaticFiles 打到生产） | 占应用线程/带宽，2C2G 上代价不成比例；nginx 直供零成本 |
| 原图直存（不压缩、不重编码） | 磁盘×10 浪费、EXIF GPS 泄露、伪装文件风险、弱网上传体验差 |
| 现在就接 COS | 用户没有 COS；且本设计把切换成本压到"换一个实现 + 搬文件"后，先接 COS 没有收益 |
| 多图相册 v1 就做 | 排序/删除/浏览/带宽四重复杂度，与"先跑通链路"的目标不匹配（用户也选了单图） |

## 6. 防复发机制

1. 归属+穿越双防护集中在 `validate_key`（唯一入口），并有反例测试（§4.8）。
2. 清理顺序纪律：**先提交 DB、后删文件**（注释 + 测试断言替换/删除后旧文件消失）。
3. 前端唯一口径：URL 拼接只在 `utils/media.ts`；check:tokens 守卫新样式不引入新色值。
4. 备份覆盖：media 目录纳入每日备份（见备份 ADR），图片进盘 ≠ 裸奔。
5. 本 ADR 记录"key 不存 URL"的根因，防止后人"顺手把 URL 存进去"。

## 7. 测试计划（Phase 4）

| ID | 类型 | 场景 | 期望 |
|---|---|---|---|
| T1 | Happy | 上传真实小 JPEG（测试内 Pillow 生成） | 201；key 匹配 `^{uid}/\d{4}/\d{2}/[0-9a-f]{32}\.jpg$`；主图+缩略图都在盘上；thumb 更小 |
| T2 | 错误 | 文本字节伪装 .jpg | 400；不落盘 |
| T3 | 边界 | >4MB / 1×1 / 20000×20000 | 400（三条各自成立） |
| T4 | 规范化 | 带 EXIF（含 GPS + Orientation）的 3000×2000 | 输出 ≤2000、无 EXIF、方向已纠正 |
| T5 | 频控 | 日配额调成 2 后连传 3 次 | 第 3 次 429 |
| T6 | 归属/穿越 | PATCH cover/photo 用他人 key、`../../`、非法格式 | 400 且状态不变 |
| T7 | 替换/清空 | 设置→替换→清空 | 每次旧文件被删；`null` 后详情返回 null |
| T8 | 删除联动 | 删除 trip（含 cover + places.photo）/ 删除 place | 对应文件被删；其余不受影响 |
| T9 | 鉴权 | 未登录上传 | 401 |
| T10 | 管线单测 | 透明 PNG / CMYK / GIF 首帧 | 输出白底 RGB JPEG；不抛异常 |
| T11 | E2E（CDP） | 选图→压缩→上传→预览→保存→卡片条/头图/缩略图→大图预览→移除 | 全链路 + toast 错误路径 |
| T12 | 守卫 | lint/check:tokens/type-check/build；后端 65→75+ 全绿 | 全绿 |

## 8. 实施顺序（Phase 3）

1. 依赖：`uv add pillow`（lock 更新）→ `storage.py` → `config.py` 新设置 → `.env.example`/`.gitignore`（`uploads/`）
2. 迁移 `places.photo` + schemas + PATCH 校验/清理 + 删除联动
3. `POST /uploads/images`（管线+频控）+ `main.py` 挂载 `/media` + 路由注册
4. 后端测试 T1–T10
5. 前端：`media.ts`/`imageCompress.ts`/`uploads.ts`/api 类型 → 两个 sheet → 三处展示 → `vite.config.ts` 代理
6. 备份 ADR 的脚本与 cron 同批落地（见另一份 ADR）
7. 验证（T11/T12）→ 部署（nginx 两处 location + 体积上限 + dist + 迁移）→ 线上冒烟

## 9. 已知限制与后续

- UGC 内容审核（备案站义务）：v1 无审核链路，已知限制；后续可加管理员删除接口（配合备份 ADR 的运维面）。
- 孤儿文件（上传未引用）：量级小；后续加 TTL 清理任务。
- 单图制：地点多图相册留待 v2（上传链路可直接复用）。
- 迁移 COS 的步骤（未来）：实现 `storage_cos.py` → `rclone/coscli` 搬运 → `settings.media_root`/`public_url` 切换 → 回归 T7–T8 → 无需改 DB。

---

## 10. 验证与上线记录（Phase 4/5，2026-10-12）

### 10.1 验证证据

- **后端 76 测试全绿**（65 存量 + 11 新增）：上传成功路径/未鉴权 401/伪装文件/超限/1×1 与解压炸弹/GPS+方向 EXIF 抹除与纠正/频控 429/归属与目录穿越（含 `../`、异人 key、非法格式）/替换与清空清理/删除联动清理/管线单测（透明 PNG、CMYK、动图首帧、空载荷）。
- **E2E 16 断言全通过**（CDP 真实文件选择 `DOM.setFileInputFiles` → 前端压缩 → 上传 → 预览 [缩略图] → 保存 → hero 头图 [原图，fetch 200] → 地点行缩略图 → 列表卡封面条 → **服务端落盘结构 `uid/年/月/hex.jpg` + `.thumb.jpg`** → 删除行程后文件被清理）。
- **前端守卫**：check:tokens / oxlint / eslint / type-check / build 全绿。
- **线上冒烟**：`https://waynote.cn/` 200；`/media/` 直供（存在文件 200 `image/jpeg`、不存在 404 不回落 SPA）；上传端点未鉴权 401；`/docs`、`/openapi.json` 直连后端 404（文档未注册）。
- **迁移**：本地 upgrade 往返 + 服务器 `c4a7d92b6e15 → d8e1a4f7c9b2` 已应用（head）✓。

### 10.2 实施偏差

| # | 设计原文 | 实施 | 理由 |
|---|---|---|---|
| ① | 上传响应 `{key,width,height,bytes}` | 额外含 `url` | 让"存储缝"真实可用（未来 COS 需要绝对 URL）；前端渲染仍统一走 `utils/media.ts` |
| ② | 未设定最小边长 | 增加 `MIN_EDGE=64` 拒绝占位/追踪像素 | ADR T3 已把 1×1 定义为 400；实现补齐 |
| ③ | 缩略图 key 未明确正则 | `path_of` 接受 `.thumb.jpg`、`validate_key`（对外引用）拒绝之 | 首轮测试即抓到"缩略图被自己的校验拒了"的 500，见 §6 防复发第 1 条 |

### 10.3 上线记录

- 提交：`9e580e5`（30 files, +1416；含两份 ADR、迁移、测试、前端、nginx、备份脚本与 cron）。
- 服务器：`update.sh` 一键完成（代码 → `uv sync` 装 Pillow → 迁移 → 重启 → 健康检查）；`MEDIA_ROOT=/home/ubuntu/waynote-media` 已写入 `.env` 并建目录；nginx 两个 server 块加 `/media/` 直供与 6m 上传上限（改前备份）。
- 前端 dist：md5 与本地一致；备份 cron 已安装（03:30）。
- 待办：GitHub 推送待代理恢复；**真人真机验证**：请用户在 https://waynote.cn 给自己的行程上传一张封面与地点照片（唯一需要用户账号的环节）。
