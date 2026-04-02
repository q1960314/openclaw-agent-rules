# Stop Criteria

This document describes the current executable stop criteria used by optimization loops.

## Philosophy
Robustness first, not paper-optimal performance.

## Current Criteria Support
- `min_total_return`
- `min_sharpe_ratio`
- `max_drawdown`
- `min_total_trades`

## Runtime Module
- `scripts/runtime/stop_criteria.py`

## Current Use
- `cross_worker_optimization_loop.py` evaluates backtest artifacts against stop criteria
- if criteria are not met, the loop can continue parameter/backtest rounds until `max_param_rounds` is reached
- if criteria still are not met, final status becomes `threshold_not_met`
