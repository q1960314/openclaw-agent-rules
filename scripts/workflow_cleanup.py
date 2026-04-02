#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工作流日常清理：修复 stale cycle、清理旧 queue、归档旧状态。"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

QUEUE_ROOT = Path('/home/admin/.openclaw/workspace/master/reports/workflow/queue')
PENDING = QUEUE_ROOT / 'pending'
DISPATCHED = QUEUE_ROOT / 'dispatched'
DONE = QUEUE_ROOT / 'done'
FAILED = QUEUE_ROOT / 'failed'
ARCHIVE = QUEUE_ROOT / 'archive'
for d in [PENDING, DISPATCHED, DONE, FAILED, ARCHIVE]:
    d.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=3)
    args = parser.parse_args()

    cutoff = datetime.now() - timedelta(days=args.days)
    moved: List[str] = []

    for bucket in [DISPATCHED, DONE, FAILED]:
        for f in bucket.glob('*.json'):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                target = ARCHIVE / f.name
                shutil.move(str(f), str(target))
                moved.append(str(target))

    result = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'archived_count': len(moved),
        'archived_files': moved,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
