#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据 data_check 结果计算轻量级数据质量评分。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict


def load_json(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def grade(score: int) -> str:
    if score >= 90:
        return 'A'
    if score >= 80:
        return 'B'
    if score >= 70:
        return 'C'
    if score >= 60:
        return 'D'
    return 'F'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle-dir', required=True)
    parser.add_argument('--stage-id', default='data_quality_score')
    args = parser.parse_args()

    cycle_dir = Path(args.cycle_dir)
    data_check_path = cycle_dir / 'artifacts' / 'data_validate' / 'data_check.json'
    if not data_check_path.exists():
        raise SystemExit(f'缺少 data_check.json: {data_check_path}')

    payload = load_json(data_check_path)
    summary = payload.get('summary', {})
    warnings = int(summary.get('warnings', 0) or 0)
    errors = int(summary.get('errors', 0) or 0)
    spread = summary.get('sample_trade_date_spread_days')
    spread = 0 if spread is None else int(spread)
    sample_count = int(summary.get('sample_stock_count', 0) or 0)

    score = 100
    score -= errors * 25
    score -= warnings * 5
    if spread > 2:
        score -= min(20, (spread - 2) * 3)
    if sample_count < 10:
        score -= 10
    score = max(0, min(100, score))

    result = {
        'stage': args.stage-id if False else args.stage_id,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'score': score,
        'grade': grade(score),
        'errors': errors,
        'warnings': warnings,
        'sample_trade_date_spread_days': spread,
        'sample_stock_count': sample_count,
        'status': 'pass' if score >= 80 and errors == 0 else 'review',
    }

    artifact_dir = cycle_dir / 'artifacts' / args.stage_id
    write_json(artifact_dir / 'data_quality_score.json', result)
    (artifact_dir / 'data_quality_score.md').write_text(
        '\n'.join([
            '# Data Quality Score',
            '',
            f"- score: {result['score']}",
            f"- grade: {result['grade']}",
            f"- status: {result['status']}",
            f"- errors: {result['errors']}",
            f"- warnings: {result['warnings']}",
            f"- spread_days: {result['sample_trade_date_spread_days']}",
            f"- sample_stock_count: {result['sample_stock_count']}",
        ]),
        encoding='utf-8'
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
