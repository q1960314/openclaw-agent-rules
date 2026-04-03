I understand I'm in plan mode and need to create a comprehensive execution plan without making any changes. Let me analyze the provided diagnostic information and focus on the specified files to create a build-ready plan.
It looks like the risk_engine.py file doesn't exist. Let me search for any risk-related files in the codebase:
Now let me search for any other configuration files or parameters that might be relevant to the strategy and risk management:
Now I have a good understanding of the system. Based on the diagnostic reports and code files, I'll create a comprehensive execution plan to address the issues identified. The main problems are poor performance due to inappropriate parameters for current market conditions, particularly with stop-loss thresholds and strategy weights. Let me create a plan focusing on the key areas that need improvement:

# Execution Plan

## 1. Scope

Focus on improving the strategy performance by adjusting parameters and logic based on the diagnostic findings:
- **Primary Issue**: Poor performance with total_return=-0.1715, sharpe=-4.4467, max_drawdown=0.1693
- **Root Cause**: Parameter misalignment with current market conditions, inadequate risk controls
- **Files to Modify**: strategy_core.py, backtest_engine.py, strategy_ensemble.py, config_manager.py

## 2. File Order

1. **modules/config_manager.py** - Update default parameters for better risk management
2. **vnpy_backtest/backtest_engine.py** - Enhance risk controls and dynamic parameter adjustment
3. **plugins/strategy_ensemble.py** - Improve strategy fusion with market-adaptive weights
4. **modules/strategy_core.py** - Strengthen strategy filtering and scoring mechanisms

## 3. Minimal Changes

### Phase 1: Configuration Updates
- Adjust default stop-loss from 6% to 4.5% (tightened for better risk control)
- Reduce default position size from 20% to 15% to limit individual stock exposure
- Enable dynamic market regime detection with adjusted weights
- Update strategy-specific thresholds for current market conditions

### Phase 2: Backtesting Engine Enhancement
- Add market regime detection to adjust parameters dynamically
- Implement tighter drawdown controls with early warning systems
- Enhance the stop-loss mechanism to be more responsive to market volatility

### Phase 3: Strategy Ensemble Optimization
- Improve market regime detection algorithm
- Add adaptive weight adjustment based on recent performance
- Enhance risk management with dynamic position sizing

### Phase 4: Core Strategy Refinement
- Add market condition awareness to strategy filtering
- Enhance scoring system to account for current market volatility
- Strengthen pre-filtering to eliminate weak candidates

## 4. Validation

1. **Unit Testing**: Test individual components after each modification
2. **Parameter Sensitivity**: Test stop-loss levels (-3%, -4.5%, -6%) and position sizes (10%, 15%, 20%)
3. **Rolling Window Tests**: Run 30/60/90 day rolling backtests to verify stability
4. **Market Regime Tests**: Validate performance across different market conditions
5. **Risk Metrics**: Confirm Sharpe ratio > 0.5, max_drawdown < 12%, positive returns

## 5. Approval Gates

- [ ] Parameter updates reviewed and approved by master-quant
- [ ] Backtesting shows improved Sharpe ratio (>0.5) and reduced drawdown (<12%)
- [ ] Rolling window tests confirm parameter stability (no overfitting)
- [ ] Market regime adaptation works across different conditions
- [ ] Final approval for production deployment

This plan addresses the core issues identified by the diagnostic reports:
- **Strategy Expert**: Addresses market environment mismatch with dynamic parameters
- **Parameter Evolver**: Optimizes stop-loss, position sizing, and risk controls  
- **Backtest Engine**: Improves validation and adds market-aware adjustments

The changes will be conservative and focused on risk management improvements rather than complete strategy overhauls, aligning with the diagnostic recommendations.