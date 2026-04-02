#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工作流预检查。"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--cycle-dir", required=True)
    parser.add_argument("--stage-id", default="preflight")
    args = parser.parse_args()

    code_root = Path(args.code_root)
    workspace_root = Path(args.workspace_root)
    cycle_dir = Path(args.cycle_dir)

    checks = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    add_check("code_root_exists", code_root.exists(), str(code_root))
    add_check("workspace_root_exists", workspace_root.exists(), str(workspace_root))
    add_check("python_env_exists", Path(sys.executable).exists(), sys.executable)
    add_check("required_fetch_file", (code_root / "fetch_data_optimized.py").exists(), str(code_root / "fetch_data_optimized.py"))
    add_check("required_backtest_package", (code_root / "vnpy_backtest").exists(), str(code_root / "vnpy_backtest"))
    add_check("required_data_dir", (code_root / "data_all_stocks").exists(), str(code_root / "data_all_stocks"))
    add_check("required_limit_file", (code_root / "data" / "limit_list_d.parquet").exists(), str(code_root / "data" / "limit_list_d.parquet"))
    add_check("git_repo_present", (code_root / ".git").exists(), str(code_root / ".git"))

    total_stocks = 0
    stock_dir = code_root / "data_all_stocks"
    if stock_dir.exists():
        total_stocks = len([p for p in stock_dir.iterdir() if p.is_dir()])

    payload = {
        "stage": args.stage_id,
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "python_executable": sys.executable,
        "code_root": str(code_root),
        "workspace_root": str(workspace_root),
        "total_stock_dirs": total_stocks,
        "checks": checks,
        "all_passed": all(item["ok"] for item in checks),
    }

    artifact = cycle_dir / "artifacts" / args.stage_id / "preflight.json"
    write_json(artifact, payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
