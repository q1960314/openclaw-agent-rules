#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工作流冒烟回测入口。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/data/agents/master")

from vnpy_backtest import VnpyDataLoader, PortfolioStrategy, BacktestEngine  # type: ignore
from fetch_data_optimized import StrategyCore  # type: ignore


USE_HISTORY = {
    "缩量潜伏策略": True,
}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", required=True)
    parser.add_argument("--cycle-dir", required=True)
    parser.add_argument("--stage-id", default="smoke_backtest")
    parser.add_argument("--strategy", default="打板策略")
    parser.add_argument("--days", type=int, default=60)
    args = parser.parse_args()

    cycle_dir = Path(args.cycle_dir)
    days = max(10, args.days)
    strategy_type = args.strategy

    loader = VnpyDataLoader()
    all_dates = loader.get_trade_dates("2023-01-01", datetime.now().strftime("%Y-%m-%d"))
    if not all_dates:
        raise SystemExit("未获取到交易日，无法执行冒烟回测")

    trade_dates = all_dates[-days:]
    start_date, end_date = trade_dates[0], trade_dates[-1]

    strategy_core = StrategyCore(strategy_type)
    strategy = PortfolioStrategy(
        strategy_core=strategy_core,
        strategy_type=strategy_type,
        config={"min_score": 10, "top_n": 3}
    )
    engine = BacktestEngine(strategy=strategy, strategy_type=strategy_type)

    result = engine.run(
        trade_dates,
        loader,
        use_history_data=USE_HISTORY.get(strategy_type, False),
    )
    report_text = engine.generate_report(result)

    payload = {
        "stage": args.stage_id,
        "executed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "strategy_type": strategy_type,
        "days": days,
        "start_date": start_date,
        "end_date": end_date,
        "metrics": {
            "total_return": result.get("total_return"),
            "annual_return": result.get("annual_return"),
            "max_drawdown": result.get("max_drawdown"),
            "sharpe_ratio": result.get("sharpe_ratio"),
            "win_rate": result.get("win_rate"),
            "total_trades": result.get("total_trades"),
        },
        "engine": {
            "slippage_rate": getattr(engine, "slippage_rate", None),
            "high_open_buy_fail_rate": getattr(engine, "high_open_buy_fail_rate", None),
        },
        "report_text": report_text,
    }

    artifact_dir = cycle_dir / "artifacts" / args.stage_id
    write_json(artifact_dir / "smoke_backtest.json", payload)
    (artifact_dir / "smoke_backtest_report.md").write_text(report_text, encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
