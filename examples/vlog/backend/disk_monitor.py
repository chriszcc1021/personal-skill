#!/usr/bin/env python3
"""Disk monitor for vlog server.
- 检查 / 分区使用率
- > 70% 通过 OpenClaw delivery-queue 发 SeaTalk DM 给牛子哥的主 session
- 列出 /var/vlog-data/ 下最大的几个目录
建议 crontab 每 30 分钟跑一次。
"""
import json, os, shutil, time, urllib.request, subprocess
from pathlib import Path

THRESHOLD = 0.70
DATA = Path("/var/vlog-data")
ALERT_FILE = Path("/var/vlog-data/.last_disk_alert")
ALERT_COOLDOWN = 3600  # 1h between alerts

# This script runs on the server. It POSTs to the OpenClaw inbound webhook
# (provided by Garena gateway / openclaw inbound API) to reach chenchen.zhang@garena.com
SEATALK_WEBHOOK = os.environ.get(
    "VLOG_DISK_WEBHOOK",
    # Garena SeaTalk OpenClaw inbound endpoint - set via env
    ""
)


def human(n: int) -> str:
    for u in ["B", "K", "M", "G", "T"]:
        if n < 1024: return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}P"


def main():
    total, used, free = shutil.disk_usage("/")
    pct = used / total
    if pct < THRESHOLD:
        return

    # Cooldown
    if ALERT_FILE.exists():
        if time.time() - ALERT_FILE.stat().st_mtime < ALERT_COOLDOWN:
            return

    # Find top consumers under /var/vlog-data
    items = []
    for sub in DATA.glob("*"):
        if sub.is_dir():
            try:
                size = int(subprocess.check_output(["du", "-sb", str(sub)]).split()[0])
                items.append((sub.name, size))
            except Exception:
                pass
    items.sort(key=lambda x: -x[1])

    lines = [
        f"🚨 服务器磁盘报警",
        f"使用率 {pct*100:.0f}% ({human(used)} / {human(total)})",
        f"剩余 {human(free)}",
        "",
        "vlog 数据占用 (top 5):",
    ]
    for name, sz in items[:5]:
        lines.append(f"  /var/vlog-data/{name}: {human(sz)}")
    lines.append("")
    lines.append("建议清理: outputs / uploads 里 7 天前的文件")
    msg = "\n".join(lines)

    print(msg)
    if SEATALK_WEBHOOK:
        try:
            body = json.dumps({"text": msg}).encode()
            req = urllib.request.Request(SEATALK_WEBHOOK, data=body,
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(f"alert send fail: {e}")

    ALERT_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_FILE.touch()


if __name__ == "__main__":
    main()
