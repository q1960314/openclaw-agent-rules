# Official Release Rehearsal

Updated: 2026-03-28 19:39 Asia/Shanghai

## 1. 目的

official release rehearsal 用于在不真正发布的前提下，形成一条更接近真实发布的预演路径。

它当前不是 official release pipeline；
而是 official release rehearsal skeleton。

---

## 2. 当前产物
- `official_release_rehearsal.json`
- `approval_decision_placeholder.json`
- `approval_transition_stub.json`
- `human_approval_result_stub.json`
- `release_execution_guardrail.json`
- `post_approval_guardrail_transition.json`
- `official_release_state_placeholder.json`
- `approval_recompute_snapshot.json`
- `release_artifact_binding.json`

## 3. 当前关键状态
- `not_eligible`
- `ready_for_rehearsal`
- `approved_release_placeholder`

## 4. 当前最准确的说法

现在可以说：
- 系统已经能识别哪些 candidate 进入 official release rehearsal 范围
- 系统已经有官方发布预演骨架
- 系统已经把审批结果占位、执行硬阻断、审批后 guardrail 迁移、官方发布状态占位、审批结果重算快照与 release/rollback artifact 绑定接入 closure 链

但不能说：
- 已完成真实 official release pipeline
- 已完成真实发布执行链
- 已完成真实人工审批接入
