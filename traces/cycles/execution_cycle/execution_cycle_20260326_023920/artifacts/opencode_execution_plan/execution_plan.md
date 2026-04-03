I understand you want me to create an execution plan based on the diagnostic reports, and I'm in READ-ONLY mode. Let me analyze the files and create a comprehensive plan.
Let me check if the risk engine exists in another location:
Now let me run an explore agent to better understand the codebase structure and the diagnostic findings:
# Execution Plan

## 1. Scope
Based on the diagnostic reports and code analysis, focus on the four critical files:
- `/data/agents/master/modules/strategy_core.py` - Strategy logic adjustments
- `/data/agents/master/vnpy_backtest/backtest_engine.py` - Parameter and risk adjustments  
- `/data/agents/master/plugins/strategy_ensemble.py` - Market regime and weight adjustments
- `/data/agents/master/vnpy_backtest/risk_engine.py` - Risk management enhancements

The main issues identified are: poor parameter configuration (causing Sharpe -4.45, max drawdown 16.93%), lack of market regime adaptation, and insufficient risk controls.

## 2. File Order
1. **strategy_core.py** - First, adjust strategy thresholds and scoring logic to be more adaptive
2. **risk_engine.py** - Second, enhance risk controls to prevent excessive losses
3. **backtest_engine.py** - Third, adjust trading parameters (stop loss/profit, position sizing)
4. **strategy_ensemble.py** - Fourth, improve market regime detection and strategy weighting

## 3. Minimal Changes
1. **strategy_core.py**: Add market regime awareness to scoring, adjust strategy-specific pass scores based on volatility
2. **risk_engine.py**: Enhance VaR calculations, add account drawdown limits (reduce from 15% to 12%), implement position sizing based on Kelly criterion
3. **backtest_engine.py**: Tighten stop loss from 6% to 4%, reduce position size from 20% to 15%, add volatility-based adjustments
4. **strategy_ensemble.py**: Improve market regime detection algorithm, adjust strategy weights based on market conditions

## 4. Validation
1. Run immediate parameter sensitivity tests on stop loss rates (-3% to -6% range)
2. Execute 30-day rolling backtest with new parameters against the failing period
3. Test risk controls with stress scenarios simulating the current market conditions
4. Compare Sharpe ratio, max drawdown, and total return metrics against baseline (-0.1715, -4.4467, 0.1693)

## 5. Approval Gates
- **Gate 1**: Parameter adjustments must pass unit tests and basic sanity checks
- **Gate 2**: Risk enhancements must reduce theoretical maximum drawdown below 12%
- **Gate 3**: Backtested performance must show improved Sharpe ratio (>0) in recent 30-day window
- **Gate 4**: All changes must maintain backward compatibility with existing interfaces