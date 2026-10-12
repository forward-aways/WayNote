# 途笺 WayNote 部署（Ubuntu 24.04 · systemd · 实测版）

> 本文件是 **2026-09-30 在腾讯云轻量（2C2G）上跑通的实测记录**，参数与那台机器一致；
> 换机器只需改：用户名、代码路径、端口（见「端口规划」）。

| 项 | 实际值 |
| --- | --- |
| 代码路径 | `/home/ubuntu/ai-project/WayNote` |
| 运行账号 | `ubuntu`（**不建系统账号**） |
| 后端 | systemd 服务 `waynote` → `127.0.0.1:8010`（开机自启） |
| 对外访问 | **`https://waynote.cn`**（80 → 301 → 443，Let's Encrypt）；`8090` 保留为应急兜底 |
| 数据库 | PostgreSQL 16（本机 5432，库/用户均为 `waynote`） |
| 日志 | `<代码路径>/backend/logs`（代码自动创建，按天轮转 14 天） |

### 端口规划（与同机既有服务共存）

| 端口 | 占用者 | 说明 |
| --- | --- | --- |
| 8000 | 同机其它应用（MeiKen AI） | 所以 waynote 后端改用 **8010** |
| 8080 | 同机 nginx 既有站点 | 所以 waynote 站点改用 **8090** |
| 8010 / 8090 | **waynote** | 部署前先确认空闲 |

```bash
sudo ss -ltnp | grep -E ':(8010|8090)\b' || echo "8010/8090 都空着，可以部署"
```

### 域名与 HTTPS（2026-10-12 上线）

| 项 | 实际值 |
| --- | --- |
| 域名 | `waynote.cn` / `www.waynote.cn`（DNS 在 DNSPod，A 记录 → 本机 IP） |
| 备案 | 辽ICP备2026015937号-2（落地页页脚悬挂并链接工信部备案官网） |
| 证书 | Let's Encrypt（`certbot --nginx` 签发，`certbot.timer` 自动续期；演练 `sudo certbot renew --dry-run`） |
| nginx | 站点文件 `deploy/nginx.conf`：域名 80/443 块（certbot 管理）+ 8090 兜底块 |
| 验证 | `curl -sI https://waynote.cn/ \| head -1`、`curl -s https://waynote.cn/api/v1/health` |

### 图片媒体（本地存储）

| 项 | 实际值 |
| --- | --- |
| 存储根 | `MEDIA_ROOT=/home/ubuntu/waynote-media`（独立目录、不进代码仓库；见 ADR-20261012 图片篇） |
| 直供 | nginx `location /media/` → `alias /home/ubuntu/waynote-media/`（长缓存 + nosniff，不走应用） |
| 上传 | `POST /api/v1/uploads/images`（≤4MB，前端会先压缩）；nginx `client_max_body_size 6m` |
| 迁移 COS | 换 `app/core/storage.py` 实现 + 搬文件 + 改 `MEDIA_URL_PREFIX`；数据库存的是相对 key，无需改动 |

### 备份与恢复（每日 03:30 自动）

```bash
# 手动执行一次
bash /home/ubuntu/ai-project/WayNote/deploy/waynote-backup.sh

# 产物（~/backups，700；保留 14 份）
#   db/waynote-YYYYMMDD.dump      数据库（pg_dump -Fc，自检通过后原子改名）
#   media/current -> media-*      media 硬链接快照（增量≈当日新增）
#   backup.log                    每次运行日志
```

**恢复演练（已验证过一次）：**

```bash
# 1) 数据库：恢复到临时库并比对计数
sudo -u postgres createdb waynote_restore_test
sudo -u postgres pg_restore -d waynote_restore_test ~/backups/db/waynote-<日期>.dump
sudo -u postgres psql -d waynote_restore_test -c "SELECT (SELECT count(*) FROM users) users, (SELECT count(*) FROM trips) trips, (SELECT count(*) FROM places) places;"
sudo -u postgres psql -d waynote          -c "SELECT (SELECT count(*) FROM users) users, (SELECT count(*) FROM trips) trips, (SELECT count(*) FROM places) places;"
sudo -u postgres dropdb waynote_restore_test

# 2) media：从快照恢复（示例：恢复全部文件到原目录）
rsync -a --delete ~/backups/media/current/ /home/ubuntu/waynote-media/

# 3) 拉一份到本机（异地容灾的最小手段；整盘故障时备份同盘会一起丢，见 ADR §6）
#    scp -r ubuntu@81.70.160.226:/home/ubuntu/backups/db ./
```

