#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""周度健康检查：训练段 vs 测试段。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/data/agents/master")

from vnpy_backtest import VnpyDataLoader, PortfolioStrategy, BacktestEngine  # type: ignore
from vnpy_backtest.health_check import StrategyHealthChecker  # type: ignore
from fetch_data_optimized import StrategyCore  # type: ignore


USE_HISTORY = {
    "缩量潜伏策略": True,
}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)


def run_segment(strategy_type: str, trade_dates):
    loader = VnpyDataLoader()
    strategy_core = StrategyCore(strategy_type)
    strategy = PortfolioStrategy(
        strategy_core=strategy_core,
        strategy_type=strategy_type,
        config={"min_score": 10, "top_n": 3}
    )
    engine = BacktestEngine(strategy=strategy, strategy_type=strategy_type)
    result = engine.run(trade_dates, loader, use_history_data=USE_HISTORY.get(strategy_type, False))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", required=True)
    parser.add_argument("--cycle-dir", required=True)
    parser.add_argument("--stage-id", default="health_check")
    parser.add_argument("--strategy", default="打板策略")
    args = parser.parse_args()

    cycle_dir = Path(args.cycle_dir)
    strategy_type = args.strategy

    loader = VnpyDataLoader()
    all_dates = loader.get_trade_dates("2023-01-01", datetime.now().strftime("%Y-%m-%d"))
    if len(all_dates) < 240:
        raise SystemExit("交易日不足 240 天，无法执行周度健康检查")

    recent = all_dates[-240:]
    train_dates = recent[:120]
    test_dates = recent[120:]

    train_result = run_segment(strategy_type, train_dates)
    test_result = run_segment(strategy_type, test_dates)

    checker = StrategyHealthChecker()
    report = checker.full_health_check(train_result=train_result, test_result=test_result)

    payload = {
        "stage": args.stage_id,
        "executed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "strategy_type": strategy_type,
        "train_range": [train_dates[0], train_dates[-1]],
        "test_range": [test_dates[0], test_dates[-1]],
        "train_result": train_result,
        "test_result": test_result,
        "health_report": report,
    }

    artifact_dir = cycle_dir / "artifacts" / args.stage_id
    write_json(artifact_dir / "weekly_health.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
