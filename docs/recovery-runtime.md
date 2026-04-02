# Recovery Runtime

Updated: 2026-03-28 15:04 Asia/Shanghai

## 1. 目的

`recovery_runtime.py` 用于把当前系统从“发现异常”推进到“结构化判断异常是否可恢复、如何恢复、是否需要人工介入”。

它不是最终 daemon/supervisor，也不是完整调度器；当前定位是：

> **治理层与持续运行化之间的恢复分级中间层**

---

## 2. Runtime Module

- `scripts/runtime/recovery_runtime.py`

---

## 3. 当前已实现职责

### 3.1 恢复分级
当前会把任务按 recoverability 进行分类：
- `none`
- `auto_retry`
- `retryable`
- `manual_intervention`
- `unknown`

### 3.2 推荐动作
当前会给出结构化 `recommended_action`：
- `none`
- `auto_retry`
- `retry_candidate`
- `manual_review`

### 3.3 单任务恢复快照
- `task_recovery_snapshot(task_id)`

### 3.4 全局恢复看板
- `jobs_recovery_dashboard()`
- `export_recovery_dashboard(...)`

---

## 4. 当前意义

这一步的价值不在于“自动修好一切”，而在于先把：

- 什么能自动重试
- 什么只能人工介入
- 什么已经不应再恢复

这三件事，从隐式经验判断，收敛成显式结构化判断。

---

## 5. 当前阶段新增进展

现在已经补上了一个最小 scheduler 骨架：

- `scripts/runtime/worker_runtime_scheduler.py`
- `scripts/run_worker_runtime_scheduler.sh`

它当前支持：
- `run-once`
- `loop`
- `status`

并会输出：
- latest cycle state
- health / recovery / lifecycle dashboard
- healed jobs summary
- scheduler events

这意味着系统已经不再完全依赖手动逐条运行治理脚本，而是有了最小周期驱动入口。

## 6. 当前仍未完成的部分

现在还没有做到：

1. 真正的 daemon/supervisor 托管
2. 与系统服务管理器（systemd/supervisord）集成
3. 真正的分级回滚策略
4. 与 worker 状态机的完整闭环恢复点
5. 更细粒度的错误原因分类（例如网络错误 / 代码错误 / 依赖错误 / 审批阻断）

所以现在不能表述成：
- 已完成自动恢复系统
- 已完成长期无人值守运行

更准确的表述应是：

> **恢复分级基础层已建立，并已进入最小持续运行化阶段，但还不是完整常驻运行系统。**
