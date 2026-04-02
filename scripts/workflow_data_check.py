#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日数据校验脚本（面向 parquet 数据主干）。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd


REQUIRED_PARQUET_FILES = [
    "data/limit_list_d.parquet",
]

SAMPLE_STOCKS = 20
MAX_ALLOWED_DATE_SPREAD = 2  # 最新日期允许最多相差 2 天


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)


def normalize_trade_date(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.replace("-", "")
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", required=True)
    parser.add_argument("--cycle-dir", required=True)
    parser.add_argument("--stage-id", default="data_validate")
    args = parser.parse_args()

    code_root = Path(args.code_root)
    cycle_dir = Path(args.cycle_dir)

    results: Dict[str, object] = {
        "stage": args.stage_id,
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "required_files": [],
        "samples": [],
        "warnings": [],
        "errors": [],
        "summary": {},
    }

    for rel in REQUIRED_PARQUET_FILES:
        path = code_root / rel
        ok = path.exists()
        results["required_files"].append({"path": str(path), "exists": ok})
        if not ok:
            results["errors"].append(f"缺少必需文件: {path}")

    stock_root = code_root / "data_all_stocks"
    stock_dirs = sorted([p for p in stock_root.iterdir() if p.is_dir()]) if stock_root.exists() else []
    latest_dates: List[str] = []

    for stock_dir in stock_dirs[:SAMPLE_STOCKS]:
        daily_file = stock_dir / "daily.parquet"
        sample = {
            "ts_code": stock_dir.name,
            "daily_file": str(daily_file),
            "exists": daily_file.exists(),
            "rows": 0,
            "latest_trade_date": None,
        }
        if daily_file.exists():
            try:
                df = pd.read_parquet(daily_file, columns=["trade_date"])
                sample["rows"] = int(len(df))
                if not df.empty:
                    latest = normalize_trade_date(df["trade_date"].astype(str).max())
                    sample["latest_trade_date"] = latest
                    latest_dates.append(latest)
            except Exception as e:
                sample["error"] = str(e)
                results["errors"].append(f"读取失败 {daily_file}: {e}")
        else:
            results["warnings"].append(f"样本缺少 daily.parquet: {daily_file}")
        results["samples"].append(sample)

    latest_global = None
    spread_days = None
    if latest_dates:
        latest_dates_sorted = sorted(latest_dates)
        latest_global = latest_dates_sorted[-1]
        try:
            dt_min = datetime.strptime(latest_dates_sorted[0], "%Y%m%d")
            dt_max = datetime.strptime(latest_dates_sorted[-1], "%Y%m%d")
            spread_days = (dt_max - dt_min).days
            if spread_days > MAX_ALLOWED_DATE_SPREAD:
                results["warnings"].append(
                    f"样本最新交易日分布偏差较大: min={latest_dates_sorted[0]} max={latest_dates_sorted[-1]} spread={spread_days}天"
                )
        except Exception:
            pass

    limit_max_date = None
    limit_file = code_root / "data" / "limit_list_d.parquet"
    if limit_file.exists():
        try:
            limit_df = pd.read_parquet(limit_file, columns=["trade_date"])
            if not limit_df.empty:
                limit_max_date = normalize_trade_date(limit_df["trade_date"].astype(str).max())
        except Exception as e:
            results["errors"].append(f"读取 limit_list_d.parquet 失败: {e}")

    if latest_global and limit_max_date and latest_global != limit_max_date:
        results["warnings"].append(
            f"样本股票最新日({latest_global}) 与涨停文件最新日({limit_max_date}) 不一致"
        )

    results["summary"] = {
        "sample_stock_count": len(results["samples"]),
        "latest_sample_trade_date": latest_global,
        "limit_list_latest_trade_date": limit_max_date,
        "sample_trade_date_spread_days": spread_days,
        "warnings": len(results["warnings"]),
        "errors": len(results["errors"]),
        "status": "ok" if not results["errors"] else "failed",
    }

    artifact = cycle_dir / "artifacts" / args.stage_id / "data_check.json"
    write_json(artifact, results)
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    return 0 if not results["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
