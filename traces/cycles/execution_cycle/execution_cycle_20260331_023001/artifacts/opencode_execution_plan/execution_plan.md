# Execution Plan

## 1. Scope
Focus on the four specified files for execution plan:
- `/data/agents/master/modules/strategy_core.py` - Core strategy logic
- `/data/agents/master/vnpy_backtest/backtest_engine.py` - Backtesting engine
- `/data/agents/master/plugins/strategy_ensemble.py` - Strategy ensemble plugin
- `/data/agents/master/modules/risk_engine.py` - Risk management engine

## 2. File Order
1. `modules/risk_engine.py` - First, establish risk boundaries and controls
2. `modules/strategy_core.py` - Second, implement core strategy logic with risk awareness
3. `plugins/strategy_ensemble.py` - Third, integrate strategies into ensemble framework
4. `vnpy_backtest/backtest_engine.py` - Fourth, validate through backtesting

## 3. Minimal Changes
- **risk_engine.py**: Add risk validation hooks for strategy execution, implement circuit breaker logic
- **strategy_core.py**: Connect to risk_engine validation, implement safety checks before execution
- **strategy_ensemble.py**: Update to use validated strategy and risk interfaces
- **backtest_engine.py**: Add integration points to validate strategies against risk constraints

## 4. Validation
- Unit tests for each component after modification
- Integration tests between risk_engine and strategy components
- Backtest validation using historical data to confirm risk controls work
- Dry-run execution in controlled environment

## 5. Approval Gates
- Test-expert validation of risk controls
- Strategy-expert review of core logic changes
- Backtest-engine verification of performance impact
- Risk-officer approval of new circuit breakers