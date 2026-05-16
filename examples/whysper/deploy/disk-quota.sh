#!/bin/bash
# Whysper + vlog 磁盘 10G 巡检 - 超限删最老素材 + SeaTalk 告警
set -e

WHYSPER_DATA=/var/whysper-data
VLOG_DATA=/var/vlog-data
LIMIT_MB=10240   # 10G

usage_mb() { du -sm "$1" 2>/dev/null | awk '{print $1}'; }

prune_whysper() {
  # 删 90 天前的音频（保留 db 文本永久）
  find "$WHYSPER_DATA/audio" -type f -mtime +90 -delete 2>/dev/null
  # 若仍超限，按时间从旧到新删
  while [ "$(usage_mb $WHYSPER_DATA)" -gt $LIMIT_MB ]; do
    OLDEST=$(find "$WHYSPER_DATA/audio" "$WHYSPER_DATA/images" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | head -1 | awk '{print $2}')
    [ -z "$OLDEST" ] && break
    rm -f "$OLDEST"
  done
}

prune_vlog() {
  # 删 30 天前的成片
  find "$VLOG_DATA/output" -type f -mtime +30 -delete 2>/dev/null
  # 还超就删最老素材
  while [ "$(usage_mb $VLOG_DATA)" -gt $LIMIT_MB ]; do
    OLDEST=$(find "$VLOG_DATA" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | head -1 | awk '{print $2}')
    [ -z "$OLDEST" ] && break
    rm -f "$OLDEST"
  done
}

W_BEFORE=$(usage_mb $WHYSPER_DATA)
V_BEFORE=$(usage_mb $VLOG_DATA)

[ "$W_BEFORE" -gt $LIMIT_MB ] && prune_whysper
[ "$V_BEFORE" -gt $LIMIT_MB ] && prune_vlog

W_AFTER=$(usage_mb $WHYSPER_DATA)
V_AFTER=$(usage_mb $VLOG_DATA)

# 简单日志
echo "[$(date '+%F %T')] whysper: ${W_BEFORE}MB -> ${W_AFTER}MB | vlog: ${V_BEFORE}MB -> ${V_AFTER}MB" >> /var/log/disk-quota.log
