# 途笺 WayNote 部署手册

**单机部署**：Ubuntu 24.04 · systemd 托管 · Nginx（静态 + 反代）· PostgreSQL 16（本机）。
面向 2C2G 轻量服务器：**前端在本地构建、只上传 `dist/`**，服务器不装 Node。

---

## 0. 约定（照抄即用，只需替换占位符）

| 占位符 | 说明 |
| --- | --- |
| `改我-数据库密码` | 自己设一个强密码 |
| `waynote.example.com` | 你的域名（备案未过时先看第 8 步的非标端口方案） |
| `你的邮箱` | certbot 证书通知邮箱（第 9 步用） |
| `你的用户名` / `服务器IP` | 你登录服务器用的账号与公网 IP |

目录与端口（全文统一，无需修改）：

```
代码目录    /srv/waynote              运行用户  waynote（系统账号，无登录 shell）
虚拟环境    /srv/waynote/.venv        后端      127.0.0.1:8000（只监听本机）
日志        /var/log/waynote          数据库    PostgreSQL 16，本机 5432
```

**服务器已有**：Python、Nginx → **本手册需要装**：PostgreSQL 16、uv（第 1 步）。

---

## 1. 系统准备（一次性）

```bash
sudo apt update
sudo apt install -y postgresql curl git unzip

# 2G 内存建议加 2G swap（迁移更稳；已有 swap 可跳过）
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 服务专用账号（无登录 shell）
sudo useradd --system --create-home --shell /usr/sbin/nologin waynote

# uv：用来获取 Python 3.13 与项目依赖
# （Ubuntu 24.04 自带 Python 3.12，本项目要求 >=3.13，uv 会自动下载独立解释器）
curl -LsSf https://astral.sh/uv/install.sh | sudo env UV_INSTALL_DIR=/usr/local/bin sh
uv --version
```

## 2. 建数据库（一次性）

```bash
sudo -u postgres psql -c "CREATE USER waynote WITH PASSWORD '改我-数据库密码';"
sudo -u postgres psql -c "CREATE DATABASE waynote OWNER waynote;"

# 验证（能打印版本号即可）
psql "postgresql://waynote:改我-数据库密码@127.0.0.1:5432/waynote" -c "select version();"
```

## 3. 拉代码 + 装后端依赖

```bash
sudo mkdir -p /srv/waynote && sudo chown waynote:waynote /srv/waynote
sudo -u waynote git clone https://github.com/forward-aways/WayNote.git /srv/waynote

cd /srv/waynote
sudo -u waynote /usr/local/bin/uv sync --frozen --no-dev    # 只装生产依赖（pytest/ruff 等不装）
```

**网络小贴士（国内服务器）**

- PyPI 慢：`export UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple` 后再执行 `uv sync`
- uv 下载 Python 3.13 失败：uv 从 GitHub 拉独立解释器，可设镜像
  `export UV_PYTHON_INSTALL_MIRROR=<你的代理或镜像前缀>https://github.com/astral-sh/python-build-standalone/releases/download`
- **`git clone` 慢或失败**：改用本地打包上传（之后升级就重复"打包 + 上传 + 覆盖"）

  ```bash
  # 本地开发机（用已提交的代码打包，不含 .env 等未跟踪文件）
  git archive --format=tar.gz -o waynote.tar.gz HEAD
  scp waynote.tar.gz 你的用户名@服务器IP:/tmp/

  # 服务器
  sudo tar -xzf /tmp/waynote.tar.gz -C /srv/waynote
  sudo chown -R waynote:waynote /srv/waynote
  ```

## 4. 写配置（一次性）

```bash
sudo -u waynote cp /srv/waynote/backend/.env.example /srv/waynote/backend/.env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # ← 生成 SECRET_KEY，先复制输出
sudo -u waynote nano /srv/waynote/backend/.env
```

`.env` 填成下面这样（其余保持默认）：

```
DATABASE_URL=postgresql+psycopg://waynote:改我-数据库密码@127.0.0.1:5432/waynote
SECRET_KEY=粘贴上一步生成的值
TRUSTED_PROXY_IPS=127.0.0.1
LOG_DIR=/var/log/waynote
# ALLOW_REGISTRATION=false   # 不想开放注册就去掉注释
```

```bash
sudo chmod 600 /srv/waynote/backend/.env
sudo mkdir -p /var/log/waynote && sudo chown waynote:waynote /var/log/waynote
```

## 5. 建表（迁移）

```bash
cd /srv/waynote/backend
sudo -u waynote /srv/waynote/.venv/bin/alembic upgrade head
```

> 必须在 `backend/` 目录下执行（`alembic.ini` 里 `prepend_sys_path = .`，迁移脚本要能 `import app`）。

## 6. 起后端（systemd）

```bash
sudo cp /srv/waynote/deploy/waynote.service /etc/systemd/system/waynote.service
sudo systemctl daemon-reload
sudo systemctl enable --now waynote
sudo systemctl status waynote --no-pager          # 看到 active (running) 即可

curl -s http://127.0.0.1:8000/api/v1/health       # 期望 {"status":"ok","database":"connected"}
```

