#!/usr/bin/env python3
"""
Helper to install this automation as a system service / cron job.
Run:  python scheduler.py install   →  installs cron job (Linux/Mac)
      python scheduler.py remove    →  removes cron job
      python scheduler.py status    →  shows current cron jobs
"""
import sys, os, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable
MAIN = ROOT / "main.py"
LOG = ROOT / "data" / "dropship_hunter.log"


def install_cron():
    LOG.parent.mkdir(exist_ok=True)
    cron_line = f"0 8 * * * {PYTHON} {MAIN} >> {LOG} 2>&1"
    # Read existing crontab
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""
    if str(MAIN) in existing:
        print("✓ Cron job already installed.")
        return
    new_crontab = existing.rstrip() + "\n" + cron_line + "\n"
    proc = subprocess.run(["crontab", "-"], input=new_crontab, text=True)
    if proc.returncode == 0:
        print(f"✓ Cron job installed: runs at 08:00 daily")
        print(f"  Log file: {LOG}")
    else:
        print("✗ Failed to install cron job")


def remove_cron():
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0:
        print("No crontab found.")
        return
    lines = [l for l in result.stdout.splitlines() if str(MAIN) not in l]
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True)
    print("✓ Cron job removed.")


def status():
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        print("No cron jobs found.")
    else:
        print("Current crontab:")
        print(result.stdout)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"install": install_cron, "remove": remove_cron, "status": status}.get(cmd, status)()
