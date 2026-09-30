# ADR：部署方案（单机 systemd）

- 日期：2026-09-29
- 状态：已确认（用户选择 systemd 裸机方案）
- 产物：`deploy/DEPLOY.md`（操作手册）、`deploy/waynote.service`、`deploy/nginx.conf`

## 背景

- 目标环境：腾讯云轻量 **Ubuntu 24.04，2C2G**（内存偏紧）；**已有 Python 与 Nginx**，**无数据库**。
- 约束：ICP 备案未通过前 80/443 不可用；单体应用、个人规模流量。

## 决策

1. **单机架构**：Nginx（静态 `frontend/dist` + `/api` 反代）→ uvicorn（`127.0.0.1:8000`，systemd）→ 本机 PostgreSQL 16。**不用 Docker**：内存紧张，省一层运行时开销，也少一套需要维护的编排。
2. **只用 1 个 uvicorn worker**：`client_logs` 限流是**进程内内存桶**（`_buckets: dict`）——多 worker 会让限额按 worker 数翻倍。个人规模 1 个足够；将来要扩容，第一步是把限流换成共享存储（Redis）。
3. **不给 uvicorn 加 `--proxy-headers`**：`RequestContextMiddleware` 自己按 `TRUSTED_PROXY_IPS` 白名单采信 `X-Forwarded-For`；让 uvicorn 改写 `scope["client"]` 会与白名单判断打架（保持"直连对端=127.0.0.1"才能采信 Nginx 递来的 XFF）。
4. **前端本地构建、只上传 `dist/`**：2G 内存跑 Vite 构建有 OOM 风险；产物纯静态，Nginx 直接读目录，服务器无需 Node。
5. **Python 3.13 由 uv 提供**：Ubuntu 24.04 自带 3.12，不满足 `requires-python >=3.13`；用 uv 的独立解释器，不引入 deadsnakes PPA。
6. **运行身份**：系统账号 `waynote`（`--system`，无登录 shell）；代码 `/srv/waynote`、虚拟环境 `/srv/waynote/.venv`、日志 `/var/log/waynote`。
7. **HTTPS**：备案 + 解析生效后用 `certbot --nginx --redirect`；备案前用非标端口（如 8080）验证功能。
8. **systemd 加固**：`MemoryMax=512M`（超限自动重启）、`NoNewPrivileges`、`PrivateTmp`、`Restart=always`。
9. **备份**：cron 每日 `pg_dump | gzip` → `/var/backups`。

## 后果与注意事项

- 升级流程见 `deploy/DEPLOY.md` 第 10 节；**迁移必须在 `backend/` 目录执行**（`alembic.ini` 的 `prepend_sys_path = .`，迁移脚本需要 `import app`）。
- `alembic.ini` 不得写入非 ASCII 字符（Windows GBK 历史坑；Linux 无此问题，但保持纪律）。
- 安全自查见 `DEPLOY.md` 第 13 节：8000 端口不对外、`.env` 600、`TRUSTED_PROXY_IPS` 只填 `127.0.0.1`、按需关闭注册。
- 本 ADR 不排除后续引入 Docker Compose（多环境一致性诉求出现时再评估）。

## 实测修订（2026-09-30，腾讯云轻量 · Ubuntu 24.04）

实际部署中修正了以下几条（以 `deploy/` 目录下的文件为准）：

1. **端口规划（与同机既有服务共存）**：8000 已被同机其它应用占用、8080 已被既有 nginx 站点占用 → waynote 后端改用 **8010**、对外站点用 **8090**；部署前用 `ss -ltnp` 确认空闲。
2. **不建系统账号、不用系统日志目录**：以部署者本人（`ubuntu`）运行，代码在 `~/ai-project/WayNote`，日志写项目内 `backend/logs`（代码自动创建）——原方案里的 `useradd` / `chown /var/log/*` 全部取消。
3. **依赖走 uv**：`uv sync --frozen --no-dev` + `uv run alembic upgrade head`（`uv run` 自动定位 `.venv`，避免手拼路径）；`deploy/requirements.txt` 保留作为"没有 uv"时的 pip 兜底。
4. **前端一律本地构建**：服务器 Node 20 不满足项目要求（`^22.18.0 || >=24.12.0`），且 2G 内存构建风险高 → 本地 build 后 `scp` 上传 `dist`。
5. **家目录权限坑（表现为 500）**：nginx worker 无法进入 `/home/ubuntu`（默认没有 `o+x`）→ `stat() ... Permission denied` → `try_files` 兜底触发 `rewrite or internal redirection cycle` → 500。修法：`sudo chmod o+x /home/ubuntu`；或把 `dist` 放到 `/var/www/waynote`。排查用 `namei -l <路径>`。
6. **站点文件放在既有 nginx 布局的同一目录**（实测为 `/etc/nginx/sites-enabled/`），用独立端口与既有站点共存，不动默认站点。
