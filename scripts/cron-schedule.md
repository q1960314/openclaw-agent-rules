# 24 小时循环定时任务配置

## Crontab 配置

```bash
# 编辑 crontab
crontab -e

# 添加以下任务（Asia/Shanghai 时区）
```

### 定时任务列表

| 时间 | Cron 表达式 | 任务 | 脚本命令 |
|------|-----------|------|----------|
| 00:00 | `0 0 * * *` | 日切归档 | `/home/admin/.openclaw/agents/master/scripts/daily-cycle.sh archive` |
| 02:00 | `0 2 * * *` | 数据更新 | `/home/admin/.openclaw/agents/master/scripts/daily-cycle.sh data-update` |
| 06:00 | `0 6 * * *` | 盘前准备 | `/home/admin/.openclaw/agents/master/scripts/daily-cycle.sh pre-market` |
| 08:00 | `0 8 * * *` | 每日选股 | `/home/admin/.openclaw/agents/master/scripts/daily-cycle.sh daily-stock-pick` |
| 09:30 | `30 9 * * 1-5` | 开盘监控（工作日） | `/home/admin/.openclaw/agents/master/scripts/daily-cycle.sh market-open-monitor` |
| 12:00 | `0 12 * * 1-5` | 午间检查（工作日） | `/home/admin/.openclaw/agents/master/scripts/daily-cycle.sh noon-check` |
| 15:00 | `0 15 * * 1-5` | 收盘检查（工作日） | `/home/admin/.openclaw/agents/master/scripts/daily-cycle.sh market-close-check` |
| 17:00 | `0 17 * * *` | 回测验证 | `/home/admin/.openclaw/agents/master/scripts/daily-cycle.sh backtest` |
| 19:00 | `0 19 * * *` | 策略优化 | `/home/admin/.openclaw/agents/master/scripts/daily-cycle.sh strategy-optimize` |
| 21:00 | `0 21 * * *` | 代码审查 | `/home/admin/.openclaw/agents/master/scripts/daily-cycle.sh code-review` |
| 23:00 | `0 23 * * *` | 每日总结 | `/home/admin/.openclaw/agents/master/scripts/daily-cycle.sh daily-summary` |
| 23:30 | `30 23 * * *` | 知识库沉淀 | `/home/admin/.openclaw/agents/master/scripts/daily-cycle.sh kb-sync` |

---

## 输出物位置

| 任务 | 输出文件 | 位置 |
|------|----------|------|
| 日切归档 | `archive/YYYYMMDD_archive.md` | `/home/admin/.openclaw/agents/master/traces/archive/` |
| 数据更新 | `data_update_report.md` | `/home/admin/.openclaw/agents/master/traces/` |
| 盘前准备 | `pre_market_report.md` | `/home/admin/.openclaw/agents/master/traces/` |
| 每日选股 | `daily_stock_pick.md` | `/home/admin/.openclaw/agents/master/traces/` |
| 开盘监控 | `market_open_monitor.md` | `/home/admin/.openclaw/agents/master/traces/` |
| 午间检查 | `noon_check_report.md` | `/home/admin/.openclaw/agents/master/traces/` |
| 收盘检查 | `market_close_check.md` | `/home/admin/.openclaw/agents/master/traces/` |
| 回测验证 | `backtest_report.md` | `quant-research-knowledge-base/回测报告库/` |
| 策略优化 | `strategy_optimization.md` | `quant-research-knowledge-base/策略库/` |
| 代码审查 | `code_review_report.md` | `quant-research-knowledge-base/代码版本库/` |
| 每日总结 | `daily_summary_YYYYMMDD.md` | `/home/admin/.openclaw/agents/master/traces/` |
| 知识库沉淀 | 更新记录 | `quant-research-knowledge-base/` 各分类目录 |

---

## 用户通知机制

### 每日总结推送（23:00）
- **渠道**：webchat / 飞书
- **内容**：核心结论、关键指标、异常告警
- **格式**：简洁版（300 字以内）+ 详细版链接

### 异常告警（实时）
- **触发条件**：发现高优先级风险
- **渠道**：飞书 + 邮件
- **内容**：异常点、风险等级、排查建议

---

## 启用/禁用

### 启用全部任务
```bash
# 添加 crontab
crontab -e
# 粘贴上面的 cron 表达式
```

### 禁用全部任务
```bash
# 注释掉所有 cron 表达式（行首加 #）
crontab -e
```

### 仅启用核心任务
```bash
# 保留以下任务：
0 8 * * *    # 每日选股
0 17 * * *   # 回测验证
0 23 * * *   # 每日总结
30 23 * * *  # 知识库沉淀
```

---

## 监控与调试

### 查看执行日志
```bash
# 实时查看
tail -f /home/admin/.openclaw/agents/master/traces/daily-cycle.log

# 查看今日日志
cat /home/admin/.openclaw/agents/master/traces/daily-cycle.log | grep $(date +%Y-%m-%d)
```

### 手动执行任务
```bash
# 测试每日选股任务
/home/admin/.openclaw/agents/master/scripts/daily-cycle.sh daily-stock-pick

# 测试每日总结任务
/home/admin/.openclaw/agents/master/scripts/daily-cycle.sh daily-summary
```

### 检查 crontab 状态
```bash
# 查看已配置的任务
crontab -l

# 检查 cron 服务状态
systemctl --user status cron
```

---

## 注意事项

1. **时区**：所有时间均为 Asia/Shanghai (GMT+8)
2. **工作日任务**：开盘监控/午间检查/收盘检查仅在周一至周五执行
3. **日志保留**：日志保留 30 天，自动清理
4. **失败重试**：任务失败自动重试 2 次，连续失败发送告警
5. **资源限制**：单个任务执行时间不超过 30 分钟
