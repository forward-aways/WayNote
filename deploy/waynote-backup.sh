#!/usr/bin/env bash
# 途笺 WayNote · 每日备份（数据库 + media 目录）与保留策略
#
# 设计见 .deepcode/ADR-20261012-Waynote-backup.md §3.2。安装：
#   sudo cp deploy/waynote-backup.cron /etc/cron.d/waynote-backup && sudo chmod 644 /etc/cron.d/waynote-backup
#   mkdir -p /home/ubuntu/backups        # cron 的重定向目标目录必须先存在
# 手动执行：bash deploy/waynote-backup.sh
#
# 产物（~/backups，权限 700）：
#   db/waynote-YYYYMMDD.dump     pg_dump -Fc（自检通过后原子改名）
#   media/current -> media-*     rsync --link-dest 硬链接快照（图片只增不改 ⇒ 增量≈当日新增）
#   backup.log                   追加日志（失败告警未接入，见 ADR §6）
set -euo pipefail

DB_NAME="waynote"
BACKUP_ROOT="$HOME/backups"
DB_DIR="$BACKUP_ROOT/db"
MEDIA_SNAP_DIR="$BACKUP_ROOT/media"
MEDIA_ROOT="${MEDIA_ROOT:-/home/ubuntu/waynote-media}"
KEEP=14
TODAY="$(date +%Y%m%d)"
PREFIX="[$(date '+%F %T')]"

mkdir -p "$DB_DIR" "$MEDIA_SNAP_DIR"
chmod 700 "$BACKUP_ROOT" "$DB_DIR" "$MEDIA_SNAP_DIR"
echo "$PREFIX == 备份开始（DB=$DB_NAME，MEDIA=$MEDIA_ROOT）"

# ── 1) 数据库：dump → 自检 → 原子改名（绝不留下"看起来成功实则半截"的文件）──
DUMP_TMP="$DB_DIR/waynote-$TODAY.dump.tmp"
DUMP_FINAL="$DB_DIR/waynote-$TODAY.dump"
sudo -n -u postgres pg_dump -Fc "$DB_NAME" > "$DUMP_TMP"
pg_restore --list "$DUMP_TMP" > /dev/null
chmod 600 "$DUMP_TMP"
mv -f "$DUMP_TMP" "$DUMP_FINAL"
echo "$PREFIX DB dump 完成：$DUMP_FINAL（$(du -h "$DUMP_FINAL" | cut -f1)）"

# ── 2) media：硬链接快照（未变化文件零额外空间；同日重跑退化为普通同步）──
if [ -d "$MEDIA_ROOT" ] && [ -n "$(ls -A "$MEDIA_ROOT" 2>/dev/null)" ]; then
  SNAP="$MEDIA_SNAP_DIR/media-$TODAY"
  PREV="$(readlink -f "$MEDIA_SNAP_DIR/current" 2>/dev/null || true)"
  if [ -n "$PREV" ] && [ -d "$PREV" ] && [ "$PREV" != "$SNAP" ]; then
    rsync -a --delete --link-dest="$PREV" "$MEDIA_ROOT/" "$SNAP/"
  else
    rsync -a --delete "$MEDIA_ROOT/" "$SNAP/"
  fi
  ln -sfn "$SNAP" "$MEDIA_SNAP_DIR/current"
  echo "$PREFIX media 快照完成：$SNAP（$(find "$SNAP" -type f | wc -l) 个文件）"
else
  echo "$PREFIX media 目录为空或不存在，跳过快照"
fi

# ── 3) 保留策略（先落新产物、再删旧；磁盘紧张时宁可少一份历史）──
find "$DB_DIR" -maxdepth 1 -name 'waynote-*.dump' -mtime +"$KEEP" -delete
ls -1dt "$MEDIA_SNAP_DIR"/media-* 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -rf

echo "$PREFIX == 备份完成（保留最近 $KEEP 份）"
