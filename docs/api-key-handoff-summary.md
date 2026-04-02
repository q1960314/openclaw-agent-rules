# API Key 更换前交接摘要

Updated: 2026-03-28 04:16 Asia/Shanghai

## 1. 目的

这份文档用于在更换 API key、模型通道、会话上下文或短期中断前，保留当前系统的关键状态，确保后续可以快速恢复工作，而不必重新梳理整个 worker 生态。

---

## 2. 当前系统一句话状态

当前系统已经从“多会话 agent”演进为：

> **可验证、可运行、已进入多轮自动推进阶段的 worker 生态原型**

它已经具备：
- 多 worker 执行
- 多轮 loop
- retry
- stop criteria
- adaptive switching
- audit / heartbeat / stale 治理
- artifact manifest / result envelope / health dashboard / governance actions

但它还不是最终完工的全自动优化系统。

---

## 3. 当前已接入的 worker

### 3.1 入口 / 编排 / 验收 / 交付
- `main_worker.py`
- `master_quant_worker.py`
- `test_expert_worker.py`
- `doc_manager_worker.py`
- `knowledge_steward_worker.py`

### 3.2 已真实打通的执行型 worker
- `coder_worker.py`
- `strategy_expert_worker.py`
- `parameter_evolver_worker.py`
- `backtest_engine_worker.py`
- `data_collector_worker.py`
- `factor_miner_worker.py`
- `sentiment_analyst_worker.py`
- `finance_learner_worker.py`
- `ops_monitor_worker.py`

---

## 4. 当前已验证的关键能力

### 4.1 单 worker loop
已验证：
- `LOOP-20260328-025841` → `passed`
- `LOOP-20260328-030148` → `passed`

### 4.2 coder retry 分支
已验证：
- `LOOP-20260328-030906` → `passed`
- 第 1 轮 reject
- 自动创建 retry task
- 第 2 轮通过

### 4.3 固定跨 worker 多轮链
已验证：
- `XLOOP-20260328-031412` → `passed`
- 链路：`strategy-expert -> backtest-engine -> parameter-evolver -> backtest-engine`

### 4.4 stop criteria 生效
已验证：
- `XLOOP-20260328-032109` → `threshold_not_met`
- 回测执行成功 ≠ 优化完成
- 系统会因阈值不满足而停止

### 4.5 adaptive switching 生效
已验证：
- `XLOOP-20260328-032755` → `threshold_not_met`
- 已真实发生角色切换：
  - `factor-miner`
  - `strategy-expert`

### 4.6 决策中枢（第一/二/三轮）
已验证：
- retry policy 接入 loop
- stop decision 接入 cross-worker loop
- adaptive next step 接入 cross-worker loop
- governance action 接入 health governance
- intake 分类接入 `decision_engine`
- worker routing 接入 `decision_engine`

---

## 5. 当前最重要的 runtime / docs 文件

### 5.1 runtime
- `scripts/runtime/task_queue.py`
- `scripts/runtime/worker_base.py`
- `scripts/runtime/status_manager.py`
- `scripts/runtime/review_manager.py`
- `scripts/runtime/artifact_manager.py`
- `scripts/runtime/audit_manager.py`
- `scripts/runtime/heartbeat_monitor.py`
- `scripts/runtime/stop_criteria.py`
- `scripts/runtime/decision_engine.py`
- `scripts/runtime/continuous_optimization_loop.py`
- `scripts/runtime/cross_worker_optimization_loop.py`

### 5.2 protocols
- `protocols/task.schema.json`
- `protocols/claim.schema.json`
- `protocols/status.schema.json`
- `protocols/handoff.schema.json`
- `protocols/review.schema.json`
- `protocols/artifact_manifest.schema.json`
- `protocols/result_envelope.schema.json`
- `protocols/stop_criteria.schema.json`

### 5.3 docs
- `docs/worker-ecosystem-status.md`
- `docs/self-audit-checklist.md`
- `docs/continuous-optimization-loop.md`
- `docs/cross-worker-optimization-loop.md`
- `docs/decision-engine.md`
- `docs/stop-criteria.md`
- `docs/api-key-handoff-summary.md`（本文件）
- `docs/ecosystem-completion-roadmap.md`

---

## 6. 当前最关键的已验证 loop 目录

### 单 worker / retry
- `traces/loops/LOOP-20260328-025841`
- `traces/loops/LOOP-20260328-030148`
- `traces/loops/LOOP-20260328-030906`
- `traces/loops/LOOP-20260328-035140`

### 跨 worker / stop / adaptive
- `traces/loops/XLOOP-20260328-031412`
- `traces/loops/XLOOP-20260328-032109`
- `traces/loops/XLOOP-20260328-032755`
- `traces/loops/XLOOP-20260328-034506`
- `traces/loops/XLOOP-20260328-034704`

---

## 7. 当前仍未彻底完成的部分

### 7.1 持续常驻运行
当前没有证据证明：
- 系统已作为长期 daemon / supervisor 持续运行
- 无需人工触发即可长期稳定循环

### 7.2 完整 DAG 编排
`master-quant` 已具备多角色路由与结构化派单，但还不是完整 DAG 编排器。

### 7.3 全场景自动优化到最终完成
当前没有证据证明：
- 系统能在所有场景下自动持续优化到最终满意结果

### 7.4 关键 agent 的“细致专家能力”
当前很多 agent 已做到：
- 能跑
- 能出产物
- 能进 loop

但尚未完全做到：
- 像成熟专家一样非常细致地分析问题、拆解约束、给出多方案并识别隐含风险。

---

## 8. 更换 API key 后如何恢复

### 8.1 可以保留的前提
如果满足以下条件，通常可继续承接：
- 同一台机器 / 同一 OpenClaw 实例
- 同一工作区：`/home/admin/.openclaw/workspace/master`
- 同一 `traces/`、`docs/`、`memory/`、runtime 文件
- 同一长期记忆范围（若使用）

### 8.2 恢复时优先看的文件
按顺序建议查看：
1. `docs/self-audit-checklist.md`
2. `docs/worker-ecosystem-status.md`
3. `docs/api-key-handoff-summary.md`
4. `docs/ecosystem-completion-roadmap.md`
5. 最近的 loop 报告：`traces/loops/*/loop_report.json`

### 8.3 最简恢复口令
后续恢复时，可以直接从这句开始：

> 继续基于 `docs/api-key-handoff-summary.md` 和 `docs/self-audit-checklist.md` 的当前状态推进，不要把强雏形说成最终完工系统。

---

## 9. 后续开发的正确口径

以后所有汇报都应该明确区分：
- **已验证**
- **部分验证**
- **仅骨架**
- **需修正表述**

避免再次把：
- “已实现雏形”
说成：
- “已彻底完成”

---

## 10. 当前最准确的一句话

> 当前系统已经真实具备多 worker 执行、多轮 loop、retry、stop criteria、adaptive switching、治理与审计，但它仍应被定义为：**可验证、可运行、已进入多轮自动推进阶段的 worker 生态原型**。
