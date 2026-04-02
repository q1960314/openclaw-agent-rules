# Quant Backtest & Stock Selection Workspace

本仓库用于保存当前最新的量化回测与选股相关代码、规则文档与 Agent 协作说明。

## 当前重点内容
- 核心量化代码：`data/agents/master/`
- 环境依赖清单：`DEPENDENCIES_OVERVIEW.md`
- Agent 深化细则与职业灵魂：`AGENT_DEEP_RULES_AND_SOUL.md`
- 系统规则/身份文档：`AGENTS.md` `SOUL.md` `USER.md` `MEMORY.md`
- 设计与实现文档：`docs/`

## 当前核心代码模块
- `data/agents/master/modules/risk_engine.py`
- `data/agents/master/modules/strategy_core.py`
- `data/agents/master/plugins/strategy_ensemble.py`
- `data/agents/master/vnpy_backtest/backtest_engine.py`

## 说明
- 已通过 `.gitignore` 排除本地敏感配置、日志、缓存与运行态文件。
- 当前代码以回测/模拟执行为主，不包含自动实盘交易行为。
