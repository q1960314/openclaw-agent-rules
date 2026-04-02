# Worker Ecosystem Status

Updated: 2026-03-28 02:50 Asia/Shanghai

## 1. 当前结论

当前系统已经从“多会话 agent”演进为“可运行的 worker 生态骨架”。

### 已完成的核心能力
- 结构化 intake 入口（main）
- 多角色任务路由（master-quant）
- 9 个真实执行型 worker 链路
- 内容级验收（test-expert）
- 文档/沉淀闭环（doc-manager / knowledge-steward）
- claim / handoff / status / retry / 审计 / 心跳 / lease / stale 治理
- artifact manifest / result envelope / health dashboard / governance actions

### 当前真实状态（截至本次盘点）
- 已接入 worker 文件：14 个（含 orchestration / validation / delivery 节点）
- 已跑通真实执行 worker：9 个
- 已跑通闭环支持节点：4 个（main / master-quant / test-expert / doc-manager / knowledge-steward 中，main/master 更偏入口/编排）
- 健康治理：已具备 lease、heartbeat、stale scan、heal、策略位控制 auto-retry、健康仪表盘

## 2. 已接入 worker 清单

### 2.1 入口 / 编排 / 验收 / 交付类
- `main_worker.py`
- `master_quant_worker.py`
- `test_expert_worker.py`
- `doc_manager_worker.py`
- `knowledge_steward_worker.py`

### 2.2 已真实打通的执行型 worker
- `coder_worker.py`
- `strategy_expert_worker.py`
- `parameter_evolver_worker.py`
- `backtest_engine_worker.py`
- `data_collector_worker.py`
- `factor_miner_worker.py`
- `sentiment_analyst_worker.py`
- `finance_learner_worker.py`
- `ops_monitor_worker.py`

## 3. 已真实跑通过的任务类型

### 3.1 OpenCode / plan-build 相关
- coder（plan / build / isolate worktree）
- strategy-expert（plan）
- parameter-evolver（plan）
- factor-miner（plan）
- sentiment-analyst（plan）
- finance-learner（plan）

### 3.2 原生执行相关
- backtest-engine（vnpy_env + smoke backtest）
- data-collector（snapshot / check / quality score）
- ops-monitor（openclaw status / workflow status / health dashboard）

## 4. 协议与运行时基座

### 4.1 protocols/
- `task.schema.json`
- `claim.schema.json`
- `status.schema.json`
- `handoff.schema.json`
- `review.schema.json`
- `artifact_manifest.schema.json`
- `result_envelope.schema.json`

### 4.2 runtime/
- `task_queue.py`
- `worker_base.py`
- `status_manager.py`
- `artifact_manager.py`
- `review_manager.py`
- `audit_manager.py`
- `heartbeat_monitor.py`

## 5. 已落地治理能力

### 5.1 权限与流转
- 非授权 worker 不能执行别人的任务
- handoff 目标必须合法
- handoff 后只有目标角色能 claim
- rejected / failed 任务不能直接伪装为 passed
- 状态机已限制非法跳转

### 5.2 验收与阻断
- `test-expert` 已支持多类型内容级验收
- 未通过 review 的任务不能继续进入 doc-manager / knowledge-steward
- 假完成（如无真实 diff / 无真实变更）可以被正确打回

### 5.3 审计与恢复
- `events.jsonl` 记录 task_created / claimed / status / artifact / handoff / review / completed / failed / stale_marked 等事件
- retry 已有标准语义：`retry_of` / `retry_index` / `retry_requested_by` / `retry_reason`
- stale task 可被识别并回收
- auto-retry 已按 metadata 策略位控制，而非一刀切

### 5.4 健康治理
- claim 带 `lease_until`
- worker 活动时自动续租
- `heartbeat.json` 持续记录最后活跃状态
- `heal_jobs()` 可对 stale task 执行恢复逻辑
- `health_dashboard.json` / `health_dashboard.md` 已可输出
- `governance_actions.json` 已可输出治理建议

## 6. 当前还没有彻底完成的部分（真实缺口）

以下内容仍应视为“下一阶段改进项”，不应伪装成已完成：

### 6.1 持续运行能力
- 当前 worker 主要仍通过 `run_once` 驱动，没有统一常驻 supervisor / daemon
- 但已新增最小周期驱动骨架：
  - `scripts/runtime/worker_runtime_scheduler.py`
  - `scripts/run_worker_runtime_scheduler.sh`
- scheduler 已能做单次 / 循环巡检，并输出 latest cycle state + health/recovery/lifecycle dashboards
- 因此当前状态应理解为：**已进入最小持续运行化阶段，但尚未完成完整常驻托管**

### 6.2 更强编排能力
- `master-quant` 已能路由多类任务，但还不算完整 DAG 编排器
- 跨 worker 多步依赖仍偏顺序式，尚未形成复杂依赖图管理

### 6.3 真正 build 能力的覆盖面
- 真实 build 执行目前主要集中在 coder 链路
- 其他研究型 worker 仍以 plan/研究产物为主，不是代码执行型 build worker

### 6.4 全量 agent 终态
- 当前体系已覆盖 14 个 worker 文件层面的骨架与大部分关键能力
- 但“所有 agent 在所有业务场景都完全独立完成任务”这一终态仍未达到

## 7. 当前最真实的一句话总结

系统已经不是概念原型。

它已经具备：
- 结构化入口
- 多 worker 路由
- 多类型真实执行
- 内容级验收
- 权限约束
- 审计
- 健康治理
- 自动恢复策略位

但它仍处于“强骨架、可运行、持续加固中”的阶段，而不是“最终完工”。

## 8. 下一步建议

优先顺序建议如下：

1. **持续运行化**：引入 supervisor / loop / cron 化健康巡检
2. **编排升级**：把 master-quant 从规则路由升级为更完整的依赖编排器
3. **schema 收口**：补每类 worker 的专属 result schema 校验
4. **build 扩展**：决定除 coder 外，哪些 worker 需要真正 build 模式
5. **运行看板**：把 health dashboard 提升为常驻运维视图
