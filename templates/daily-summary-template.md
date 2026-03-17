# 每日总结报告

**日期**：{{DATE}}  
**生成时间**：{{TIMESTAMP}}  
**循环周期**：24 小时

---

## 📊 今日核心指标

| 指标 | 数值 | 环比 |
|------|------|------|
| 执行任务数 | {{TASK_COUNT}} | {{TASK_COUNT_CHANGE}} |
| 选股数量 | {{STOCK_PICK_COUNT}} | - |
| 回测次数 | {{BACKTEST_COUNT}} | - |
| 代码修改 | {{CODE_CHANGE_COUNT}} | - |
| 知识库更新 | {{KB_UPDATE_COUNT}} | - |
| Token 消耗 | {{TOKEN_USAGE}} | {{TOKEN_CHANGE}} |

---

## ✅ 已完成任务

| 时间 | 任务 | 状态 | 输出物 |
|------|------|------|--------|
| 00:00 | 日切归档 | {{ARCHIVE_STATUS}} | `traces/archive/{{DATE}}_archive.md` |
| 02:00 | 数据更新 | {{DATA_STATUS}} | `traces/data_update_report.md` |
| 06:00 | 盘前准备 | {{PREMARKET_STATUS}} | `traces/pre_market_report.md` |
| 08:00 | 每日选股 | {{STOCKPICK_STATUS}} | `traces/daily_stock_pick.md` |
| 09:30 | 开盘监控 | {{OPENMON_STATUS}} | `traces/market_open_monitor.md` |
| 12:00 | 午间检查 | {{NOON_STATUS}} | `traces/noon_check_report.md` |
| 15:00 | 收盘检查 | {{CLOSE_STATUS}} | `traces/market_close_check.md` |
| 17:00 | 回测验证 | {{BACKTEST_STATUS}} | `回测报告库/{{DATE}}_backtest.md` |
| 19:00 | 策略优化 | {{STRATEGY_STATUS}} | `策略库/{{DATE}}_optimization.md` |
| 21:00 | 代码审查 | {{CODEREVIEW_STATUS}} | `代码版本库/{{DATE}}_review.md` |
| 23:00 | 每日总结 | ✅ 执行中 | 本报告 |
| 23:30 | 知识库沉淀 | ⏳ 待执行 | - |

---

## 📈 策略表现

### 今日选股
```
选股数量：{{STOCK_COUNT}} 只
行业分布：{{INDUSTRY_DIST}}
平均预期收益：{{EXPECTED_RETURN}}%
```

### 回测结果
```
回测周期：{{BACKTEST_PERIOD}}
年化收益率：{{ANNUAL_RETURN}}%
最大回撤：{{MAX_DRAWDOWN}}%
夏普比率：{{SHARPE_RATIO}}
胜率：{{WIN_RATE}}%
```

---

## ⚠️ 异常与告警

| 时间 | 异常点 | 风险等级 | 处理状态 |
|------|--------|----------|----------|
| {{ALERT_TIME}} | {{ALERT_ITEM}} | {{RISK_LEVEL}} | {{ALERT_STATUS}} |

**今日告警总数**：{{ALERT_COUNT}}  
**高优先级**：{{HIGH_PRIORITY_COUNT}}  
**已解决**：{{RESOLVED_COUNT}}

---

## 📚 知识库更新

| 分类 | 更新内容 | 智能体 |
|------|----------|--------|
| 代码版本库 | {{CODE_VERSION_UPDATE}} | 代码守护者 |
| 策略库 | {{STRATEGY_UPDATE}} | 策略专家 |
| 参数池 | {{PARAM_UPDATE}} | 参数进化智能体 |
| 回测报告库 | {{BACKTEST_UPDATE}} | 回测引擎智能体 |
| 避坑指南 | {{PITFALL_UPDATE}} | 测试专家 |
| 规则手册 | {{RULE_UPDATE}} | 文档管理员 |
| 智能体能力库 | {{CAPABILITY_UPDATE}} | 各智能体 |

---

## 💰 成本统计

| 项目 | 用量 | 成本 |
|------|------|------|
| Token 输入 | {{TOKEN_INPUT}} | ¥{{COST_INPUT}} |
| Token 输出 | {{TOKEN_OUTPUT}} | ¥{{COST_OUTPUT}} |
| API 调用 | {{API_CALLS}} | ¥{{COST_API}} |
| **合计** | - | **¥{{TOTAL_COST}}** |

---

## 📅 次日计划

| 时间 | 任务 | 优先级 | 备注 |
|------|------|--------|------|
| 08:00 | 每日选股 | P0 | 例行任务 |
| 17:00 | 回测验证 | P0 | 例行任务 |
| 19:00 | 策略优化 | P1 | {{STRATEGY_PLAN}} |
| 21:00 | 代码审查 | P1 | {{CODE_PLAN}} |

---

## 🎯 优化停止标准监控

| 指标 | 当前值 | 目标值 | 状态 |
|------|--------|--------|------|
| 年化收益率 | {{ANNUAL_RETURN}}% | ≥30% | {{ANNUAL_STATUS}} |
| 最大回撤 | {{MAX_DRAWDOWN}}% | ≤15% | {{DRAWDOWN_STATUS}} |
| 夏普比率 | {{SHARPE_RATIO}} | ≥2.5 | {{SHARPE_STATUS}} |
| 样本外胜率 | {{WIN_RATE}}% | ≥58% | {{WINRATE_STATUS}} |
| 代码运行 | {{CODE_STATUS}} | 无报错 | {{CODE_HEALTH}} |
| 6 大优化域 | {{RISK_COUNT}} 个风险 | 0 个高中风险 | {{RISK_STATUS}} |

**综合状态**：{{OVERALL_STATUS}}  
（✅ 全部达标 / ⚠️ 部分达标 / ❌ 未达标）

---

## 📝 备注

{{REMARKS}}

---

**报告生成**：master-quant  
**复核**：文档管理员  
**下次更新**：{{NEXT_UPDATE}}

【合规提示】本内容仅为量化研究回测使用，不构成任何投资建议，投资有风险，入市需谨慎
