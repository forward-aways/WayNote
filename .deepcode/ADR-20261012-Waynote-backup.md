# ADR-20261012：每日自动备份（数据库 + media 目录）与恢复演练

- 状态：待确认（与图片 ADR 同批交付，Phase 1/2 完成）
- 日期：2026-10-12
- 关联：ADR-20261012-Waynote-image-upload.md（media 目录的来源）、ADR-20260929-Waynote-deployment-systemd.md（服务器/目录纪律）、ADR-20261009-Waynote-email-code-auth.md（cron 方式先例：/etc/cron.d）

---

## 1. 背景与问题

- 生产库与文件目录目前**没有任何备份**：一次误删数据、一次坏迁移、一次磁盘故障 = 全部丢失。这是当前产品最大的单点风险（产品经理路线图 P0 第 1 项）。
- 图片特性上线后，本地盘上会多一份**只增不减**的 media 资产，备份范围必须同时覆盖。
- 用户已抉择：与图片同批把每日备份补上。

## 2. 现状约束

| 项 | 事实 |
|---|---|
| 磁盘 | 40G 中 26G 空闲（DB 很小；media 预计 ≤ 数 GB/年） |
| 数据库 | PostgreSQL 16 本机，库 `waynote`；`ubuntu` 有免密 sudo（可 `sudo -n -u postgres`） |
| 既有 cron | 过期验证码清理：`/etc/cron.d/waynote-cleanup`，04:30（本方案错开到 03:30） |
| 目录 | 代码在 `/home/ubuntu/ai-project/WayNote`；media_root（生产）计划 `/home/ubuntu/waynote-media` |
| 单机 | 无对象存储、无第二台机器（同盘备份是"已知限制"，见 §6） |

## 3. 设计

### 3.1 触发与产物

```
/etc/cron.d/waynote-backup        # ubuntu 用户，03:30（错开 04:30 的验证码清理）
30 3 * * * ubuntu /home/ubuntu/ai-project/WayNote/deploy/waynote-backup.sh >> /home/ubuntu/backups/backup.log 2>&1
```

```
~/backups/                          (700)
├── db/waynote-YYYYMMDD.dump        (600, pg_dump -Fc 自定义格式=自带压缩)
├── media/current -> media-YYYYMMDD (软链，指向最新快照)
├── media/media-YYYYMMDD/            (rsync --link-dest 增量快照)
└── backup.log
```

### 3.2 步骤（`deploy/waynote-backup.sh`，`set -euo pipefail`，幂等可重跑）

1. **DB dump**：`sudo -n -u postgres pg_dump -Fc waynote` 写入 `*.tmp` → `pg_restore --list` 自检通过后原子 `mv` 为正式名（绝不留下"看起来成功实则半截"的 dump）。
2. **media 快照**（核心决策）：
   ```
   rsync -a --delete --link-dest="$PREV_SNAPSHOT_ABS" "$MEDIA_ROOT/" "media-$TODAY/"
   ln -sfn "media-$TODAY" media/current
   ```
   **为什么用 rsync 硬链接快照而不是每天 tar 全量**：media 的数据特征 = 只增不改（uuid 文件名不可变）⇒ `--link-dest` 让"未变化的文件"在新快照里只是硬链接，**每份快照的增量成本 ≈ 当日新增图片的字节数**；tar 全量则是 O(全量)×14 天。这是数据结构与算法选择匹配问题形态的点（内容不可变 ⇒ 结构共享）。
   - 首次运行（无 media/无 prev）：目录不存在则跳过并记日志，不失败。
3. **保留策略**：`db/*.dump` 与 `media/media-*` 各保留 14 份（`find … -mtime +14` / `ls -1dt | tail -n +15`），**先落新产物再删旧**（磁盘紧张时宁可少一份历史，也不留半截新产物）。
4. **日志**：追加到 `backup.log`（含每步大小与耗时）；`set -e` 任一步失败即整个脚本失败并留下错误栈。

### 3.3 恢复演练（本次交付必须执行一次并留证）

| 步骤 | 命令要点 | 通过标准 |
|---|---|---|
| DB 恢复 | `createdb waynote_restore_test` → `pg_restore -d …` → 比对 `users/trips/places` 计数 | 计数与生产一致 |
| media 恢复 | 从最近快照 `rsync -a` 到临时目录 | 文件数与 `find media_root -type f` 一致 |
| 清理 | `dropdb waynote_restore_test` + 删临时目录 | 生产库/目录不受影响 |

### 3.4 文档

`deploy/DEPLOY.md` 新增「备份与恢复」节：产物位置、保留策略、**一步步的恢复命令**、手动拉取到本机（`scp -r`）的方法、以及将来的异地备份建议（有对象存储后 `rclone`；或接入监控告警）。

## 4. 不变量与边界

- **I1**：备份产物权限 700/600（含 dump 与 media 快照）；不进 git 工作区。
- **I2**：脚本任意次数重跑结果一致（同日重跑覆盖当天的 tmp→最终产物；media 快照同日重建等价）。
- **I3**：只有"自检通过 + 原子改名完成"的 dump 才会被保留策略看到；半截产物只会以 `.tmp` 存在并被下次运行清理。
- **反例/边界**：media 为空（首次）→ 跳过不失败；快照数量 <14 → 不删任何东西；磁盘写满 → 脚本失败但既有备份不被破坏（删除策略在最后一步）。
- **非适用**：异地容灾、PITR（WAL 归档）、多副本 —— 超出个人项目规模，见 §6。

## 5. 被否决的替代方案

| 方案 | 否决理由 |
|---|---|
| 每天 tar 全量 media | 保留 14 天 = 14 倍空间；与"图片不可变"的数据特征不匹配 |
| systemd timer 替代 cron | 与既有 cleanup 先例（cron）不一致；无收益 |
| 备份放在代码仓库目录内 | update.sh 以 git 工作区判定更新，且备份不应与代码混放 |
| 只备份 DB 不备份 media | 图片丢失同样不可逆（且用户已明确要求含图片） |
| WAL 归档/PITR | 复杂度与运维面远超收益（个人项目、RPO≈24h 可接受） |

## 6. 已知限制

- **同盘备份**：整块磁盘故障 ⇒ 数据与备份同时丢失。缓解路径（按序）：① 有对象存储后 rclone 异地（半小时可加）；② 或定期从本机 `scp` 拉一份（文档已写命令）；③ 接入监控告警（路线图 P2）。
- **无失败告警**：备份失败只体现在 `backup.log`；建议在监控/告警落地前，每周人工看一眼日志（文档中写明）。
- RPO ≈ 24 小时（每日一次）。

## 7. 测试计划

| ID | 场景 | 期望 |
|---|---|---|
| B1 | 手工执行脚本（有数据 + 有 media） | dump 自检通过、快照生成、`current` 指向今天、日志完整 |
| B2 | 再执行一次（幂等） | 结果与 B1 一致，无报错，旧产物不受影响 |
| B3 | 恢复演练（§3.3 三步） | 计数/文件数一致；生产不受影响 |
| B4 | 边界：media 目录为空/不存在 | 跳过 media 步骤，DB 备份照常，退出码 0 |
| B5 | 保留策略 | 造 15 份假产物 → 最旧一份被清理，且新产物完整 |
| B6 | 安装 cron 并确认下一次触发时间（`systemctl status cron` / 日志） | 已注册、时间 03:30 |
