# 生态自动循环 MVP

## 已落地内容

### 1. 工作流配置
- `config/ecosystem_workflow.json`

### 2. 工作流引擎
- `scripts/workflow_engine.py`

支持：
- 初始化循环
- 运行循环
- 按阶段执行
- task / cycle 状态持久化
- lock 防重入
- logs / artifacts / reports 归档
- live heartbeat / live_status 持续写出
- latest_status / latest_cycles / events 全局状态面板

### 3. 每日研究闭环
- `scripts/run_daily_research_cycle.sh`

阶段：
1. `preflight`
2. `data_validate`
3. `smoke_backtest`
4. `followup_ticket`
5. `queue_ticket`
6. `dispatch_ticket`
7. `summarize`
8. `notify_user`

### 4. 周度健康检查闭环
- `scripts/run_weekly_health_cycle.sh`

阶段：
1. `preflight`
2. `data_validate`
3. `health_check`
4. `followup_ticket`
5. `queue_ticket`
6. `dispatch_ticket`
7. `summarize`
8. `notify_user`

### 5. 报告与状态输出目录
- `traces/cycles/<cycle_type>/<cycle_id>/meta.json`
- `traces/cycles/<cycle_type>/<cycle_id>/tasks/*.json`
- `traces/cycles/<cycle_type>/<cycle_id>/artifacts/*`
- `traces/cycles/<cycle_type>/<cycle_id>/reports/*`
- `traces/cycles/<cycle_type>/<cycle_id>/logs/*`

---

## 当前设计原则

### 自动推进
- 预检查
- 数据校验
- 冒烟回测
- 周度健康检查
- 汇总与归档

### 暂不自动生效
- 正式代码合并
- 正式参数替换
- 交易动作
- 生产配置变更

---

## 手动运行示例

### 查看状态
```bash
/home/admin/miniconda3/envs/vnpy_env/bin/python \
  /home/admin/.openclaw/workspace/master/scripts/workflow_engine.py \
  status
```

### dry-run 每日闭环
```bash
/home/admin/miniconda3/envs/vnpy_env/bin/python \
  /home/admin/.openclaw/workspace/master/scripts/workflow_engine.py \
  run --cycle-type daily_research --dry-run
```

### 只跑到数据校验
```bash
/home/admin/miniconda3/envs/vnpy_env/bin/python \
  /home/admin/.openclaw/workspace/master/scripts/workflow_engine.py \
  run --cycle-type daily_research --stop-after data_validate
```

### 执行每日闭环
```bash
/home/admin/.openclaw/workspace/master/scripts/run_daily_research_cycle.sh
```

### 执行周度闭环
```bash
/home/admin/.openclaw/workspace/master/scripts/run_weekly_health_cycle.sh
```

### 查看统一状态面板
```bash
/home/admin/.openclaw/workspace/master/scripts/check_workflow_status.sh
```

### 实时观察状态变化
```bash
/home/admin/.openclaw/workspace/master/scripts/watch_workflow.sh 5
```

### 安装 cron（已可直接使用）
```bash
/home/admin/.openclaw/workspace/master/scripts/install_ecosystem_cron.sh
```

### 全局状态文件
- `reports/workflow/state/latest_status.json`
- `reports/workflow/state/latest_cycles.json`
- `reports/workflow/state/events.jsonl`

### 队列目录
- `reports/workflow/queue/pending`
- `reports/workflow/queue/dispatched`
- `reports/workflow/queue/failed`
- `reports/workflow/queue/archive`

### 清理任务
```bash
/home/admin/.openclaw/workspace/master/scripts/run_workflow_cleanup.sh
```

---

## 下一步建议

1. 接入异常通知桥（失败后自动通知 master / 用户）
2. 接入 agent 模式阶段（当前为 command 模式）
3. 接入 OpenCode 到 coder 执行链
4. 把优化工单从 weekly_health 自动派生到下一轮 cycle