## 7. 放前端产物（本地构建 → 上传）

```bash
# ① 本地开发机
cd frontend && npm ci && npm run build

# ② 服务器：建目标目录
sudo mkdir -p /srv/waynote/frontend/dist && sudo chown -R waynote:waynote /srv/waynote/frontend/dist

# ③ 本地开发机：上传（先传到 /tmp，再进目标目录）
scp -r frontend/dist/* 你的用户名@服务器IP:/tmp/dist-upload/

# ④ 服务器：搬进去
sudo cp -r /tmp/dist-upload/* /srv/waynote/frontend/dist/
sudo chown -R waynote:waynote /srv/waynote/frontend/dist
```

> 习惯 `rsync` 的话，③④ 可合并为：
> `rsync -av --delete frontend/dist/ 你的用户名@服务器IP:/tmp/dist-upload/` 后接第 ④ 步。
> 服务器内存充足（≥1G 空闲）时也可在服务器上 `npm ci && npm run build`。

## 8. Nginx

```bash
sudo cp /srv/waynote/deploy/nginx.conf /etc/nginx/sites-available/waynote
sudo nano /etc/nginx/sites-available/waynote       # 把 server_name 改成你的域名
sudo ln -sf /etc/nginx/sites-available/waynote /etc/nginx/sites-enabled/waynote
sudo rm -f /etc/nginx/sites-enabled/default        # 移除默认站点（可选但推荐）
sudo nginx -t && sudo systemctl reload nginx
```

浏览器打开 `http://你的域名/` → 应能看到落地页，注册 / 登录 / 建行程全部可用。

**备案未通过时**（国内服务器 80/443 会被拦）：把站点里的 `listen 80;` 改成 `listen 8080;`，
用 `http://服务器IP:8080/` 先验证功能（记得 `sudo ufw allow 8080` 或在腾讯云控制台放行端口）。

## 9. HTTPS（域名备案 + 解析生效后）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d waynote.example.com -m 你的邮箱 --agree-tos --redirect
sudo systemctl list-timers | grep certbot          # 确认自动续期已就位
```

## 10. 以后升级（每次发版）

```bash
cd /srv/waynote
sudo -u waynote git pull                      # 若当初是"打包上传"方式，改为重新打包 + 覆盖
sudo -u waynote /usr/local/bin/uv sync --frozen --no-dev

cd backend && sudo -u waynote /srv/waynote/.venv/bin/alembic upgrade head && cd ..

sudo systemctl restart waynote
```

前端：本地 `npm run build` 后按第 7 步 ③④ 覆盖 `dist/`（Nginx 直接读目录，**不用重启**）。

## 11. 备份（一次性配置）

```bash
sudo mkdir -p /var/backups/waynote && sudo chown postgres:postgres /var/backups/waynote
echo '30 3 * * * postgres pg_dump waynote | gzip > /var/backups/waynote/waynote-$(date +\%F).sql.gz' \
  | sudo tee /etc/cron.d/waynote-backup
sudo chmod 644 /etc/cron.d/waynote-backup

# 恢复（示例：把某天备份还原到 waynote 库）
# gunzip -c /var/backups/waynote/waynote-2026-09-29.sql.gz | psql "postgresql://waynote:密码@127.0.0.1:5432/waynote"
```

## 12. 排障速查

```bash
sudo systemctl status waynote --no-pager      # 服务是否在跑
sudo journalctl -u waynote -n 80 --no-pager   # 后端日志（含启动失败原因）
sudo tail -n 80 /var/log/waynote/*.log        # 应用日志（按天轮转，保留 14 天）
sudo nginx -t                                 # Nginx 配置语法
```

| 现象 | 原因 / 处理 |
| --- | --- |
| 打开网页 502 | 后端没起来：看 `journalctl -u waynote`，多半是 `.env` 的 `DATABASE_URL` 连不上 |
| 首页 404 | `dist/` 没放对：`ls /srv/waynote/frontend/dist`（应看到 `index.html` 和 `assets/`） |
| 刷新子页面 404 | Nginx 少了 `try_files ... /index.html`（用仓库里的 `deploy/nginx.conf`） |
| 注册/登录报 500 | 迁移没跑：第 5 步 |
| 服务反复重启 | 内存不足被 `MemoryMax` 杀掉：加 swap，或调大 `waynote.service` 里的 `MemoryMax` |
| 静态资源更新后仍旧版 | 浏览器缓存：强刷（Ctrl+F5）；`/assets/` 是长缓存，文件名带 hash 会自动失效 |

## 13. 安全清单（部署后自查）

- [ ] `ufw` 只放行 22 / 80 / 443（或临时用的非标端口），**不要**放行 8000
- [ ] `backend/.env` 权限 600，`SECRET_KEY` 是随机值（不是示例值）
- [ ] `TRUSTED_PROXY_IPS=127.0.0.1`（**绝不填公网网段**）
- [ ] 后端只监听 `127.0.0.1:8000`，数据库只听本机
- [ ] 按需设 `ALLOW_REGISTRATION=false`（后续会改为邮件验证码注册）
