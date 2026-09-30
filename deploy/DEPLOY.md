# 途笺 WayNote 部署（Ubuntu 24.04 · systemd · 实测版）

> 本文件是 **2026-09-30 在腾讯云轻量（2C2G）上跑通的实测记录**，参数与那台机器一致；
> 换机器只需改：用户名、代码路径、端口（见「端口规划」）。

| 项 | 实际值 |
| --- | --- |
| 代码路径 | `/home/ubuntu/ai-project/WayNote` |
| 运行账号 | `ubuntu`（**不建系统账号**） |
| 后端 | systemd 服务 `waynote` → `127.0.0.1:8010`（开机自启） |
| 对外访问 | nginx 站点 `8090` → `http://<服务器IP>:8090/` |
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

## 8. 以后升级

```bash
cd /home/ubuntu/ai-project/WayNote && git pull
cd backend && uv run alembic upgrade head && cd ..
sudo systemctl restart waynote
```

前端有改动时：本地重新 `npm run build` → `scp` → 覆盖 `frontend/dist`（Nginx 不用重启）。

## 9. 备份（可选）

```bash
sudo mkdir -p /home/ubuntu/waynote-backups && sudo chown postgres:postgres /home/ubuntu/waynote-backups
sudo tee /etc/cron.d/waynote-backup >/dev/null <<'EOF'
30 3 * * * postgres pg_dump waynote | gzip > /home/ubuntu/waynote-backups/waynote-$(date +\%F).sql.gz
EOF
```

恢复：`gunzip -c .../waynote-日期.sql.gz | psql "postgresql://waynote:密码@127.0.0.1:5432/waynote"`

## 10. 排障（实测踩过的都在这里）

| 现象 | 原因 / 处理 |
| --- | --- |
| 网页 **500**，error.log 里有 `Permission denied` + `rewrite or internal redirection cycle` | nginx worker 进不去家目录 → `sudo chmod o+x /home/ubuntu`。排查：`namei -l /home/ubuntu/ai-project/WayNote/frontend/dist/index.html` |
| 网页 **500**（无 Permission denied） | `index.html` 不存在 → 确认 `frontend/dist` 里有 `index.html` |
| 网页 **502** | 后端没起来 → `sudo journalctl -u waynote -n 50 --no-pager` |
| `curl 127.0.0.1:8010/...` 无任何输出 | 服务没跑或端口被占 → `sudo systemctl status waynote`、`sudo ss -ltnp \| grep 8010` |
| 服务反复重启 | 看 journalctl；常见是单元文件里的 `User`/路径与真实不符 |
| 接口报 500 / 注册失败 | 迁移没跑 → 第 4 步 |
| `uv run alembic` 报找不到 / 命令不存在 | 必须在 `backend/` 目录下执行；或先 `uv sync --frozen --no-dev` |
| 刷新子页面 404 | nginx 里 `try_files $uri $uri/ /index.html` 被删了 |
