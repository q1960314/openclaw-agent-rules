你正在维护一个中国A股量化回测/选股系统，代码根目录为 /data/agents/master。

当前进入 optimization_cycle，来源工单如下：
- ticket_id: daily_research_20260325_224940::strategy_review
- category: strategy_review
- title: 每日闭环触发策略复核
- reason: smoke_backtest total_return=-0.1715, sharpe=-4.4467, max_drawdown=0.1693
- suggested_next_step: 复核近 60 交易日策略表现，确认是否需要进入周度优化/参数审查

请先做“计划模式”输出，不要直接进行高风险改动。你的任务：
1. 阅读与该工单最相关的代码文件
2. 判断这是参数问题、策略逻辑问题、数据问题，还是回测框架问题
3. 给出最小改动路径
4. 给出建议修改文件列表
5. 给出验证方案（test/backtest）
6. 明确哪些改动必须人工审批后才能执行

强约束：
- 只围绕中国A股量化回测/选股系统
- 不做实盘交易动作
- 不修改实盘参数
- 不删除大量文件
- 默认输出“计划”，不要直接 build

输出格式：
# OpenCode Optimization Plan
## 1. Diagnosis
## 2. Minimal Change Path
## 3. Files To Touch
## 4. Validation Plan
## 5. Approval Gates
