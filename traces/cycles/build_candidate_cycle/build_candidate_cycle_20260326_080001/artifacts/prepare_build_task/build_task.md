你现在在一个隔离 worktree 中执行中国A股量化回测/选股系统的 build 候选任务。

工作目录：/data/agents/worktrees/build_candidate_cycle_20260326_080001
原始代码仓：/data/agents/master
这是 research/backtest 范围，不是实盘，不允许修改实盘参数。

你必须优先只修改这些文件（如果文件不存在则跳过，不要扩展到无关目录）：
- /data/agents/master/modules/strategy_core.py
- /data/agents/master/vnpy_backtest/backtest_engine.py
- /data/agents/master/plugins/strategy_ensemble.py

专项 agent 已经完成诊断，execution plan 如下：
I understand I'm in plan mode and need to create a comprehensive execution plan without making any changes. Let me analyze the provided diagnostic information and focus on the specified files to create a build-ready plan.
It looks like the risk_engine.py file doesn't exist. Let me search for any risk-related files in the codebase:
Now let me search for any other configuration files or parameters that might be related to the strategies and backtesting:
Now I have analyzed all the key files. Based on the diagnostic information from the specialized agents, I can create a comprehensive execution plan. Let me also look for any fetch_data files that might contain parameter definitions:
Based on my analysis of the diagnostic information and the code files, I'll create a comprehensive execution plan for the build-ready code changes needed to address the performance issues identified by the specialized agents.

# Execution Plan

## 1. Scope
Address performance degradation in the quant system with specific focus on:
- Parameter tuning for strategy logic
- Risk management improvements
- Backtesting engine enhancements
- Multi-strategy ensemble optimizations

## 2. File Order
1. **modules/strategy_core.py** - Primary strategy logic adjustments and parameter fixes
2. **vnpy_backtest/backtest_engine.py** - Backtesting parameters and risk controls
3. **plugins/strategy_ensemble.py** - Ensemble strategy weights and risk management
4. **vnpy_backtest/risk_engine.py** - Risk engine parameter tuning

## 3. Minimal Changes

### modules/strategy_core.py
- Adjust strategy-specific parameters based on performance diagnostics
- Tune stop-loss and position sizing parameters
- Modify scoring thresholds to adapt to current market conditions
- Reduce overfitting by adjusting dynamic weight multipliers

### vnpy_backtest/backtest_engine.py 
- Adjust stop-loss rate from 0.06 to tighter 0.03-0.05 range
- Increase position diversification parameters
- Fine-tune slippage and commission parameters
- Improve market state detection logic

### plugins/strategy_ensemble.py
- Adjust dynamic weighting based on market regime detection
- Modify risk-adjusted position sizing logic
- Tune ensemble weights for current market conditions

### vnpy_backtest/risk_engine.py
- Tighten VaR limits and maximum drawdown thresholds
- Adjust Kelly criterion position sizing for current market volatility
- Enhance stress testing scenarios based on recent market conditions

## 4. Validation
- Run 30-day rolling backtest with optimized parameters
- Validate Sharpe ratio improvement (>0.5 target)
- Check maximum drawdown reduction (<12% target)
- Verify win rate and profit factor improvements
- Perform out-of-sample testing

## 5. Approval Gates
- Parameter optimization results verification
- Risk metrics compliance check
- Backtesting performance validation
- Ensemble strategy stability confirmation
- Final approval from master-quant before deployment

【强约束】
1. 本次不是写计划，必须进行真实代码修改
2. 至少要修改 1 个目标文件，并产生 git diff
3. 不扫描 backup/历史文件
4. 不修改无关目录
5. 不做实盘相关修改
6. 如果你判断当前不应该改代码，也要明确说明“为什么不能改”，但默认目标是做最小可验证改动

【执行要求】
请优先完成一个最小但真实的实现，例如：
- 调整 strategy_core 中和诊断直接相关的阈值/参数接入
- 或调整 backtest_engine / risk_engine 中直接相关的风险参数逻辑
- 或修正 strategy_ensemble 中与市场状态/权重有关的最小逻辑

结束后必须输出：
- 修改了哪些文件
- 做了什么改动
- 需要怎么验证
- 是否建议继续更大范围修改

如果没有实际改动，任务视为不合格。
