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
