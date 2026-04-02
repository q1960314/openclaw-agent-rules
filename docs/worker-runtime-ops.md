# Worker Runtime Ops Guide

Updated: 2026-03-28 15:19 Asia/Shanghai

## 1. 当前定位

worker runtime scheduler 目前是：

> **最小持续运行化骨架**

它已经能：
- 单次巡检
- 周期循环巡检
- 输出 health / recovery / lifecycle dashboards
- 输出 latest cycle state
- 输出 scheduler events

但它还不是：
- 完整 daemon
- systemd/supervisord 托管服务
- 长期无人值守成熟系统

---

## 2. 常用命令

### 2.1 单次巡检
```bash
bash scripts/run_worker_runtime_scheduler.sh run-once --max-age-minutes 30
```

### 2.2 周期循环
```bash
bash scripts/run_worker_runtime_scheduler.sh loop --interval-seconds 300 --max-age-minutes 30
```

### 2.3 查看最新状态
```bash
bash scripts/run_worker_runtime_scheduler.sh status
```

### 2.4 查看统一看板
```bash
/home/admin/miniconda3/envs/vnpy_env/bin/python scripts/workflow_dashboard.py
```

---

## 3. 输出位置

### Latest state
- `reports/worker-runtime/state/latest_cycle.json`
- `reports/worker-runtime/state/latest_cycle.md`
- `reports/worker-runtime/state/latest_health_dashboard.json`
- `reports/worker-runtime/state/latest_recovery_dashboard.json`
- `reports/worker-runtime/state/latest_lifecycle_dashboard.json`
- `reports/worker-runtime/state/events.jsonl`

### Cycle history
- `reports/worker-runtime/cycles/<cycle_id>/cycle_summary.json`
- `reports/worker-runtime/cycles/<cycle_id>/cycle_summary.md`
- `reports/worker-runtime/cycles/<cycle_id>/health_dashboard.*`
- `reports/worker-runtime/cycles/<cycle_id>/recovery_dashboard.*`
- `reports/worker-runtime/cycles/<cycle_id>/lifecycle_dashboard.*`
- `reports/worker-runtime/cycles/<cycle_id>/healed_jobs.json`

---

## 4. 当前最准确的描述

现在可以说：
- 已有最小 scheduler
- 已有 latest state
- 已有 cycle history
- 已有三层运维视图

但不能说：
- 已完成完整常驻运行
- 已完成系统服务托管
- 已完成无人值守运维
