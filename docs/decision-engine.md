# Decision Engine

Updated: 2026-03-28 14:35 Asia/Shanghai

`scripts/runtime/decision_engine.py` 现在不只是 loop 决策模块，而是正在收口为统一决策中枢的第一阶段实现。

---

## 1. Runtime Module

- `scripts/runtime/decision_engine.py`

---

## 2. 当前职责（已实现）

### 2.1 Intake / Routing
- `intake_type(...)`
- `route_worker_role(...)`
- `execution_mode(...)`
- `routing_decision(...)`
- `analyze_request(...)`
- `intake_decision(...)`

当前已能输出：
- intake type
- suggested role
- execution mode
- risk tags / risk assessment
- manual review required
- clarification questions / clarification priority
- dependency plan / execution sequence
- objective hierarchy
- acceptance contract
- stop policy

### 2.2 Loop / Optimization
- `retry_policy(...)`
- `classify_failed_checks(...)`
- `adaptive_next_step(...)`
- `stop_decision(...)`
- `classify_terminal_status(...)`

### 2.3 Governance
- `governance_action_for_item(...)`
- `governance_recommendations(...)`

---

## 3. 当前输出语义

### 3.1 `analyze_request(...)`
返回结构化需求分析结果，包括：
- `objective_summary`
- `main_objective`
- `sub_objectives`
- `objective_hierarchy`
- `constraints`
- `acceptance_criteria`
- `acceptance_contract`
- `stop_criteria_hints`
- `stop_policy`
- `clarification_questions`
- `clarification_priority`
- `needs_clarification`
- `manual_review_required`
- `intake_type`
- `suggested_role`
- `execution_mode`
- `risk_tags`
- `risk_assessment`
- `dependency_plan`
- `execution_sequence`

### 3.2 `retry_policy(...)`
返回：
- `allow_retry`
- `reason`
- `requested_reason`

### 3.3 `adaptive_next_step(...)`
返回：
- `next_role`
- `objective`
- `decision_basis`

### 3.4 `stop_decision(...)`
返回之一：
- `stop_passed`
- `stop_threshold_not_met`
- `continue_with_adaptive_step`

---

## 4. 本轮增强的意义

这次增强的重点不是再加新 worker，而是把原本分散的“需求理解 + 风险识别 + 路由判断 + 审批判定”收进统一模块。

这使系统更接近：

> **先分析，再派单；先识别风险，再继续流转。**

而不是：

> **收到一句目标后直接路由。**

---

## 5. 当前仍未彻底完成的部分

虽然 intake / routing 已进入第一阶段收口，但还没有完全做到：

1. review 决策完全统一
2. governance 分级恢复完全统一
3. loop / routing / review 共用一套状态枚举
4. 更复杂 DAG 并行策略自动生成
5. 与 worker result schema 完整联动

因此现在的准确表述应是：

> `decision_engine.py` 已从 loop 决策模块升级为 **统一决策中枢雏形（当前已完成 master 骨架深化版）**，但还不是最终形态。