---

## 1. 装 PostgreSQL

```bash
sudo apt update && sudo apt install -y postgresql
sudo systemctl enable --now postgresql

sudo -u postgres psql -c "CREATE USER waynote WITH PASSWORD '改我';"
sudo -u postgres psql -c "CREATE DATABASE waynote OWNER waynote;"

psql "postgresql://waynote:改我@127.0.0.1:5432/waynote" -c "select 1"    # 返回 1 即成功
```

## 2. 装 Python 依赖

```bash
cd /home/ubuntu/ai-project/WayNote
uv sync --frozen --no-dev
```

> 没有 uv 时（要求 `python3 -V` ≥ 3.13）：
> `python3 -m venv .venv && .venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r deploy/requirements.txt`

## 3. 写配置（只改两行）

```bash
cd /home/ubuntu/ai-project/WayNote/backend
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"    # 复制输出当 SECRET_KEY
nano .env
chmod 600 .env
```

`.env` 里只需要改这两行（其余保持默认）：

```
DATABASE_URL=postgresql+psycopg://waynote:改我@127.0.0.1:5432/waynote
SECRET_KEY=粘贴上一步的输出
```

> `.env.example` 里带内容的只有这两行，其余都是注释掉的「可选项」，默认值在 `backend/app/core/config.py`；
> 其中 `TRUSTED_PROXY_IPS=127.0.0.1,::1` 正好匹配「nginx 与后端同机」，不用改。

## 4. 建表

```bash
cd /home/ubuntu/ai-project/WayNote/backend
uv run alembic upgrade head
```

> `uv run` 会自动定位项目里的 `.venv`，不用手拼路径；必须在 `backend/` 目录下执行。

## 5. 起后端（systemd）

```bash
sudo cp /home/ubuntu/ai-project/WayNote/deploy/waynote.service /etc/systemd/system/waynote.service
sudo systemctl daemon-reload
sudo systemctl enable --now waynote

sudo systemctl status waynote --no-pager | head -5
curl -s http://127.0.0.1:8010/api/v1/health     # 期望 {"status":"ok","database":"connected"}
```

排错入口：`sudo journalctl -u waynote -n 50 --no-pager`

## 6. 构建前端（**在本地构建**，服务器不构建）

服务器的 Node 20 不满足项目要求（`^22.18.0 || >=24.12.0`），且 2G 内存构建风险高。

```bash
# 本地开发机
cd frontend && npm ci && npm run build
scp -r dist ubuntu@<服务器IP>:/tmp/
```

```bash
# 服务器
mkdir -p /home/ubuntu/ai-project/WayNote/frontend/dist
cp -r /tmp/dist/* /home/ubuntu/ai-project/WayNote/frontend/dist/
ls /home/ubuntu/ai-project/WayNote/frontend/dist     # 应看到 index.html 与 assets/
```

## 7. Nginx

```bash
sudo cp /home/ubuntu/ai-project/WayNote/deploy/nginx.conf /etc/nginx/sites-enabled/waynote.conf
sudo nginx -t && sudo systemctl reload nginx
```

**关键一步**（静态文件在家目录下，必须让 nginx 能"进入"家目录）：

```bash
sudo chmod o+x /home/ubuntu
```

浏览器打开 `http://<服务器IP>:8090/`（云控制台/防火墙放行 8090）。
这个站点与同机既有站点**互不影响**（不同端口、不同 server 块）。

## 8. 以后更新

**服务器不要再用 `git pull`**：这台机器在国内直连 `github.com` 会被 TLS 重置
（`fatal: unable to access ... GnuTLS recv error (-110): The TLS connection was non-properly terminated.`），
取代码改成「本地打包 → 送进服务器」。

### 8.1 后端 / 整仓代码更新

```powershell
# 本地（Windows PowerShell，仓库根目录）
git bundle create waynote.bundle main
scp waynote.bundle ubuntu@<服务器IP>:/tmp/
```

```bash
# 服务器
bash /home/ubuntu/ai-project/WayNote/deploy/update.sh /tmp/waynote.bundle
```

