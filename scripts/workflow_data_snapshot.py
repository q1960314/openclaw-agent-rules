#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成数据循环快照清单（轻量级，可日常运行）。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)


def safe_latest_trade_date(parquet_path: Path) -> str | None:
    try:
        df = pd.read_parquet(parquet_path, columns=['trade_date'])
        if df.empty:
            return None
        return str(df['trade_date'].astype(str).max()).replace('-', '')
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--code-root', required=True)
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='data_snapshot')
    parser.add_argument('--sample-size', type=int, default=10)
    args = parser.parse_args()

    code_root = Path(args.code_root)
    cycle_dir = Path(args.cycle_dir)

    stock_root = code_root / 'data_all_stocks'
    stock_dirs = sorted([p for p in stock_root.iterdir() if p.is_dir()]) if stock_root.exists() else []

    samples: List[Dict] = []
    for stock_dir in stock_dirs[: max(1, args.sample_size)]:
        daily_file = stock_dir / 'daily.parquet'
        samples.append({
            'ts_code': stock_dir.name,
            'daily_exists': daily_file.exists(),
            'daily_size_bytes': daily_file.stat().st_size if daily_file.exists() else 0,
            'latest_trade_date': safe_latest_trade_date(daily_file) if daily_file.exists() else None,
        })

    important_files = [
        code_root / 'data' / 'limit_list_d.parquet',
        code_root / 'data' / 'top_list.parquet',
        code_root / 'data' / 'hm_detail.parquet',
    ]
    file_manifest = []
    for f in important_files:
        file_manifest.append({
            'path': str(f),
            'exists': f.exists(),
            'size_bytes': f.stat().st_size if f.exists() else 0,
            'mtime': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S') if f.exists() else None,
        })

    payload = {
        'stage': args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'code_root': str(code_root),
        'stock_dir_count': len(stock_dirs),
        'sample_size': len(samples),
        'important_files': file_manifest,
        'samples': samples,
    }

    artifact_dir = cycle_dir / 'artifacts' / args.stage_id
    write_json(artifact_dir / 'data_snapshot.json', payload)

    md_lines = ['# Data Snapshot', '', f"- generated_at: {payload['generated_at']}", f"- stock_dir_count: {payload['stock_dir_count']}", '']
    md_lines.append('## Important Files')
    for item in file_manifest:
        md_lines.append(f"- {item['path']} | exists={item['exists']} | size={item['size_bytes']}")
    md_lines.append('')
    md_lines.append('## Samples')
    for s in samples:
        md_lines.append(f"- {s['ts_code']} | exists={s['daily_exists']} | latest={s['latest_trade_date']} | size={s['daily_size_bytes']}")
    (artifact_dir / 'data_snapshot.md').write_text('\n'.join(md_lines), encoding='utf-8')

    print(json.dumps({'stage': args.stage_id, 'stock_dir_count': len(stock_dirs), 'sample_size': len(samples)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
