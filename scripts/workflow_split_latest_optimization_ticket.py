#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""找到最新 optimization ticket 并执行 split。"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path('/home/admin/.openclaw/workspace/master/reports/workflow/optimization_tickets')
SCRIPT = '/home/admin/.openclaw/workspace/master/scripts/workflow_split_optimization_ticket.py'
PYTHON = '/home/admin/miniconda3/envs/vnpy_env/bin/python'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    files = sorted(ROOT.glob('*.json'))
    if not files:
        raise SystemExit('未找到 optimization ticket')
    latest = files[-1]
    proc = subprocess.run([PYTHON, SCRIPT, '--ticket-file', str(latest)], check=False)
    raise SystemExit(proc.returncode)


if __name__ == '__main__':
    main()
