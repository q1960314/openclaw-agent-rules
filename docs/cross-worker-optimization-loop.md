# Cross Worker Optimization Loop

This loop orchestrates an adaptive multi-worker optimization chain.

## Current Flow
1. strategy-expert
2. baseline backtest-engine
3. stop criteria evaluation
4. adaptive next-step selection based on failed checks + richer expert handoff hints:
   - factor-miner for weak return / weak Sharpe when factor-oriented handoff remains strongest
   - parameter-evolver for drawdown/risk tuning or when handoff points to threshold/guardrail work
   - strategy-expert when broader logic revision is needed or when handoff points back to strategy redesign
5. backtest-engine re-validation
6. repeat until stop criteria pass or `max_adjust_rounds` is exhausted

## Entry Script
- `scripts/runtime/cross_worker_optimization_loop.py`

## Current Goal
Prove the ecosystem can do more than fixed sequences: it can look at threshold failures, consume richer expert handoff hints from research artifacts, choose the next worker accordingly, write those decision reasons into trace/report outputs, and expose the resulting adaptive-routing summary to runtime/stage-card visibility.