`deploy/update.sh` 依次做四件事：应用代码（`git fetch` bundle + 只允许快进合并）→
`uv sync --frozen --no-dev`（Python 工程根在**仓库根**：`pyproject.toml`/`uv.lock`/`.venv` 都在那）→
`backend/` 下 `uv run alembic upgrade head` → 重启 `waynote` 并打健康检查。
不带参数运行则只做后三步（代码已更新时用）。

### 8.2 前端更新（本地构建，服务器不构建）

```powershell
# 本地：构建 + 上传（先清服务器上的旧临时目录，避免 scp 套成 /tmp/dist/dist）
cd frontend; npm run build
ssh ubuntu@<服务器IP> 'rm -rf /tmp/dist'
scp -r dist ubuntu@<服务器IP>:/tmp/
```

```bash
# 服务器：备份现有 dist → 覆盖 → 自检（Nginx 不用重启）
cd /home/ubuntu/ai-project/WayNote/frontend
cp -r dist "dist.bak.$(date +%Y%m%d-%H%M%S)"
rsync -a --delete /tmp/dist/ dist/
md5sum dist/index.html        # 与本地 Get-FileHash -Algorithm MD5 .\dist\index.html 对照
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8090/
```

回滚：`rm -rf dist && cp -r dist.bak.<时间戳> dist`

> **字体文件**：`frontend/public/fonts/harmonyos-sans-sc/`（HarmonyOS Sans SC 拆分版，约 9.5MB，**不入库**）。
> 新机器首次构建前先跑 `node scripts/fetch-fonts.mjs`；没有它也能构建，只是页面回退到系统字体（不会报错）。

## 9. 备份（可选）

```bash
sudo mkdir -p /home/ubuntu/waynote-backups && sudo chown postgres:postgres /home/ubuntu/waynote-backups
sudo tee /etc/cron.d/waynote-backup >/dev/null <<'EOF'
30 3 * * * postgres pg_dump waynote | gzip > /home/ubuntu/waynote-backups/waynote-$(date +\%F).sql.gz
EOF
```

恢复：`gunzip -c .../waynote-日期.sql.gz | psql "postgresql://waynote:密码@127.0.0.1:5432/waynote"`

**过期验证码清理**（建议开，一行 cron；`deploy/waynote-cleanup.cron`）：

```bash
sudo cp /home/ubuntu/ai-project/WayNote/deploy/waynote-cleanup.cron /etc/cron.d/waynote-cleanup
sudo chmod 644 /etc/cron.d/waynote-cleanup
systemctl is-active cron
```

每天 04:30 删除 30 天前的 `email_codes` 行（验证码 TTL 仅 10 分钟，旧行必然是终态）。手动核对：

```bash
sudo -u postgres psql -d waynote -c "SELECT count(*) AS rows, min(created_at) FROM email_codes;"
```

## 10. 排障（实测踩过的都在这里）

| 现象 | 原因 / 处理 |
| --- | --- |
| 网页 **500**，error.log 里有 `Permission denied` + `rewrite or internal redirection cycle` | nginx worker 进不去家目录 → `sudo chmod o+x /home/ubuntu`。排查：`namei -l /home/ubuntu/ai-project/WayNote/frontend/dist/index.html` |
| 网页 **500**（无 Permission denied） | `index.html` 不存在 → 确认 `frontend/dist` 里有 `index.html` |
| 网页 **502** | 后端没起来 → `sudo journalctl -u waynote -n 50 --no-pager` |
| `curl 127.0.0.1:8010/...` 无任何输出 | 服务没跑或端口被占 → `sudo systemctl status waynote`、`sudo ss -ltnp \| grep 8010` |
| 服务反复重启 | 看 journalctl；常见是单元文件里的 `User`/路径与真实不符 |
| 接口报 500 / 注册失败 | 迁移没跑 → 第 4 步 |
| 「获取验证码」返回 **503**「邮件服务未配置」 | `backend/.env` 的 `SMTP_*` 未填 → 见 `.env.example` 的 SMTP 段（163 需生成客户端授权码），改完 `sudo systemctl restart waynote` |
| 「获取验证码」返回 **502**「邮件发送失败」 | 服务器到发信服务不通或授权码错误 → `sudo journalctl -u waynote -n 30 --no-pager` 看 `auth.email_code.send_failed` |
| `uv run alembic` 报找不到 / 命令不存在 | 必须在 `backend/` 目录下执行；或先 `uv sync --frozen --no-dev` |
| 刷新子页面 404 | nginx 里 `try_files $uri $uri/ /index.html` 被删了 |
