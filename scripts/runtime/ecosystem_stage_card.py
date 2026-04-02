#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ecosystem stage card: compress many runtime/formalization/evaluation signals into one honest stage summary."""
from __future__ import annotations

from datetime import datetime
from typing import Any


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _clamp(v: int) -> int:
    return max(0, min(100, int(v)))


OFFICIAL_RELEASE_FOCUS_LABEL_ZH = {
    'prereq_not_ready': '前置条件未满足',
    'awaiting_human_approval': '等待人工审批',
    'approved_but_blocked': '已审批但仍有阻塞',
    'execution_path_not_implemented': '执行路径未实现',
    'rejected_candidates_present': '已出现拒绝样本',
    'pipeline_state_unclear': '当前卡点仍不清晰',
}

OFFICIAL_RELEASE_STATE_ZH = {
    'candidate_not_ready': '候选结果尚未就绪',
    'awaiting_human_approval': '等待人工审批',
    'approved_but_blocked': '已审批但仍阻塞',
    'ready_but_execution_not_implemented': '已就绪但执行路径未实现',
    'rejected': '已拒绝',
}

OFFICIAL_RELEASE_BLOCKER_ZH = {
    'human_approval_not_recorded': '人工审批结果未记录',
    'official_release_rehearsal_not_ready': '正式发布预演未就绪',
    'pre_release_gate_not_ready': '发布前置门禁未就绪',
    'release_artifact_binding_not_ready': '发布产物绑定未就绪',
    'rollback_not_ready': '回滚准备未就绪',
    'human_approval_rejected': '人工审批已拒绝',
    'human_approval_invalid_state': '人工审批状态异常',
}

GAP_ID_ZH = {
    'official_release_pipeline': '正式发布 / 回滚闭环',
    'real_human_approval': '真实人工审批闭环',
    'adaptive_loop_depth': '自适应循环样本深度',
    'recent_learning_density': '近期经验沉淀密度',
    'benchmark_regression': '基准与回归评测体系',
    'supervisor_runtime': '常驻托管闭环',
    'quality_observability': '质量观察面完整度',
}

ROLE_NAME_ZH = {
    'strategy-expert': '策略专家',
    'parameter-evolver': '参数进化智能体',
    'factor-miner': '因子挖掘智能体',
    'backtest-engine': '回测引擎智能体',
    'data-collector': '数据采集员',
    'finance-learner': '金融学习员',
    'sentiment-analyst': '舆情分析员',
    'ops-monitor': '运维监控员',
    'coder': '代码守护者',
    'test-expert': '测试专家',
    'doc-manager': '文档管理员',
    'knowledge-steward': '生态沉淀员',
    'master-quant': '主控中枢',
}


def _sorted_positive_counts(counts: dict[str, Any], *, limit: int | None = None) -> dict[str, int]:
    normalized = {str(key): int(value or 0) for key, value in (counts or {}).items() if int(value or 0) > 0}
    ordered_keys = sorted(normalized, key=lambda key: (-normalized[key], key))
    if limit is not None:
        ordered_keys = ordered_keys[:limit]
    return {key: normalized[key] for key in ordered_keys}


def _translate_count_keys(counts: dict[str, Any], mapping: dict[str, str]) -> dict[str, int]:
    translated: dict[str, int] = {}
    for key, value in (counts or {}).items():
        normalized = int(value or 0)
        if normalized <= 0:
            continue
        translated[mapping.get(str(key), str(key))] = normalized
    return translated


def _aggregate_pipeline_blockers(items: list[dict[str, Any]]) -> dict[str, int]:
    blocker_counts: dict[str, int] = {}
    for item in items or []:
        blockers = item.get('official_release_pipeline_blockers') or []
        if not isinstance(blockers, list):
            continue
        for blocker in blockers:
            blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1
    return _sorted_positive_counts(blocker_counts)


def _build_official_release_focus_card(*, state_counts: dict[str, Any], blocker_counts: dict[str, Any]) -> dict[str, Any]:
    normalized_states = _sorted_positive_counts(state_counts)
    normalized_blockers = _sorted_positive_counts(blocker_counts, limit=4)
    state_order = {
        'candidate_not_ready': 0,
        'awaiting_human_approval': 1,
        'approved_but_blocked': 2,
        'ready_but_execution_not_implemented': 3,
        'rejected': 4,
    }
    dominant_state = None
    if normalized_states:
        dominant_state = sorted(
            normalized_states,
            key=lambda key: (-normalized_states[key], state_order.get(key, 99), key),
        )[0]

    prereq_blockers = {
        'pre_release_gate_not_ready',
        'official_release_rehearsal_not_ready',
        'release_artifact_binding_not_ready',
        'rollback_not_ready',
    }
    top_blockers = list(normalized_blockers.keys())
    blocker_summary = normalized_blockers if normalized_blockers else {}

    if dominant_state == 'candidate_not_ready':
        prereq_hits = {key: normalized_blockers.get(key, 0) for key in prereq_blockers if normalized_blockers.get(key, 0)}
        title = '优先补正式发布前置条件'
        why_now = (
            '当前首要缺口虽然已经进入正式发布管线看板，但主导状态仍是“候选结果尚未就绪”，'
            f'说明卡点主要还在发布前置条件，而不是审批动作本身；状态分布={_translate_count_keys(normalized_states, OFFICIAL_RELEASE_STATE_ZH)}'
        )
        if prereq_hits:
            why_now += f'，当前主导前置阻塞={_translate_count_keys(_sorted_positive_counts(prereq_hits), OFFICIAL_RELEASE_BLOCKER_ZH)}。'
        elif blocker_summary:
            why_now += f'，当前可见阻塞={_translate_count_keys(blocker_summary, OFFICIAL_RELEASE_BLOCKER_ZH)}。'
        else:
            why_now += '，当前还缺更完整的前置阻塞样本。'
        recommended_actions = [
            '先补齐发布前置门禁、正式发布预演、发布产物绑定、回滚支持这组前置条件，不要过早讨论真实发布执行',
            '继续让收口快照和运行看板明确暴露到底缺哪一个前置条件，而不是只给“未就绪”总标签',
            '等前置条件进入“可提交人工发布评审”后，再把焦点切到真实人工审批接入',
        ]
        focus_label = 'prereq_not_ready'
    elif dominant_state == 'awaiting_human_approval':
        title = '优先接通真实人工审批入口'
        why_now = (
            '当前正式发布管线的主导状态是“等待人工审批”，'
            f'说明前置条件已基本进入可审批态，但真实批准/拒绝输入仍未进入执行路径；状态分布={_translate_count_keys(normalized_states, OFFICIAL_RELEASE_STATE_ZH)}。'
        )
        recommended_actions = [
            '把真实人工审批输入槽位从占位态推进到可正式记录“批准/拒绝”的入口',
            '让审批结果真正回写到人工审批结果、审批重算、发布执行门禁，而不是只停留在占位状态',
            '在阶段卡里持续区分“等待人工审批”和“候选结果尚未就绪”，避免把审批缺口和前置缺口混为一谈',
        ]
        focus_label = 'awaiting_human_approval'
    elif dominant_state == 'approved_but_blocked':
        title = '优先解除审批后的残余阻塞'
        why_now = (
            '当前正式发布管线已出现“已审批但仍阻塞”，'
            f'说明人工审批假设已跨过去，但发布仍被剩余门禁卡住；状态分布={_translate_count_keys(normalized_states, OFFICIAL_RELEASE_STATE_ZH)}'
        )
        if blocker_summary:
            why_now += f'，当前残余阻塞={_translate_count_keys(blocker_summary, OFFICIAL_RELEASE_BLOCKER_ZH)}。'
        else:
            why_now += '。'
        recommended_actions = [
            '优先清掉审批之后仍保留的阻塞原因，尤其是发布前置门禁、发布产物绑定、回滚支持这类非审批阻塞',
            '让审批后门禁切换和正式发布管线摘要输出同一组保留阻塞，避免两套口径',
            '确认一旦阻塞解除，阶段卡会把焦点自动切换到“执行路径未实现”，而不是继续停留在“仍阻塞”口径',
        ]
        focus_label = 'approved_but_blocked'
    elif dominant_state == 'ready_but_execution_not_implemented':
        title = '优先补真实发布执行路径'
        why_now = (
            '当前正式发布管线已进入“已就绪但执行路径未实现”，'
            f'说明前置条件和审批信号已经足够，但真正的正式发布动作仍停留在占位实现；状态分布={_translate_count_keys(normalized_states, OFFICIAL_RELEASE_STATE_ZH)}。'
        )
        recommended_actions = [
            '把正式发布动作从占位实现推进到受控的真实执行前检查链',
            '同步补齐回滚登记与发布产物的正式绑定，确保执行路径和回滚路径成对成立',
            '让阶段卡在“执行路径未实现”时直接标出这是最后一跳缺失，避免再次被误判成审批问题',
        ]
        focus_label = 'execution_path_not_implemented'
    elif dominant_state == 'rejected':
        title = '优先处理已拒绝候选结果的返工分流'
        why_now = (
            '当前正式发布管线已出现“已拒绝”状态，'
            f'说明至少有一部分候选结果已被拒绝，不应再按“可发布候选”口径汇总；状态分布={_translate_count_keys(normalized_states, OFFICIAL_RELEASE_STATE_ZH)}。'
        )
        recommended_actions = [
            '把已拒绝候选结果从“可发布”汇总面里单独分流，避免污染可发布候选统计',
            '让阶段卡明确区分“需要返工的已拒绝样本”和“仍等待审批的候选结果”',
            '在后续正式发布收口汇总里补充拒绝后回退到哪一层重做的说明',
        ]
        focus_label = 'rejected_candidates_present'
    else:
        title = '优先补正式发布管线可解释性'
        why_now = '当前正式发布管线已进入总控观察面，但状态分布仍不足以判断主导卡点，需要继续补真实样本。'
        recommended_actions = [
            '继续补正式发布管线的真实状态样本',
            '让阻塞分布和状态分布一起进入阶段卡',
            '避免只看到首要缺口，而看不到具体卡点类型',
        ]
        focus_label = 'pipeline_state_unclear'

    return {
        'focus_label': focus_label,
        'focus_label_zh': OFFICIAL_RELEASE_FOCUS_LABEL_ZH.get(focus_label, focus_label),
        'dominant_state': dominant_state,
        'dominant_state_zh': OFFICIAL_RELEASE_STATE_ZH.get(dominant_state, dominant_state),
        'state_counts': normalized_states,
        'state_counts_zh': _translate_count_keys(normalized_states, OFFICIAL_RELEASE_STATE_ZH),
        'blocker_counts': blocker_summary,
        'blocker_counts_zh': _translate_count_keys(blocker_summary, OFFICIAL_RELEASE_BLOCKER_ZH),
        'title': title,
        'why_now': why_now,
        'recommended_actions': recommended_actions,
    }


def build_stage_card(*, latest_cycle: dict[str, Any], health: dict[str, Any], recovery: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    job_count = int((health or {}).get('job_count') or 0)
    stale_count = int((health or {}).get('stale_count') or 0)
    governance_action_count = int((latest_cycle or {}).get('governance_action_count') or 0)
    quality_average = (health or {}).get('quality_average_score')
    quality_observable = quality_average is not None or bool((health or {}).get('quality_grade_counts'))
    formalization_counts = (health or {}).get('formalization_state_counts', {}) or {}
    closure_counts = (health or {}).get('closure_counts', {}) or {}
    adaptive_loop_summary = (latest_cycle or {}).get('adaptive_loop_summary', {}) or {}
    recent_learning_summary = (latest_cycle or {}).get('recent_ecosystem_learning', {}) or {}
    open_gap_summary = (latest_cycle or {}).get('open_gap_summary', {}) or {}
    observation_runtime = (latest_cycle or {}).get('observation_runtime', {}) or {}
    human_approval_state_counts = (health or {}).get('human_approval_state_counts', {}) or {}
    approval_recompute_state_counts = (health or {}).get('approval_recompute_state_counts', {}) or {}
    release_execution_state_counts = (health or {}).get('release_execution_state_counts', {}) or {}
    official_release_pipeline_state_counts = (health or {}).get('official_release_pipeline_state_counts', {}) or {}
    health_items = (health or {}).get('items', []) or []
    official_release_pipeline_blocker_counts = _aggregate_pipeline_blockers(health_items)
    official_release_focus = _build_official_release_focus_card(
        state_counts=official_release_pipeline_state_counts,
        blocker_counts=official_release_pipeline_blocker_counts,
    )
    release_ready_candidates = int(formalization_counts.get('release_ready_candidate', 0) or 0)
    manual_review_gates = int(formalization_counts.get('manual_review_gate', 0) or 0)
    approval_required_count = int(closure_counts.get('approval_required', 0) or 0)
    awaiting_approval_count = int(human_approval_state_counts.get('awaiting', 0) or 0)
    approved_count = int(human_approval_state_counts.get('approved', 0) or 0)
    rejected_count = int(human_approval_state_counts.get('rejected', 0) or 0)
    pre_release_ready_count = int(closure_counts.get('pre_release_ready', 0) or 0)
    closure_consistency_ready_count = int(closure_counts.get('closure_consistency_ready', 0) or 0)
    official_release_rehearsal_ready_count = int(closure_counts.get('official_release_rehearsal_ready', 0) or 0)
    rollback_ready_count = int(closure_counts.get('rollback_supported', 0) or 0)
    official_release_pipeline_visible_count = int(closure_counts.get('official_release_pipeline_visible', 0) or 0)
    official_release_pipeline_executable_count = int(closure_counts.get('official_release_pipeline_executable', 0) or 0)
    executor_contract_available_count = int(closure_counts.get('executor_contract_available', 0) or 0)
    dry_run_available_count = int(closure_counts.get('dry_run_available', 0) or 0)
    execution_receipt_protocol_available_count = int(closure_counts.get('execution_receipt_protocol_available', 0) or 0)
    handoff_packet_available_count = int(closure_counts.get('handoff_packet_available', 0) or 0)
    operator_execution_request_available_count = int(closure_counts.get('operator_execution_request_available', 0) or 0)
    receipt_correlation_ready_count = int(closure_counts.get('receipt_correlation_ready', 0) or 0)
    executor_readiness_review_available_count = int(closure_counts.get('executor_readiness_review_visible', 0) or 0)
    handoff_boundary_ready_count = int(closure_counts.get('handoff_boundary_ready', 0) or 0)
    executor_adapter_available_count = int((latest_cycle or {}).get('executor_adapter_available_count', 0) or 0)
    executor_capability_registry_available = bool((latest_cycle or {}).get('executor_capability_registry_available', False))
    invocation_policy_available = bool((latest_cycle or {}).get('invocation_policy_available', False))
    future_executor_scaffold_available = bool((latest_cycle or {}).get('future_executor_scaffold_available', False))
    executor_plugin_interface_available = bool((latest_cycle or {}).get('executor_plugin_interface_available', False))
    transcript_contract_available = bool((latest_cycle or {}).get('transcript_contract_available', False))
    no_op_executor_available = bool((latest_cycle or {}).get('no_op_executor_available', False))
    executor_conformance_available = bool((latest_cycle or {}).get('executor_conformance_available', False))
    executor_error_contract_available = bool((latest_cycle or {}).get('executor_error_contract_available', False))
    release_rollback_parity_available = bool((latest_cycle or {}).get('release_rollback_parity_available', False))
    implementation_blueprint_available = bool((latest_cycle or {}).get('implementation_blueprint_available', False))
    executor_delivery_pack_available = bool((latest_cycle or {}).get('executor_delivery_pack_available', False))
    executor_acceptance_pack_available = bool((latest_cycle or {}).get('executor_acceptance_pack_available', False))
    ownership_split_available = bool((latest_cycle or {}).get('ownership_split_available', False))
    executor_blocker_matrix_available = bool((latest_cycle or {}).get('executor_blocker_matrix_available', False))
    executor_delivery_item_count = int((latest_cycle or {}).get('executor_delivery_item_count', 0) or 0)
    executor_acceptance_case_count = int((latest_cycle or {}).get('executor_acceptance_case_count', 0) or 0)
    executor_blocker_count = int((latest_cycle or {}).get('executor_blocker_count', 0) or 0)
    cutover_pack_available = bool((latest_cycle or {}).get('cutover_pack_available', False))
    integration_checklist_available = bool((latest_cycle or {}).get('integration_checklist_available', False))
    risk_register_available = bool((latest_cycle or {}).get('risk_register_available', False))
    handoff_summary_available = bool((latest_cycle or {}).get('handoff_summary_available', False))
    credential_binding_policy_available = bool((latest_cycle or {}).get('credential_binding_policy_available', False))
    target_binding_registry_available = bool((latest_cycle or {}).get('target_binding_registry_available', False))
    cutover_signoff_available = bool((latest_cycle or {}).get('cutover_signoff_available', False))
    blocker_drilldown_available = bool((latest_cycle or {}).get('blocker_drilldown_available', False))
    human_action_pack_available = bool((latest_cycle or {}).get('human_action_pack_available', False))
    credential_binding_evidence_checklist_available = bool((latest_cycle or {}).get('credential_binding_evidence_checklist_available', False))
    signoff_evidence_packet_available = bool((latest_cycle or {}).get('signoff_evidence_packet_available', False))
    unresolved_blocker_tracker_available = bool((latest_cycle or {}).get('unresolved_blocker_tracker_available', False))
    pending_human_action_board_available = bool((latest_cycle or {}).get('pending_human_action_board_available', False))
    credential_binding_runbook_available = bool((latest_cycle or {}).get('credential_binding_runbook_available', False))
    signoff_runbook_available = bool((latest_cycle or {}).get('signoff_runbook_available', False))
    blocker_resolution_playbook_available = bool((latest_cycle or {}).get('blocker_resolution_playbook_available', False))
    unresolved_credential_binding_count = int((latest_cycle or {}).get('unresolved_credential_binding_count', 0) or 0)
    unresolved_signoff_count = int((latest_cycle or {}).get('unresolved_signoff_count', 0) or 0)
    unresolved_blocker_owner_count = int((latest_cycle or {}).get('unresolved_blocker_owner_count', 0) or 0)
    pending_signoff_role_count = int((latest_cycle or {}).get('pending_signoff_role_count', 0) or 0)
    binding_evidence_gap_count = int((latest_cycle or {}).get('binding_evidence_gap_count', 0) or 0)
    top_blocker_categories = list((latest_cycle or {}).get('top_blocker_categories', []) or [])
    top_human_actions = list((latest_cycle or {}).get('top_human_actions', []) or [])
    top_pending_human_actions = list((latest_cycle or {}).get('top_pending_human_actions', []) or [])
    top_unresolved_human_blockers = list((latest_cycle or {}).get('top_unresolved_human_blockers', []) or [])
    top_missing_executor_contracts = list((latest_cycle or {}).get('top_missing_executor_contracts', []) or [])
    parity_gaps = list((latest_cycle or {}).get('parity_gaps', []) or [])
    top_executor_risks = list((latest_cycle or {}).get('top_executor_risks', []) or [])
    top_executor_blockers = list((latest_cycle or {}).get('top_executor_blockers', []) or [])
    top_remaining_blockers = list((latest_cycle or {}).get('top_remaining_blockers', []) or [])
    environment_guard_ok_count = int((latest_cycle or {}).get('environment_guard_ok_count', 0) or 0)
    environment_guard_unmet_count = int((latest_cycle or {}).get('environment_guard_unmet_count', 0) or 0)
    top_executor_adapter_types = list((latest_cycle or {}).get('top_executor_adapter_types', []) or [])
    top_executor_plugin_targets = list((latest_cycle or {}).get('top_executor_plugin_targets', []) or [])
    release_execution_requested_count = int(closure_counts.get('release_execution_requested', 0) or 0)
    rollback_execution_requested_count = int(closure_counts.get('rollback_execution_requested', 0) or 0)
    release_execution_receipt_recorded_count = int(closure_counts.get('release_execution_receipt_recorded', 0) or 0)
    rollback_execution_receipt_recorded_count = int(closure_counts.get('rollback_execution_receipt_recorded', 0) or 0)
    closure_visible_count = int(closure_counts.get('closure_visible', 0) or 0)
    executor_readiness_gate_count = int((latest_cycle or {}).get('executor_readiness_gate_count', 0) or 0)
    executor_unmet_gate_count = int((latest_cycle or {}).get('executor_unmet_gate_count', 0) or 0)
    top_unmet_executor_gates = list((latest_cycle or {}).get('top_unmet_executor_gates', []) or [])
    executor_admission_available = bool((latest_cycle or {}).get('executor_admission_available', False))
    go_no_go_available = bool((latest_cycle or {}).get('go_no_go_available', False))
    rollout_gate_count = int((latest_cycle or {}).get('rollout_gate_count', 0) or 0)
    rollout_unmet_count = int((latest_cycle or {}).get('rollout_unmet_count', 0) or 0)
    waiver_exception_count = int((latest_cycle or {}).get('waiver_exception_count', 0) or 0)
    overall_admission_state = (latest_cycle or {}).get('overall_admission_state')
    top_blocking_gates = list((latest_cycle or {}).get('top_blocking_gates', []) or [])
    executor_simulation_available_count = int((latest_cycle or {}).get('executor_simulation_available_count', 0) or 0)
    executor_simulation_pass_count = int((latest_cycle or {}).get('executor_simulation_pass_count', 0) or 0)
    executor_simulation_fail_count = int((latest_cycle or {}).get('executor_simulation_fail_count', 0) or 0)
    contract_compliance_available = bool((latest_cycle or {}).get('contract_compliance_available', False))
    integration_rehearsal_available = bool((latest_cycle or {}).get('integration_rehearsal_available', False))
    top_executor_contract_gaps = list((latest_cycle or {}).get('top_executor_contract_gaps', []) or [])
    top_execution_handoff_targets = list((latest_cycle or {}).get('top_execution_handoff_targets', []) or [])
    top_command_plan_steps = list((latest_cycle or {}).get('top_command_plan_steps', []) or [])
    execution_request_requested_count = int((latest_cycle or {}).get('execution_request_requested_count', 0) or 0)
    execution_request_acknowledged_count = int((latest_cycle or {}).get('execution_request_acknowledged_count', 0) or 0)
    execution_request_accepted_count = int((latest_cycle or {}).get('execution_request_accepted_count', 0) or 0)
    execution_request_declined_count = int((latest_cycle or {}).get('execution_request_declined_count', 0) or 0)
    execution_request_expired_count = int((latest_cycle or {}).get('execution_request_expired_count', 0) or 0)
    request_open_count = int((latest_cycle or {}).get('request_open_count', 0) or 0)
    request_inflight_count = int((latest_cycle or {}).get('request_inflight_count', 0) or 0)
    execution_request_reassigned_count = int((latest_cycle or {}).get('execution_request_reassigned_count', 0) or 0)
    execution_request_escalated_count = int((latest_cycle or {}).get('execution_request_escalated_count', 0) or 0)
    execution_request_retry_ready_count = int((latest_cycle or {}).get('execution_request_retry_ready_count', 0) or 0)
    top_request_states = list((latest_cycle or {}).get('top_request_states', []) or [])
    top_pending_requests = list((latest_cycle or {}).get('top_pending_requests', []) or [])
    recent_request_actions = list((latest_cycle or {}).get('recent_request_actions', []) or [])
    recent_request_transitions = list((latest_cycle or {}).get('recent_request_transitions', []) or [])
    recent_request_escalations = list((latest_cycle or {}).get('recent_request_escalations', []) or [])
    top_request_owners = list((latest_cycle or {}).get('top_request_owners', []) or [])
    adaptive_loop_count = int(adaptive_loop_summary.get('loop_count', 0) or 0)
    adaptive_decision_count = int(adaptive_loop_summary.get('total_adaptive_decisions', 0) or 0)
    adaptive_next_role_counts = adaptive_loop_summary.get('next_role_counts', {}) or {}
    adaptive_handoff_source_counts = adaptive_loop_summary.get('handoff_source_role_counts', {}) or {}
    dominant_next_role = adaptive_loop_summary.get('dominant_next_role')
    dominant_handoff_source_role = adaptive_loop_summary.get('dominant_handoff_source_role')
    dominant_decision_basis = adaptive_loop_summary.get('dominant_decision_basis')
    recent_learning_task_count = int(recent_learning_summary.get('recent_task_count', 0) or 0)
    recent_learning_role_counts = recent_learning_summary.get('expert_role_counts', {}) or {}
    recent_learning_signal_counts = recent_learning_summary.get('reusable_signal_counts', {}) or {}
    dominant_learning_role = recent_learning_summary.get('dominant_expert_role')
    open_gap_count = int(open_gap_summary.get('open_gap_count', 0) or 0)
    high_priority_gap_count = int(open_gap_summary.get('high_priority_gap_count', 0) or 0)
    top_gap_ids = open_gap_summary.get('top_gap_ids', []) or []
    observation_active_count = int(observation_runtime.get('active_count', 0) or 0)
    observation_pending_followup_count = int(observation_runtime.get('pending_followup_count', 0) or 0)
    observation_timed_out_count = int(observation_runtime.get('timed_out_count', 0) or 0)
    observation_overdue_count = int(observation_runtime.get('overdue_count', 0) or 0)
    latest_attention_observations = list(observation_runtime.get('latest_attention_items', []) or [])
    followup_queue = (observation_runtime.get('followup_queue') or {}) or {}
    followup_queue_count = int(followup_queue.get('queue_count', 0) or 0)
    followup_status_counts = followup_queue.get('status_counts', {}) or {}
    followup_open_count = int((followup_status_counts.get('open', observation_runtime.get('followup_open_count', 0)) or 0))
    followup_in_progress_count = int((followup_status_counts.get('in_progress', observation_runtime.get('followup_in_progress_count', 0)) or 0))
    followup_resolved_count = int((followup_status_counts.get('resolved', observation_runtime.get('followup_resolved_count', 0)) or 0))
    followup_closed_count = int((followup_status_counts.get('closed', observation_runtime.get('followup_closed_count', 0)) or 0))
    followup_escalation_counts = followup_queue.get('escalation_counts', {}) or {}
    followup_routing_target_counts = followup_queue.get('routing_target_counts', {}) or {}
    followup_assignment_counts = followup_queue.get('assignment_counts', {}) or {}
    followup_assigned_count = int(followup_queue.get('assigned_count', observation_runtime.get('followup_assigned_count', 0)) or 0)
    followup_unassigned_count = int(followup_queue.get('unassigned_count', observation_runtime.get('followup_unassigned_count', 0)) or 0)
    followup_handoff_count = int(followup_queue.get('handoff_count', observation_runtime.get('followup_handoff_count', 0)) or 0)
    followup_resolution_category_counts = followup_queue.get('resolution_category_counts', observation_runtime.get('followup_resolution_category_counts', {})) or {}
    recently_closed_followup_items = list(followup_queue.get('recently_closed_items', observation_runtime.get('recently_closed_followup_items', [])) or [])
    top_pending_followup_items = list(followup_queue.get('top_unresolved_items', followup_queue.get('top_items', [])) or [])
    followup_resolution_review = (latest_cycle or {}).get('followup_resolution_review', {}) or {}
    followup_backfilled_item_count = int(followup_resolution_review.get('backfilled_item_count', observation_runtime.get('followup_backfilled_item_count', 0)) or 0)
    followup_manual_classification_required_count = int(followup_resolution_review.get('manual_classification_required_count', observation_runtime.get('followup_manual_classification_required_count', 0)) or 0)
    manual_classification_backlog = (followup_resolution_review.get('manual_classification_backlog') or {})
    manual_classification_backlog_count = int(manual_classification_backlog.get('count', latest_cycle.get('manual_classification_backlog_count', 0)) or 0)
    manual_classification_unresolved_count = int(manual_classification_backlog.get('unresolved_count', latest_cycle.get('manual_classification_unresolved_count', 0)) or 0)
    manual_classification_state_counts = manual_classification_backlog.get('state_counts', latest_cycle.get('manual_classification_state_counts', {})) or {}
    followup_resolution_digest_available = bool(followup_resolution_review.get('digest_available', latest_cycle.get('followup_resolution_digest_available', False)))
    pattern_digest_available = bool(followup_resolution_review.get('pattern_digest_available', latest_cycle.get('pattern_digest_available', False)))
    followup_target_resolution_category_counts = followup_resolution_review.get('target_resolution_category_counts', latest_cycle.get('followup_target_resolution_category_counts', {})) or {}
    recent_closure_insights = list(followup_resolution_review.get('recent_closure_insights', []) or [])
    recent_closure_knowledge_themes = followup_resolution_review.get('recent_closure_knowledge_themes', latest_cycle.get('recent_closure_knowledge_themes', {})) or {}
    top_closure_themes = followup_resolution_review.get('top_closure_themes', latest_cycle.get('top_closure_themes', {})) or {}
    resolution_taxonomy_theme_counts = followup_resolution_review.get('resolution_taxonomy_theme_counts', latest_cycle.get('followup_resolution_taxonomy_theme_counts', {})) or {}
    pattern_digest_top = followup_resolution_review.get('pattern_digest_top', latest_cycle.get('pattern_digest_top', {})) or {}
    top_rule_candidates = followup_resolution_review.get('top_rule_candidates', latest_cycle.get('top_rule_candidates', {})) or {}
    top_pattern_candidates = followup_resolution_review.get('top_pattern_candidates', latest_cycle.get('top_pattern_candidates', {})) or {}
    theme_contrast = followup_resolution_review.get('theme_contrast', latest_cycle.get('theme_contrast', {})) or {}
    knowledge_candidate_counts = followup_resolution_review.get('knowledge_candidate_counts', latest_cycle.get('knowledge_candidate_counts', {})) or {}
    rule_proposal_review = (latest_cycle or {}).get('rule_proposal_review', {}) or {}
    rule_proposal_count = int(rule_proposal_review.get('proposal_count', latest_cycle.get('rule_proposal_count', 0)) or 0)
    rule_proposal_pending_review_count = int(rule_proposal_review.get('pending_review_count', latest_cycle.get('rule_proposal_pending_review_count', 0)) or 0)
    rule_proposal_accepted_count = int(rule_proposal_review.get('accepted_count', latest_cycle.get('rule_proposal_accepted_count', 0)) or 0)
    rule_proposal_rejected_count = int(rule_proposal_review.get('rejected_count', latest_cycle.get('rule_proposal_rejected_count', 0)) or 0)
    rule_proposal_state_counts = rule_proposal_review.get('proposal_state_counts', latest_cycle.get('rule_proposal_state_counts', {})) or {}
    top_proposed_rules = list(rule_proposal_review.get('top_proposed_rules', latest_cycle.get('top_proposed_rules', [])) or [])
    governed_rule_sink = (latest_cycle or {}).get('governed_rule_sink', {}) or {}
    rule_sink_ready_count = int(governed_rule_sink.get('sink_ready_count', latest_cycle.get('rule_sink_ready_count', rule_proposal_accepted_count)) or 0)
    written_rule_candidate_count = int(governed_rule_sink.get('written_count', latest_cycle.get('written_rule_candidate_count', 0)) or 0)
    governed_rule_state_counts = governed_rule_sink.get('state_counts', latest_cycle.get('governed_rule_state_counts', {})) or {}
    top_written_rules = list(governed_rule_sink.get('top_written_rules', latest_cycle.get('top_written_rules', [])) or [])
    local_rulebook_export = (latest_cycle or {}).get('local_rulebook_export', {}) or {}
    local_rulebook_exported_count = int(local_rulebook_export.get('exported_count', latest_cycle.get('local_rulebook_exported_count', 0)) or 0)
    local_rulebook_item_count = int(local_rulebook_export.get('local_rulebook_item_count', latest_cycle.get('local_rulebook_item_count', 0)) or 0)
    local_rulebook_export_audit_available = bool(local_rulebook_export.get('export_audit_available', latest_cycle.get('local_rulebook_export_audit_available', False)))
    local_rulebook_export_status_counts = local_rulebook_export.get('export_status_counts', latest_cycle.get('local_rulebook_export_status_counts', {})) or {}
    local_rulebook_duplicate_blocked_count = int(local_rulebook_export.get('duplicate_blocked_count', latest_cycle.get('local_rulebook_duplicate_blocked_count', 0)) or 0)
    local_rulebook_active_rule_count = int(local_rulebook_export.get('active_rule_count', latest_cycle.get('local_rulebook_active_rule_count', 0)) or 0)
    local_rulebook_inactive_rule_count = int(local_rulebook_export.get('inactive_rule_count', latest_cycle.get('local_rulebook_inactive_rule_count', 0)) or 0)
    local_rulebook_archived_rule_count = int(local_rulebook_export.get('archived_rule_count', latest_cycle.get('local_rulebook_archived_rule_count', 0)) or 0)
    local_rulebook_merged_rule_count = int(local_rulebook_export.get('merged_rule_count', latest_cycle.get('local_rulebook_merged_rule_count', 0)) or 0)
    local_rulebook_superseded_rule_count = int(local_rulebook_export.get('superseded_rule_count', latest_cycle.get('local_rulebook_superseded_rule_count', 0)) or 0)
    local_rulebook_consequence_state_counts = local_rulebook_export.get('consequence_state_counts', latest_cycle.get('local_rulebook_consequence_state_counts', {})) or {}
    local_rulebook_merge_candidate_count = int(local_rulebook_export.get('merge_candidate_count', latest_cycle.get('local_rulebook_merge_candidate_count', 0)) or 0)
    local_rulebook_conflict_candidate_count = int(local_rulebook_export.get('conflict_candidate_count', latest_cycle.get('local_rulebook_conflict_candidate_count', 0)) or 0)
    local_rulebook_duplicate_candidate_count = int(local_rulebook_export.get('duplicate_candidate_count', latest_cycle.get('local_rulebook_duplicate_candidate_count', 0)) or 0)
    merge_queue_count = int(local_rulebook_export.get('merge_queue_count', latest_cycle.get('merge_queue_count', 0)) or 0)
    merge_queue_state_counts = local_rulebook_export.get('merge_queue_state_counts', latest_cycle.get('merge_queue_state_counts', {})) or {}
    merge_queue_open_count = int(local_rulebook_export.get('merge_queue_open_count', latest_cycle.get('merge_queue_open_count', 0)) or 0)
    merge_queue_reviewing_count = int(local_rulebook_export.get('merge_queue_reviewing_count', latest_cycle.get('merge_queue_reviewing_count', 0)) or 0)
    merge_queue_accepted_count = int(local_rulebook_export.get('merge_queue_accepted_count', latest_cycle.get('merge_queue_accepted_count', 0)) or 0)
    merge_queue_rejected_count = int(local_rulebook_export.get('merge_queue_rejected_count', latest_cycle.get('merge_queue_rejected_count', 0)) or 0)
    top_exported_rules = list(local_rulebook_export.get('top_exported_rules', latest_cycle.get('top_exported_rules', [])) or [])
    top_merge_targets = list(local_rulebook_export.get('top_merge_targets', latest_cycle.get('top_merge_targets', [])) or [])
    top_supersede_suggestions = list(local_rulebook_export.get('top_supersede_suggestions', latest_cycle.get('top_supersede_suggestions', [])) or [])
    top_supersede_candidates = list(local_rulebook_export.get('top_supersede_candidates', latest_cycle.get('top_supersede_candidates', [])) or [])
    top_merge_items = list(local_rulebook_export.get('top_merge_items', latest_cycle.get('top_merge_items', [])) or [])
    top_conflict_items = list(local_rulebook_export.get('top_conflict_items', latest_cycle.get('top_conflict_items', [])) or [])
    recent_adjudications = list(local_rulebook_export.get('recent_adjudications', latest_cycle.get('recent_adjudications', [])) or [])
    conflict_resolution_type_counts = local_rulebook_export.get('conflict_resolution_type_counts', latest_cycle.get('conflict_resolution_type_counts', {})) or {}
    recent_consequence_updates = list(local_rulebook_export.get('recent_consequence_updates', latest_cycle.get('recent_consequence_updates', [])) or [])
    consequence_history_available = bool(local_rulebook_export.get('consequence_history_available', latest_cycle.get('consequence_history_available', False)))
    consequence_history_event_count = int(local_rulebook_export.get('consequence_history_event_count', latest_cycle.get('consequence_history_event_count', 0)) or 0)
    recent_consequence_transitions = list(local_rulebook_export.get('recent_consequence_transitions', latest_cycle.get('recent_consequence_transitions', [])) or [])
    transition_ledger_available = bool(local_rulebook_export.get('transition_ledger_available', latest_cycle.get('transition_ledger_available', False)))
    transition_event_count = int(local_rulebook_export.get('transition_event_count', latest_cycle.get('transition_event_count', 0)) or 0)
    unique_semantic_event_count = int(local_rulebook_export.get('unique_semantic_event_count', latest_cycle.get('unique_semantic_event_count', 0)) or 0)
    digest_duplicate_semantic_event_count = int(local_rulebook_export.get('digest_duplicate_semantic_event_count', latest_cycle.get('digest_duplicate_semantic_event_count', 0)) or 0)
    transition_duplicate_suppressed_count = int(local_rulebook_export.get('transition_duplicate_suppressed_count', latest_cycle.get('transition_duplicate_suppressed_count', 0)) or 0)
    transition_digest_review_available = bool(local_rulebook_export.get('transition_digest_review_available', latest_cycle.get('transition_digest_review_available', False)))
    recent_transition_events = list(local_rulebook_export.get('recent_transition_events', latest_cycle.get('recent_transition_events', [])) or [])
    recent_suppressed_events = list(local_rulebook_export.get('recent_suppressed_events', latest_cycle.get('recent_suppressed_events', [])) or [])
    top_transition_triggers = local_rulebook_export.get('top_transition_triggers', latest_cycle.get('top_transition_triggers', {})) or {}
    consistency_audit_available = bool(local_rulebook_export.get('consistency_audit_available', latest_cycle.get('consistency_audit_available', False)))
    audit_scope_refinement_available = bool(local_rulebook_export.get('audit_scope_refinement_available', latest_cycle.get('audit_scope_refinement_available', False)))
    registry_sync_review_available = bool(local_rulebook_export.get('registry_sync_review_available', latest_cycle.get('registry_sync_review_available', False)))
    registry_sync_issue_count = int(local_rulebook_export.get('registry_sync_issue_count', latest_cycle.get('registry_sync_issue_count', 0)) or 0)
    sync_scope_exception_count = int(local_rulebook_export.get('sync_scope_exception_count', latest_cycle.get('sync_scope_exception_count', 0)) or 0)
    scope_exception_counts = local_rulebook_export.get('scope_exception_counts', latest_cycle.get('scope_exception_counts', {})) or {}
    recent_sync_issues = list(local_rulebook_export.get('recent_sync_issues', latest_cycle.get('recent_sync_issues', [])) or [])
    recent_scope_exceptions = list(local_rulebook_export.get('recent_scope_exceptions', latest_cycle.get('recent_scope_exceptions', [])) or [])
    archived_transition_count = int(local_rulebook_export.get('archived_transition_count', latest_cycle.get('archived_transition_count', 0)) or 0)
    recent_archived_items = list(local_rulebook_export.get('recent_archived_items', latest_cycle.get('recent_archived_items', [])) or [])
    archive_policy_counts = local_rulebook_export.get('archive_policy_counts', latest_cycle.get('archive_policy_counts', {})) or {}
    archived_restorable_count = int(local_rulebook_export.get('archived_restorable_count', latest_cycle.get('archived_restorable_count', 0)) or 0)
    archived_reopened_count = int(local_rulebook_export.get('archived_reopened_count', latest_cycle.get('archived_reopened_count', 0)) or 0)
    restore_count = int(local_rulebook_export.get('restore_count', latest_cycle.get('restore_count', 0)) or 0)
    reopen_count = int(local_rulebook_export.get('reopen_count', latest_cycle.get('reopen_count', 0)) or 0)
    revive_count = int(local_rulebook_export.get('revive_count', latest_cycle.get('revive_count', 0)) or 0)
    restore_state_counts = local_rulebook_export.get('restore_state_counts', latest_cycle.get('restore_state_counts', {})) or {}
    shared_source_archived_count = int(local_rulebook_export.get('shared_source_archived_count', latest_cycle.get('shared_source_archived_count', 0)) or 0)
    recent_restore_actions = list(local_rulebook_export.get('recent_restore_actions', latest_cycle.get('recent_restore_actions', [])) or [])
    recent_restore_timeline = list(local_rulebook_export.get('recent_restore_timeline', latest_cycle.get('recent_restore_timeline', [])) or [])
    recent_archive_actions = list(local_rulebook_export.get('recent_archive_actions', latest_cycle.get('recent_archive_actions', [])) or [])
    precedence_decision_count = int(local_rulebook_export.get('precedence_decision_count', latest_cycle.get('precedence_decision_count', 0)) or 0)
    precedence_override_counts = local_rulebook_export.get('precedence_override_counts', latest_cycle.get('precedence_override_counts', {})) or {}
    recent_precedence_decisions = list(local_rulebook_export.get('recent_precedence_decisions', latest_cycle.get('recent_precedence_decisions', [])) or [])
    conflict_state_counts = local_rulebook_export.get('conflict_state_counts', latest_cycle.get('conflict_state_counts', {})) or {}
    conflict_open_count = int(local_rulebook_export.get('conflict_open_count', latest_cycle.get('conflict_open_count', 0)) or 0)
    conflict_reviewing_count = int(local_rulebook_export.get('conflict_reviewing_count', latest_cycle.get('conflict_reviewing_count', 0)) or 0)
    conflict_resolved_count = int(local_rulebook_export.get('conflict_resolved_count', latest_cycle.get('conflict_resolved_count', 0)) or 0)
    top_duplicate_items = list(local_rulebook_export.get('top_duplicate_items', latest_cycle.get('top_duplicate_items', [])) or [])
    post_decision_linkage_count = int(local_rulebook_export.get('post_decision_linkage_count', latest_cycle.get('post_decision_linkage_count', 0)) or 0)
    merge_linked_count = int(local_rulebook_export.get('merge_linked_count', latest_cycle.get('merge_linked_count', 0)) or 0)
    supersede_linked_count = int(local_rulebook_export.get('supersede_linked_count', latest_cycle.get('supersede_linked_count', 0)) or 0)
    conflict_adjudicated_linked_count = int(local_rulebook_export.get('conflict_adjudicated_linked_count', latest_cycle.get('conflict_adjudicated_linked_count', 0)) or 0)
    recent_decision_linkages = list(local_rulebook_export.get('recent_decision_linkages', latest_cycle.get('recent_decision_linkages', [])) or [])
    formalization_observable = bool(formalization_counts)
    closure_visible = closure_visible_count > 0

    if official_release_rehearsal_ready_count > 0 or (pre_release_ready_count > 0 and closure_consistency_ready_count > 0):
        closure_readiness_state = 'approvable_candidates_present'
    elif pre_release_ready_count > 0 or (release_ready_candidates > 0 and approval_required_count > 0):
        closure_readiness_state = 'observable'
    elif closure_visible:
        closure_readiness_state = 'observable'
    else:
        closure_readiness_state = 'none'

    skeleton = 88
    agent_depth = 62
    runtime = 72 if latest_cycle else 45
    if stale_count == 0 and latest_cycle:
        runtime += 6
    if governance_action_count == 0 and latest_cycle:
        runtime += 2
    formalization = 48
    if release_ready_candidates > 0:
        formalization += 10
    if manual_review_gates > 0:
        formalization += 4
    if closure_visible:
        formalization += 4
    if closure_readiness_state == 'approvable_candidates_present':
        formalization += 4
    evaluation = 46 if quality_observable else 34

    capability_axes = {
        'skeleton': _clamp(skeleton),
        'agent_depth': _clamp(agent_depth),
        'runtime': _clamp(runtime),
        'formalization': _clamp(formalization),
        'evaluation': _clamp(evaluation),
    }

    stage_id = 'strong-skeleton-midphase'
    stage_label = '强骨架 + 关键深化 + 最小持续运行化 + 收口边界建立'
    maturity_band = 'mid'

    approval_signal_summary = ''
    if approval_required_count > 0:
        approval_signal_summary = (
            f' 当前审批观察面显示：等待审批={awaiting_approval_count}、已批准={approved_count}、已拒绝={rejected_count}；'
            '真实外部人工审批仍未接入。'
        )
    adaptive_signal_summary = ''
    if adaptive_decision_count > 0:
        adaptive_signal_summary = (
            f' 最近自适应流转已记录 {adaptive_decision_count} 次选路，'
            f'下一责任角色分布={_translate_count_keys(adaptive_next_role_counts, ROLE_NAME_ZH)}，'
            f'任务来源分布={_translate_count_keys(adaptive_handoff_source_counts, ROLE_NAME_ZH)}。'
        )
        if dominant_next_role:
            adaptive_signal_summary += (
                f' 当前主导流向={ROLE_NAME_ZH.get(dominant_next_role, dominant_next_role)}'
                + (f'，主导依据={dominant_decision_basis}' if dominant_decision_basis else '')
                + (f'，主要来源={ROLE_NAME_ZH.get(dominant_handoff_source_role, dominant_handoff_source_role)}' if dominant_handoff_source_role else '')
                + '。'
            )
    recent_learning_signal_summary = ''
    if recent_learning_task_count > 0:
        recent_learning_signal_summary = (
            f' 最近已沉淀 {recent_learning_task_count} 个专家产物样本，角色分布={_translate_count_keys(recent_learning_role_counts, ROLE_NAME_ZH)}，'
            f'可复用信号分布={recent_learning_signal_counts}'
            + (f'，当前主导沉淀角色={ROLE_NAME_ZH.get(dominant_learning_role, dominant_learning_role)}' if dominant_learning_role else '')
            + '。'
        )
    observation_signal_summary = ''
    if observation_active_count or observation_pending_followup_count or observation_timed_out_count or observation_overdue_count or followup_queue_count:
        observation_signal_summary = (
            f' 观察刷新汇总：活跃 observation={observation_active_count}，待人工跟进={observation_pending_followup_count}，'
            f'已超时={observation_timed_out_count}，已逾期={observation_overdue_count}，follow-up queue={followup_queue_count}，'
            f'open={followup_open_count} / in_progress={followup_in_progress_count} / resolved={followup_resolved_count} / closed={followup_closed_count}，'
            f'assigned={followup_assigned_count} / unassigned={followup_unassigned_count} / handoff={followup_handoff_count}。'
        )
        if followup_escalation_counts:
            observation_signal_summary += f' escalation 分布={followup_escalation_counts}。'
        if followup_routing_target_counts:
            observation_signal_summary += f' routing 分布={followup_routing_target_counts}。'
        if followup_resolution_category_counts:
            observation_signal_summary += f' resolution 分布={followup_resolution_category_counts}。'
        if followup_target_resolution_category_counts:
            observation_signal_summary += f' target-resolution 分布={followup_target_resolution_category_counts}。'
        if followup_backfilled_item_count or followup_manual_classification_required_count or manual_classification_backlog_count:
            observation_signal_summary += (
                f' 历史回填修复={followup_backfilled_item_count}，'
                f'待人工补分类={followup_manual_classification_required_count}，'
                f'manual backlog={manual_classification_backlog_count}，'
                f'未解决补分类项={manual_classification_unresolved_count}。'
            )
            if manual_classification_state_counts:
                observation_signal_summary += f' manual classification states={manual_classification_state_counts}。'
        if followup_resolution_digest_available:
            observation_signal_summary += ' resolution insight digest 已可用。'
        if pattern_digest_available:
            observation_signal_summary += ' pattern digest 已可用。'
        if recent_closure_knowledge_themes:
            observation_signal_summary += f' closure theme counts={recent_closure_knowledge_themes}。'
        if top_closure_themes:
            observation_signal_summary += f' top closure themes={top_closure_themes}。'
        if resolution_taxonomy_theme_counts:
            observation_signal_summary += f' taxonomy themes={resolution_taxonomy_theme_counts}。'
        if pattern_digest_top:
            observation_signal_summary += f' top patterns={pattern_digest_top}。'
        if top_rule_candidates:
            observation_signal_summary += f' top rule candidates={top_rule_candidates}。'
        if top_pattern_candidates:
            observation_signal_summary += f' top pattern candidates={top_pattern_candidates}。'
        if rule_proposal_count:
            observation_signal_summary += (
                f' rule proposals={rule_proposal_count}，待审核={rule_proposal_pending_review_count}，'
                f'accepted={rule_proposal_accepted_count}，rejected={rule_proposal_rejected_count}。'
            )
        if top_proposed_rules:
            observation_signal_summary += f' top proposed rules={top_proposed_rules[:3]}。'
        if rule_sink_ready_count or written_rule_candidate_count:
            observation_signal_summary += (
                f' sink-ready={rule_sink_ready_count}，written rule candidates={written_rule_candidate_count}'
                + (f'，governed rule states={governed_rule_state_counts}' if governed_rule_state_counts else '')
                + '。'
            )
        if top_written_rules:
            observation_signal_summary += f' top written rules={top_written_rules[:3]}。'
        if local_rulebook_exported_count or local_rulebook_item_count or local_rulebook_export_audit_available or local_rulebook_active_rule_count or local_rulebook_superseded_rule_count or local_rulebook_duplicate_blocked_count or local_rulebook_merge_candidate_count or local_rulebook_conflict_candidate_count or local_rulebook_duplicate_candidate_count:
            observation_signal_summary += (
                f' local rulebook exported={local_rulebook_exported_count}，local rulebook items={local_rulebook_item_count}，'
                f'active={local_rulebook_active_rule_count}，inactive={local_rulebook_inactive_rule_count}，archived={local_rulebook_archived_rule_count}，merged={local_rulebook_merged_rule_count}，superseded={local_rulebook_superseded_rule_count}，duplicate_blocked={local_rulebook_duplicate_blocked_count}，'
                f'merge_candidates={local_rulebook_merge_candidate_count}，conflict_candidates={local_rulebook_conflict_candidate_count}，duplicate_like_candidates={local_rulebook_duplicate_candidate_count}，'
                f'merge_queue={merge_queue_count}，merge_queue_open/reviewing/accepted/rejected={merge_queue_open_count}/{merge_queue_reviewing_count}/{merge_queue_accepted_count}/{merge_queue_rejected_count}，'
                f'export audit available={local_rulebook_export_audit_available}'
                + (f'，export status counts={local_rulebook_export_status_counts}' if local_rulebook_export_status_counts else '')
                + '。'
            )
        if top_exported_rules:
            observation_signal_summary += f' top exported rules={top_exported_rules[:3]}。'
        if top_merge_targets:
            observation_signal_summary += f' top merge targets={top_merge_targets[:3]}。'
        if top_supersede_suggestions:
            observation_signal_summary += f' top supersede suggestions={top_supersede_suggestions[:3]}。'
        if top_supersede_candidates:
            observation_signal_summary += f' top supersede candidates={top_supersede_candidates[:3]}。'
        if top_merge_items:
            observation_signal_summary += f' top merge items={top_merge_items[:3]}。'
        if top_conflict_items:
            observation_signal_summary += f' top conflict items={top_conflict_items[:3]}。'
        if conflict_state_counts:
            observation_signal_summary += f' conflict states={conflict_state_counts}，open/reviewing/resolved={conflict_open_count}/{conflict_reviewing_count}/{conflict_resolved_count}。'
        if recent_adjudications:
            observation_signal_summary += f' recent adjudications={recent_adjudications[:3]}。'
        if local_rulebook_consequence_state_counts:
            observation_signal_summary += f' consequence states={local_rulebook_consequence_state_counts}。'
        if conflict_resolution_type_counts:
            observation_signal_summary += f' conflict resolution types={conflict_resolution_type_counts}。'
        if consequence_history_available:
            observation_signal_summary += f' consequence history available={consequence_history_available}，events={consequence_history_event_count}。'
        if transition_ledger_available:
            observation_signal_summary += f' transition ledger available={transition_ledger_available}，event_count={transition_event_count}，unique_semantic_events={unique_semantic_event_count}，digest_duplicate_events={digest_duplicate_semantic_event_count}，suppressed_duplicates={transition_duplicate_suppressed_count}，digest_review_available={transition_digest_review_available}。'
        if recent_suppressed_events:
            observation_signal_summary += f' recent suppressed transition events={recent_suppressed_events[:3]}。'
        if consistency_audit_available:
            observation_signal_summary += f' consistency audit available={consistency_audit_available}，registry_sync_issue_count={registry_sync_issue_count}，sync_scope_exception_count={sync_scope_exception_count}。'
        if audit_scope_refinement_available or registry_sync_review_available:
            observation_signal_summary += f' audit scope refinement available={audit_scope_refinement_available}，registry-sync review available={registry_sync_review_available}' + (f'，scope_exception_counts={scope_exception_counts}' if scope_exception_counts else '') + '。'
        if recent_sync_issues:
            observation_signal_summary += f' recent sync issues={recent_sync_issues[:3]}。'
        if recent_scope_exceptions:
            observation_signal_summary += f' recent sync scope exceptions={recent_scope_exceptions[:3]}。'
        if recent_consequence_updates:
            observation_signal_summary += f' recent consequence updates={recent_consequence_updates[:3]}。'
        if recent_consequence_transitions:
            observation_signal_summary += f' recent consequence transitions={recent_consequence_transitions[:3]}。'
        if recent_transition_events:
            observation_signal_summary += f' recent transition events={recent_transition_events[:3]}。'
        if top_transition_triggers:
            observation_signal_summary += f' top transition triggers={top_transition_triggers}。'
        if top_duplicate_items:
            observation_signal_summary += f' top duplicate-like items={top_duplicate_items[:3]}。'
        if post_decision_linkage_count:
            observation_signal_summary += (
                f' post-decision linkage={post_decision_linkage_count}，merge-linked={merge_linked_count}，'
                f'supersede-linked={supersede_linked_count}，conflict-adjudicated-linked={conflict_adjudicated_linked_count}。'
            )
        if recent_decision_linkages:
            observation_signal_summary += f' recent decision linkages={recent_decision_linkages[:3]}。'
        if theme_contrast:
            observation_signal_summary += f' release/rollback contrast={theme_contrast}。'
        if recently_closed_followup_items:
            latest_closed = recently_closed_followup_items[0]
            latest_closed_category = latest_closed.get('followup_resolution_category') or ('needs_manual_classification' if latest_closed.get('manual_classification_required') else 'unclassified')
            observation_signal_summary += f" 最近关闭={latest_closed.get('task_id')}:{latest_closed_category}。"
        elif recent_closure_insights:
            latest_closed = recent_closure_insights[0]
            observation_signal_summary += f" 最近关闭={latest_closed.get('task_id')}:{latest_closed.get('resolution_category')}。"
        if top_pending_followup_items:
            top_item = top_pending_followup_items[0]
            observation_signal_summary += (
                f' 顶部待跟进项={top_item.get("task_id")} / {top_item.get("execution_target")}，'
                f'升级级别={top_item.get("escalation_level")}，建议路由={top_item.get("recommended_routing_target")}。'
            )
        elif latest_attention_observations:
            latest_attention = latest_attention_observations[0]
            observation_signal_summary += (
                f' 最近关注 observation={latest_attention.get("task_id")} / {latest_attention.get("execution_target")}，'
                f'状态={latest_attention.get("observation_state")}，SLA={latest_attention.get("sla_state")}。'
            )
    executor_signal_summary = ''
    if executor_contract_available_count or dry_run_available_count or execution_receipt_protocol_available_count or handoff_packet_available_count or operator_execution_request_available_count or receipt_correlation_ready_count or executor_adapter_available_count or executor_capability_registry_available or invocation_policy_available or executor_conformance_available or executor_error_contract_available or release_rollback_parity_available or implementation_blueprint_available:
        executor_signal_summary = (
            f' 受控执行器观察面：contract={executor_contract_available_count}，dry-run={dry_run_available_count}，'
            f'receipt_protocol={execution_receipt_protocol_available_count}，handoff_packet={handoff_packet_available_count}，operator_request={operator_execution_request_available_count}，receipt_correlation_ready={receipt_correlation_ready_count}，readiness_review={executor_readiness_review_available_count}，'
            f'adapter_count={executor_adapter_available_count}，capability_registry={executor_capability_registry_available}，invocation_policy={invocation_policy_available}，environment_guard_ok={environment_guard_ok_count}，environment_guard_unmet={environment_guard_unmet_count}，top_executor_adapter_types={top_executor_adapter_types or []}，handoff_boundary_ready={handoff_boundary_ready_count}，executor_readiness_gate_count={executor_readiness_gate_count}，'
            f'executor_unmet_gate_count={executor_unmet_gate_count}，executor_admission_available={executor_admission_available}，go_no_go_available={go_no_go_available}，rollout_gate_count={rollout_gate_count}，rollout_unmet_count={rollout_unmet_count}，waiver_exception_count={waiver_exception_count}，overall_admission_state={overall_admission_state}，top_blocking_gates={top_blocking_gates or []}，executor_simulation_available_count={executor_simulation_available_count}，executor_simulation_pass_count={executor_simulation_pass_count}，executor_simulation_fail_count={executor_simulation_fail_count}，contract_compliance_available={contract_compliance_available}，integration_rehearsal_available={integration_rehearsal_available}，top_executor_contract_gaps={top_executor_contract_gaps or []}，top_unmet_executor_gates={top_unmet_executor_gates or []}，top_execution_handoff_targets={top_execution_handoff_targets or []}，top_command_plan_steps={top_command_plan_steps or []}，'
            f'requested={execution_request_requested_count}，acknowledged={execution_request_acknowledged_count}，accepted={execution_request_accepted_count}，declined={execution_request_declined_count}，expired={execution_request_expired_count}，open={request_open_count}，inflight={request_inflight_count}，reassigned={execution_request_reassigned_count}，escalated={execution_request_escalated_count}，retry_ready={execution_request_retry_ready_count}，top_request_states={top_request_states or []}，top_pending_requests={top_pending_requests[:3] or []}，recent_request_transitions={recent_request_transitions[:3] or []}，recent_request_escalations={recent_request_escalations[:3] or []}，top_request_owners={top_request_owners or []}，'
            f'release_requested={release_execution_requested_count}，rollback_requested={rollback_execution_requested_count}，'
            f'release_receipt={release_execution_receipt_recorded_count}，rollback_receipt={rollback_execution_receipt_recorded_count}，'
            f'executor_conformance_available={executor_conformance_available}，executor_error_contract_available={executor_error_contract_available}，release_rollback_parity_available={release_rollback_parity_available}，implementation_blueprint_available={implementation_blueprint_available}，top_missing_executor_contracts={top_missing_executor_contracts or []}，parity_gaps={parity_gaps or []}。'
        )
    gap_signal_summary = ''
    if open_gap_count > 0:
        top_gap_names = [GAP_ID_ZH.get(item, item) for item in top_gap_ids]
        top_gap_names_text = '；'.join(str(item) for item in top_gap_names) if top_gap_names else '无'
        gap_signal_summary = f' 当前正式登记的骨架缺口共 {open_gap_count} 项，其中高优先级 {high_priority_gap_count} 项，当前首要缺口={top_gap_names_text}。'
        if official_release_pipeline_visible_count > 0:
            gap_signal_summary += (
                f' 正式发布管线状态分布={_translate_count_keys(official_release_focus.get("state_counts_zh") or {}, {}) or official_release_focus.get("state_counts_zh")}，'
                f'主导卡点={official_release_focus.get("focus_label_zh")}，'
                f'当前聚焦={official_release_focus.get("title")}，'
                f'阻塞分布={official_release_focus.get("blocker_counts_zh")}，'
                f'可执行计数={official_release_pipeline_executable_count}。'
            )
    summary = (
        '系统已完成强骨架建设，并进入关键智能体深化、最小持续运行化、正式收口边界'
        '与最小评分骨架并行推进阶段；当前不应表述为最终完工生态。'
        + approval_signal_summary
        + adaptive_signal_summary
        + recent_learning_signal_summary
        + observation_signal_summary
        + executor_signal_summary
        + gap_signal_summary
    )

    completion_definition = {
        'runtime_observable': bool(latest_cycle),
        'stale_control_stable': stale_count == 0,
        'quality_observable': quality_observable,
        'formalization_observable': formalization_observable,
        'closure_visible': closure_visible,
        'closure_readiness_state': closure_readiness_state,
        'manual_gate_defined': True,
        'phase_complete_when': [
            '持续运行化可稳定输出 latest cycle 与三层 dashboard',
            '至少一批新任务经过新版 quality_score 产出链路',
            '至少一批新任务经过 formalization_gate 链路',
            '阶段卡能基于真实历史数据而非仅骨架信号判断阶段',
        ],
    }

    if completion_definition['runtime_observable'] and completion_definition['stale_control_stable'] and completion_definition['quality_observable'] and completion_definition['formalization_observable']:
        phase_completion_state = 'ready_for_next_phase'
    elif completion_definition['runtime_observable'] and completion_definition['stale_control_stable']:
        phase_completion_state = 'mostly_ready_for_next_phase'
    else:
        phase_completion_state = 'in_progress'

    if adaptive_decision_count > 0 and dominant_next_role:
        title_map = {
            'strategy-expert': '优先强化策略逻辑线',
            'parameter-evolver': '优先强化参数稳健化线',
            'factor-miner': '优先强化因子挖掘线',
        }
        action_map = {
            'strategy-expert': [
                '继续补 strategy-expert 对当前代码触点、方案比较与验证优先级的约束',
                '重点检查 handoff 是否已把“为什么回到策略层”讲清楚',
                '让后续 adaptive loop 继续验证策略改写是否真的改善 trade count / drawdown / return quality',
            ],
            'parameter-evolver': [
                '继续补 parameter-evolver 对参数触点、稳健区间依据和 guardrail 的约束',
                '重点检查 handoff 是否已把“为什么先调参数”讲清楚',
                '让后续 adaptive loop 继续验证参数调整是否真的改善 drawdown / Sharpe / trade count',
            ],
            'factor-miner': [
                '继续补 factor-miner 对因子适用条件、代码触点和 strategy/parameter handoff 的约束',
                '重点检查 handoff 是否已把“为什么先走因子线”讲清楚',
                '让后续 adaptive loop 继续验证因子探索是否真的提升 return quality 而非只增加复杂度',
            ],
        }
        next_action_card = {
            'priority': 'high',
            'title': title_map.get(dominant_next_role, '优先强化当前主导 adaptive 路径'),
            'why_now': (
                f'近期 adaptive loop 的主导流向是 {dominant_next_role}'
                + (f'，主导依据为 {dominant_decision_basis}' if dominant_decision_basis else '')
                + (f'，主要由 {dominant_handoff_source_role} 产物推动' if dominant_handoff_source_role else '')
                + '；因此下一步应优先把这条线继续做深，而不是平均撒网。'
            ),
            'recommended_actions': action_map.get(dominant_next_role, [
                '继续观察 adaptive loop 的下一环分布，识别当前真正的主导优化线',
                '围绕主导 handoff 来源继续补深对应专家产物',
                '确保看板与 loop report 能解释“为什么选了这一环”',
            ]),
        }
    elif open_gap_count > 0 and top_gap_ids:
        top_gap = top_gap_ids[0]
        gap_action_map = {
            'official_release_pipeline': {
                'title': official_release_focus.get('title', '优先补 official release / rollback 闭环'),
                'why_now': official_release_focus.get('why_now', '当前 top gap 指向 official release pipeline，说明骨架虽已成型，但正式发布/回滚仍停留在骨架层。'),
                'recommended_actions': official_release_focus.get('recommended_actions', [
                    '继续推进 official release action 从 stub 走向可执行前检查链',
                    '继续补 rollback registry 与 release artifact 的真实一致性校验',
                    '让 stage card / closure summary 明确区分“可观察”与“可执行”边界',
                ]),
                'focus_label': official_release_focus.get('focus_label'),
                'focus_label_zh': official_release_focus.get('focus_label_zh'),
                'dominant_state': official_release_focus.get('dominant_state'),
                'dominant_state_zh': official_release_focus.get('dominant_state_zh'),
                'blocker_counts': official_release_focus.get('blocker_counts', {}),
                'blocker_counts_zh': official_release_focus.get('blocker_counts_zh', {}),
                'state_counts': official_release_focus.get('state_counts', {}),
                'state_counts_zh': official_release_focus.get('state_counts_zh', {}),
            },
            'real_human_approval': {
                'title': '优先补真实人工审批闭环',
                'why_now': '当前 top gap 指向真实人工审批，说明审批三态虽然已可观察，但真实 approve/reject 输入仍未接入执行路径。',
                'recommended_actions': [
                    '继续补真实人工 approve/reject 输入接口或记录入口',
                    '让 approval result 真正驱动 release execution / rollback 分支',
                    '继续在看板层区分 awaiting 与真实 reject/approve 的行为差异',
                ],
            },
            'adaptive_loop_depth': {
                'title': '优先补 adaptive loop 真实样本深度',
                'why_now': '当前 top gap 指向 adaptive loop depth，说明虽然 loop 已能消费 richer hints，但真实多轮流转样本仍偏少。',
                'recommended_actions': [
                    '继续跑通更多 cross-worker adaptive loop 样本',
                    '重点检查多轮 strategy / parameter / factor 切换是否稳定可解释',
                    '让 adaptive trace 与 stage card 继续沉淀更多真实样本',
                ],
            },
            'recent_learning_density': {
                'title': '优先补近期经验沉淀密度',
                'why_now': '当前 top gap 指向 recent learning density，说明反哺链路已打通，但可复用样本还不够厚。',
                'recommended_actions': [
                    '继续补通过验收的 strategy / parameter / factor 真实样本',
                    '提高 recent learning 面板的样本覆盖与信号密度',
                    '让下一轮 master / loop 更多引用真实样本而不是骨架默认值',
                ],
            },
            'benchmark_regression': {
                'title': '优先补 benchmark / regression 体系',
                'why_now': '当前 top gap 指向 benchmark/regression，说明系统已具备 richer outputs，但更深评测基线还没补齐。',
                'recommended_actions': [
                    '继续补 benchmark / regression 基线与回归样本',
                    '让专家产物与 adaptive loop 的收益通过更稳定评测来验证',
                    '把 benchmark 结果继续接回 quality / stage card 观察面',
                ],
            },
            'supervisor_runtime': {
                'title': '优先补常驻托管闭环',
                'why_now': '当前 top gap 指向 supervisor/runtime，说明 scheduler 已可跑，但长期常驻托管与恢复策略仍未闭合。',
                'recommended_actions': [
                    '继续补 supervisor/systemd 级托管与恢复策略',
                    '明确 worker runtime 的常驻运行与故障恢复边界',
                    '把常驻托管状态继续接回 runtime summary',
                ],
            },
        }
        selected_gap = gap_action_map.get(top_gap, {})
        next_action_card = {
            'priority': 'high',
            'title': selected_gap.get('title', '优先补当前 top gap'),
            'why_now': selected_gap.get('why_now', f'当前 top gap={top_gap}，因此下一步应优先围绕这个骨架缺口收口。'),
            'recommended_actions': selected_gap.get('recommended_actions', [
                '优先围绕 top gap 做定向收口，而不是平均撒网',
                '把 top gap 的收口结果继续接回 runtime summary 与 stage card',
                '确保 gap summary 会随着真实状态变化自动更新',
            ]),
        }
        if selected_gap.get('focus_label'):
            next_action_card['focus_label'] = selected_gap.get('focus_label')
        if selected_gap.get('focus_label_zh'):
            next_action_card['focus_label_zh'] = selected_gap.get('focus_label_zh')
        if selected_gap.get('dominant_state'):
            next_action_card['dominant_state'] = selected_gap.get('dominant_state')
        if selected_gap.get('dominant_state_zh'):
            next_action_card['dominant_state_zh'] = selected_gap.get('dominant_state_zh')
        if selected_gap.get('blocker_counts'):
            next_action_card['blocker_counts'] = selected_gap.get('blocker_counts')
        if selected_gap.get('blocker_counts_zh'):
            next_action_card['blocker_counts_zh'] = selected_gap.get('blocker_counts_zh')
        if selected_gap.get('state_counts'):
            next_action_card['state_counts'] = selected_gap.get('state_counts')
        if selected_gap.get('state_counts_zh'):
            next_action_card['state_counts_zh'] = selected_gap.get('state_counts_zh')
    elif phase_completion_state == 'ready_for_next_phase' and closure_readiness_state == 'approvable_candidates_present':
        next_action_card = {
            'priority': 'high',
            'title': '进入下一阶段：真实审批记录与 official release 预演',
            'why_now': (
                '当前已经出现 release-ready candidate 且 closure 样本可见。'
                '审批三态观察面已抬升到看板层，但样本仍以 awaiting 为主，适合继续推进更接近真实审批/发布的闭环。'
            ),
            'recommended_actions': [
                '为 release-ready candidate 增加更明确的 approval trail 与审批占位规则',
                '把 official release action 从 stub 推进到更接近真实执行前检查',
                '继续补 rollback registry 与 release artifact 的一致性校验',
                '让阶段卡/看板持续跟踪 awaiting / approved / rejected 分布变化',
            ],
        }
    elif phase_completion_state == 'ready_for_next_phase':
        next_action_card = {
            'priority': 'high',
            'title': '进入下一阶段：更深专家能力与正式收口闭环',
            'why_now': '新版质量与 formalization 样本已经形成，当前可以从“补数据”切换到“啃最后的硬收口”。',
            'recommended_actions': [
                '继续深化关键 agent 的专家能力，而不只是结构化模板',
                '推进 official release / rollback 的真实闭环能力',
                '补更完整 benchmark / regression 评测体系',
            ],
        }
    else:
        next_action_card = {
            'priority': 'high',
            'title': '补足新版链路的真实样本数据',
            'why_now': '当前 runtime / quality / formalization 观察面已打通，但历史数据仍偏空，需要通过新版任务闭环沉淀真实统计。',
            'recommended_actions': [
                '跑一批经过新版 test-expert 的任务，生成 quality_score',
                '跑一批经过 doc-manager / knowledge-steward 的任务，生成 formalization_gate / release_readiness',
                '基于真实样本再校正 stage card 的阶段判断与 capability axes',
            ],
        }

    remaining_gaps = [GAP_ID_ZH.get(item.get('gap_id'), item.get('title')) for item in (open_gap_summary.get('items', []) or [])]

    recommended_focus_gap_id = top_gap_ids[0] if top_gap_ids else None

    signals = {
        'latest_cycle_present': bool(latest_cycle),
        'job_count': job_count,
        'stale_count': stale_count,
        'governance_action_count': governance_action_count,
        'quality_observable': quality_observable,
        'quality_average_score': quality_average,
        'formalization_state_counts': formalization_counts,
        'closure_counts': closure_counts,
        'adaptive_loop_summary': adaptive_loop_summary,
        'adaptive_loop_count': adaptive_loop_count,
        'adaptive_decision_count': adaptive_decision_count,
        'adaptive_next_role_counts': adaptive_next_role_counts,
        'adaptive_handoff_source_counts': adaptive_handoff_source_counts,
        'dominant_next_role': dominant_next_role,
        'dominant_handoff_source_role': dominant_handoff_source_role,
        'dominant_decision_basis': dominant_decision_basis,
        'recent_ecosystem_learning': recent_learning_summary,
        'recent_learning_task_count': recent_learning_task_count,
        'observation_runtime': observation_runtime,
        'observation_active_count': observation_active_count,
        'observation_pending_followup_count': observation_pending_followup_count,
        'observation_timed_out_count': observation_timed_out_count,
        'observation_overdue_count': observation_overdue_count,
        'followup_queue_count': followup_queue_count,
        'followup_open_count': followup_open_count,
        'followup_in_progress_count': followup_in_progress_count,
        'followup_resolved_count': followup_resolved_count,
        'followup_closed_count': followup_closed_count,
        'followup_status_counts': followup_status_counts,
        'followup_escalation_counts': followup_escalation_counts,
        'followup_routing_target_counts': followup_routing_target_counts,
        'followup_assignment_counts': followup_assignment_counts,
        'followup_assigned_count': followup_assigned_count,
        'followup_unassigned_count': followup_unassigned_count,
        'followup_handoff_count': followup_handoff_count,
        'followup_backfilled_item_count': followup_backfilled_item_count,
        'followup_manual_classification_required_count': followup_manual_classification_required_count,
        'manual_classification_backlog_count': manual_classification_backlog_count,
        'manual_classification_unresolved_count': manual_classification_unresolved_count,
        'manual_classification_state_counts': manual_classification_state_counts,
        'followup_resolution_digest_available': followup_resolution_digest_available,
        'pattern_digest_available': pattern_digest_available,
        'followup_resolution_category_counts': followup_resolution_category_counts,
        'followup_target_resolution_category_counts': followup_target_resolution_category_counts,
        'followup_resolution_taxonomy_theme_counts': resolution_taxonomy_theme_counts,
        'recent_closure_knowledge_themes': recent_closure_knowledge_themes,
        'top_closure_themes': top_closure_themes,
        'pattern_digest_top': pattern_digest_top,
        'top_rule_candidates': top_rule_candidates,
        'top_pattern_candidates': top_pattern_candidates,
        'rule_proposal_review': rule_proposal_review,
        'rule_proposal_count': rule_proposal_count,
        'rule_proposal_pending_review_count': rule_proposal_pending_review_count,
        'rule_proposal_accepted_count': rule_proposal_accepted_count,
        'rule_proposal_rejected_count': rule_proposal_rejected_count,
        'rule_proposal_state_counts': rule_proposal_state_counts,
        'top_proposed_rules': top_proposed_rules,
        'governed_rule_sink': governed_rule_sink,
        'rule_sink_ready_count': rule_sink_ready_count,
        'written_rule_candidate_count': written_rule_candidate_count,
        'governed_rule_state_counts': governed_rule_state_counts,
        'top_written_rules': top_written_rules,
        'local_rulebook_export': local_rulebook_export,
        'local_rulebook_exported_count': local_rulebook_exported_count,
        'local_rulebook_item_count': local_rulebook_item_count,
        'local_rulebook_export_audit_available': local_rulebook_export_audit_available,
        'local_rulebook_export_status_counts': local_rulebook_export_status_counts,
        'local_rulebook_duplicate_blocked_count': local_rulebook_duplicate_blocked_count,
        'local_rulebook_active_rule_count': local_rulebook_active_rule_count,
        'local_rulebook_inactive_rule_count': local_rulebook_inactive_rule_count,
        'local_rulebook_archived_rule_count': local_rulebook_archived_rule_count,
        'local_rulebook_merged_rule_count': local_rulebook_merged_rule_count,
        'local_rulebook_superseded_rule_count': local_rulebook_superseded_rule_count,
        'local_rulebook_consequence_state_counts': local_rulebook_consequence_state_counts,
        'local_rulebook_merge_candidate_count': local_rulebook_merge_candidate_count,
        'local_rulebook_conflict_candidate_count': local_rulebook_conflict_candidate_count,
        'local_rulebook_duplicate_candidate_count': local_rulebook_duplicate_candidate_count,
        'archived_transition_count': archived_transition_count,
        'recent_archived_items': recent_archived_items,
        'archive_policy_counts': archive_policy_counts,
        'archived_restorable_count': archived_restorable_count,
        'archived_reopened_count': archived_reopened_count,
        'restore_count': restore_count,
        'reopen_count': reopen_count,
        'revive_count': revive_count,
        'restore_state_counts': restore_state_counts,
        'shared_source_archived_count': shared_source_archived_count,
        'recent_restore_actions': recent_restore_actions,
        'recent_restore_timeline': recent_restore_timeline,
        'recent_archive_actions': recent_archive_actions,
        'precedence_decision_count': precedence_decision_count,
        'precedence_override_counts': precedence_override_counts,
        'recent_precedence_decisions': recent_precedence_decisions,
        'merge_queue_count': merge_queue_count,
        'merge_queue_state_counts': merge_queue_state_counts,
        'merge_queue_open_count': merge_queue_open_count,
        'merge_queue_reviewing_count': merge_queue_reviewing_count,
        'merge_queue_accepted_count': merge_queue_accepted_count,
        'merge_queue_rejected_count': merge_queue_rejected_count,
        'top_exported_rules': top_exported_rules,
        'top_merge_targets': top_merge_targets,
        'top_supersede_suggestions': top_supersede_suggestions,
        'top_supersede_candidates': top_supersede_candidates,
        'top_merge_items': top_merge_items,
        'top_conflict_items': top_conflict_items,
        'conflict_state_counts': conflict_state_counts,
        'conflict_open_count': conflict_open_count,
        'conflict_reviewing_count': conflict_reviewing_count,
        'conflict_resolved_count': conflict_resolved_count,
        'recent_adjudications': recent_adjudications,
        'conflict_resolution_type_counts': conflict_resolution_type_counts,
        'recent_consequence_updates': recent_consequence_updates,
        'consequence_history_available': consequence_history_available,
        'consequence_history_event_count': consequence_history_event_count,
        'recent_consequence_transitions': recent_consequence_transitions,
        'transition_ledger_available': transition_ledger_available,
        'transition_event_count': transition_event_count,
        'unique_semantic_event_count': unique_semantic_event_count,
        'digest_duplicate_semantic_event_count': digest_duplicate_semantic_event_count,
        'transition_duplicate_suppressed_count': transition_duplicate_suppressed_count,
        'transition_digest_review_available': transition_digest_review_available,
        'recent_transition_events': recent_transition_events,
        'recent_suppressed_events': recent_suppressed_events,
        'top_transition_triggers': top_transition_triggers,
        'consistency_audit_available': consistency_audit_available,
        'audit_scope_refinement_available': audit_scope_refinement_available,
        'registry_sync_review_available': registry_sync_review_available,
        'registry_sync_issue_count': registry_sync_issue_count,
        'sync_scope_exception_count': sync_scope_exception_count,
        'scope_exception_counts': scope_exception_counts,
        'recent_sync_issues': recent_sync_issues,
        'recent_scope_exceptions': recent_scope_exceptions,
        'top_duplicate_items': top_duplicate_items,
        'post_decision_linkage_count': post_decision_linkage_count,
        'merge_linked_count': merge_linked_count,
        'supersede_linked_count': supersede_linked_count,
        'conflict_adjudicated_linked_count': conflict_adjudicated_linked_count,
        'recent_decision_linkages': recent_decision_linkages,
        'theme_contrast': theme_contrast,
        'knowledge_candidate_counts': knowledge_candidate_counts,
        'followup_resolution_review': followup_resolution_review,
        'recent_closure_insights': recent_closure_insights,
        'recently_closed_followup_items': recently_closed_followup_items,
        'top_pending_followup_items': top_pending_followup_items,
        'latest_attention_observations': latest_attention_observations,
        'recent_learning_role_counts': recent_learning_role_counts,
        'recent_learning_signal_counts': recent_learning_signal_counts,
        'dominant_learning_role': dominant_learning_role,
        'open_gap_summary': open_gap_summary,
        'open_gap_count': open_gap_count,
        'high_priority_gap_count': high_priority_gap_count,
        'top_gap_ids': top_gap_ids,
        'recommended_focus_gap_id': recommended_focus_gap_id,
        'human_approval_state_counts': human_approval_state_counts,
        'approval_recompute_state_counts': approval_recompute_state_counts,
        'release_execution_state_counts': release_execution_state_counts,
        'official_release_pipeline_state_counts': official_release_pipeline_state_counts,
        'official_release_pipeline_state_counts_zh': official_release_focus.get('state_counts_zh'),
        'official_release_pipeline_blocker_counts': official_release_pipeline_blocker_counts,
        'official_release_pipeline_blocker_counts_zh': official_release_focus.get('blocker_counts_zh'),
        'official_release_pipeline_focus_label': official_release_focus.get('focus_label'),
        'official_release_pipeline_focus_label_zh': official_release_focus.get('focus_label_zh'),
        'official_release_pipeline_dominant_state': official_release_focus.get('dominant_state'),
        'official_release_pipeline_dominant_state_zh': official_release_focus.get('dominant_state_zh'),
        'release_ready_candidates': release_ready_candidates,
        'manual_review_gates': manual_review_gates,
        'approval_required_count': approval_required_count,
        'awaiting_approval_count': awaiting_approval_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'pre_release_ready_count': pre_release_ready_count,
        'closure_consistency_ready_count': closure_consistency_ready_count,
        'official_release_rehearsal_ready_count': official_release_rehearsal_ready_count,
        'rollback_ready_count': rollback_ready_count,
        'official_release_pipeline_visible_count': official_release_pipeline_visible_count,
        'official_release_pipeline_executable_count': official_release_pipeline_executable_count,
        'executor_contract_available_count': executor_contract_available_count,
        'dry_run_available_count': dry_run_available_count,
        'execution_receipt_protocol_available_count': execution_receipt_protocol_available_count,
        'handoff_packet_available_count': handoff_packet_available_count,
        'operator_execution_request_available_count': operator_execution_request_available_count,
        'receipt_correlation_ready_count': receipt_correlation_ready_count,
        'executor_readiness_review_available_count': executor_readiness_review_available_count,
        'executor_adapter_available_count': executor_adapter_available_count,
        'executor_capability_registry_available': executor_capability_registry_available,
        'invocation_policy_available': invocation_policy_available,
        'future_executor_scaffold_available': future_executor_scaffold_available,
        'executor_plugin_interface_available': executor_plugin_interface_available,
        'transcript_contract_available': transcript_contract_available,
        'no_op_executor_available': no_op_executor_available,
        'executor_conformance_available': executor_conformance_available,
        'executor_error_contract_available': executor_error_contract_available,
        'release_rollback_parity_available': release_rollback_parity_available,
        'implementation_blueprint_available': implementation_blueprint_available,
        'executor_delivery_pack_available': executor_delivery_pack_available,
        'executor_acceptance_pack_available': executor_acceptance_pack_available,
        'ownership_split_available': ownership_split_available,
        'executor_blocker_matrix_available': executor_blocker_matrix_available,
        'executor_delivery_item_count': executor_delivery_item_count,
        'executor_acceptance_case_count': executor_acceptance_case_count,
        'executor_blocker_count': executor_blocker_count,
        'cutover_pack_available': cutover_pack_available,
        'integration_checklist_available': integration_checklist_available,
        'risk_register_available': risk_register_available,
        'handoff_summary_available': handoff_summary_available,
        'credential_binding_policy_available': credential_binding_policy_available,
        'target_binding_registry_available': target_binding_registry_available,
        'cutover_signoff_available': cutover_signoff_available,
        'blocker_drilldown_available': blocker_drilldown_available,
        'human_action_pack_available': human_action_pack_available,
        'credential_binding_evidence_checklist_available': credential_binding_evidence_checklist_available,
        'signoff_evidence_packet_available': signoff_evidence_packet_available,
        'unresolved_blocker_tracker_available': unresolved_blocker_tracker_available,
        'pending_human_action_board_available': pending_human_action_board_available,
        'credential_binding_runbook_available': credential_binding_runbook_available,
        'signoff_runbook_available': signoff_runbook_available,
        'blocker_resolution_playbook_available': blocker_resolution_playbook_available,
        'unresolved_credential_binding_count': unresolved_credential_binding_count,
        'unresolved_signoff_count': unresolved_signoff_count,
        'unresolved_blocker_owner_count': unresolved_blocker_owner_count,
        'pending_signoff_role_count': pending_signoff_role_count,
        'binding_evidence_gap_count': binding_evidence_gap_count,
        'top_blocker_categories': top_blocker_categories,
        'top_human_actions': top_human_actions,
        'top_pending_human_actions': top_pending_human_actions,
        'top_unresolved_human_blockers': top_unresolved_human_blockers,
        'top_missing_executor_contracts': top_missing_executor_contracts,
        'parity_gaps': parity_gaps,
        'top_executor_risks': top_executor_risks,
        'top_executor_blockers': top_executor_blockers,
        'top_remaining_blockers': top_remaining_blockers,
        'environment_guard_ok_count': environment_guard_ok_count,
        'environment_guard_unmet_count': environment_guard_unmet_count,
        'top_executor_adapter_types': top_executor_adapter_types,
        'top_executor_plugin_targets': top_executor_plugin_targets,
        'handoff_boundary_ready_count': handoff_boundary_ready_count,
        'executor_readiness_gate_count': executor_readiness_gate_count,
        'executor_unmet_gate_count': executor_unmet_gate_count,
        'top_unmet_executor_gates': top_unmet_executor_gates,
        'executor_admission_available': executor_admission_available,
        'go_no_go_available': go_no_go_available,
        'rollout_gate_count': rollout_gate_count,
        'rollout_unmet_count': rollout_unmet_count,
        'waiver_exception_count': waiver_exception_count,
        'overall_admission_state': overall_admission_state,
        'top_blocking_gates': top_blocking_gates,
        'executor_simulation_available_count': executor_simulation_available_count,
        'executor_simulation_pass_count': executor_simulation_pass_count,
        'executor_simulation_fail_count': executor_simulation_fail_count,
        'contract_compliance_available': contract_compliance_available,
        'integration_rehearsal_available': integration_rehearsal_available,
        'top_executor_contract_gaps': top_executor_contract_gaps,
        'top_execution_handoff_targets': top_execution_handoff_targets,
        'top_command_plan_steps': top_command_plan_steps,
        'execution_request_requested_count': execution_request_requested_count,
        'execution_request_acknowledged_count': execution_request_acknowledged_count,
        'execution_request_accepted_count': execution_request_accepted_count,
        'execution_request_declined_count': execution_request_declined_count,
        'execution_request_expired_count': execution_request_expired_count,
        'request_open_count': request_open_count,
        'request_inflight_count': request_inflight_count,
        'execution_request_reassigned_count': execution_request_reassigned_count,
        'execution_request_escalated_count': execution_request_escalated_count,
        'execution_request_retry_ready_count': execution_request_retry_ready_count,
        'top_request_states': top_request_states,
        'top_pending_requests': top_pending_requests,
        'recent_request_actions': recent_request_actions,
        'recent_request_transitions': recent_request_transitions,
        'recent_request_escalations': recent_request_escalations,
        'top_request_owners': top_request_owners,
        'release_execution_requested_count': release_execution_requested_count,
        'rollback_execution_requested_count': rollback_execution_requested_count,
        'release_execution_receipt_recorded_count': release_execution_receipt_recorded_count,
        'rollback_execution_receipt_recorded_count': rollback_execution_receipt_recorded_count,
        'closure_visible_count': closure_visible_count,
        'closure_readiness_state': closure_readiness_state,
        'recoverability_counts': (recovery or {}).get('recoverability_counts', {}),
        'lifecycle_bucket_counts': (lifecycle or {}).get('bucket_counts', {}),
    }

    claims_allowed = [
        '基础骨架已成型并可运行',
        '关键智能体已完成第一轮结构化深化',
        '最小持续运行化骨架已建立',
        '候选结果与正式结果边界已显式化',
        '最小质量评分骨架已建立并接入观察面',
        '收口就绪链路已进入观察面且已有真实样本',
    ]

    not_yet_claimable = [
        '完整常驻托管体系已完成',
        '完整正式发布管线已完成',
        '真实版本回滚系统已完成',
        '完整基准、回归与排行榜评测体系已完成',
        '成熟终态生态已完成',
    ]

    return {
        'generated_at': _now(),
        'stage_id': stage_id,
        'stage_label': stage_label,
        'maturity_band': maturity_band,
        'summary': summary,
        'phase_completion_state': phase_completion_state,
        'closure_readiness_state': closure_readiness_state,
        'capability_axes': capability_axes,
        'signals': signals,
        'completion_definition': completion_definition,
        'next_action_card': next_action_card,
        'remaining_gaps': remaining_gaps,
        'claims_allowed': claims_allowed,
        'not_yet_claimable': not_yet_claimable,
    }


def write_stage_card_markdown(payload: dict[str, Any]) -> str:
    def _render_markdown_value(value: Any) -> Any:
        if isinstance(value, bool):
            return '是' if value else '否'
        if isinstance(value, list):
            if not value:
                return '无'
            return '；'.join(str(item) for item in value)
        if isinstance(value, dict):
            if not value:
                return '无'
            return '；'.join(f"{k}={v}" for k, v in value.items())
        return value

    def _render_completion_value(key: str, value: Any) -> Any:
        if key == 'closure_readiness_state':
            value = {
                'approvable_candidates_present': '已出现可审批候选结果',
                'observable': '已进入观察面',
                'none': '尚未形成收口观察面',
            }.get(str(value), value)
        if key == 'phase_complete_when' and isinstance(value, list):
            value = [
                '持续运行化可以稳定输出最新周期与三层看板',
                '至少一批新任务经过新版质量评分产出链路',
                '至少一批新任务经过正式收口判定链路',
                '阶段卡能够基于真实历史数据而不是仅靠骨架信号判断阶段',
            ]
        return _render_markdown_value(value)

    next_card = payload.get('next_action_card') or {}
    recommended_focus_gap_id = ((payload.get('signals') or {}).get('recommended_focus_gap_id'))
    capability_label_map = {
        'skeleton': '骨架成熟度',
        'agent_depth': '智能体深化度',
        'runtime': '持续运行化程度',
        'formalization': '正式收口程度',
        'evaluation': '评测完善度',
    }
    completion_label_map = {
        'runtime_observable': '持续运行可观测',
        'stale_control_stable': '陈旧任务控制稳定',
        'quality_observable': '质量观察面可见',
        'formalization_observable': '正式收口观察面可见',
        'closure_visible': '收口链路可见',
        'closure_readiness_state': '收口就绪状态',
        'manual_gate_defined': '人工门禁已定义',
        'phase_complete_when': '本阶段完成条件',
    }
    phase_state_map = {
        'ready_for_next_phase': '可进入下一阶段',
        'mostly_ready_for_next_phase': '基本可进入下一阶段',
        'in_progress': '仍在推进中',
    }
    closure_state_map = {
        'approvable_candidates_present': '已出现可审批候选结果',
        'observable': '已进入观察面',
        'none': '尚未形成收口观察面',
    }
    stage_id_map = {
        'strong-skeleton-midphase': '强骨架中期阶段',
    }
    maturity_band_map = {
        'low': '早期',
        'mid': '中期',
        'high': '后期',
    }
    lines = [
        '# 生态系统阶段卡',
        '',
        f"- 生成时间: {payload.get('generated_at')}",
        f"- 阶段编号: {stage_id_map.get(payload.get('stage_id'), payload.get('stage_id'))}",
        f"- 阶段名称: {payload.get('stage_label')}",
        f"- 成熟度分层: {maturity_band_map.get(payload.get('maturity_band'), payload.get('maturity_band'))}",
        f"- 阶段完成状态: {phase_state_map.get(payload.get('phase_completion_state'), payload.get('phase_completion_state'))}",
        f"- 收口就绪状态: {closure_state_map.get(payload.get('closure_readiness_state'), payload.get('closure_readiness_state'))}",
        '',
        payload.get('summary', ''),
        '',
        '## 当前推荐聚焦',
        f"- 当前聚焦缺口: {GAP_ID_ZH.get(recommended_focus_gap_id, recommended_focus_gap_id)}",
        f"- 当前聚焦标题: {next_card.get('title')}",
        f"- 卡点类型: {next_card.get('focus_label_zh') or next_card.get('focus_label')}",
        f"- 主导状态: {next_card.get('dominant_state_zh') or next_card.get('dominant_state')}",
        f"- 阻塞分布: {_render_markdown_value(next_card.get('blocker_counts_zh') or next_card.get('blocker_counts'))}",
        f"- 状态分布: {_render_markdown_value(next_card.get('state_counts_zh') or next_card.get('state_counts'))}",
        f"- 当前原因: {next_card.get('why_now')}",
        f"- 建议动作: {_render_markdown_value(next_card.get('recommended_actions'))}",
        '',
        '## 核心能力刻度',
    ]
    for k, v in (payload.get('capability_axes') or {}).items():
        lines.append(f"- {capability_label_map.get(k, k)}: {v}")
    lines.extend(['', '## 本阶段完成定义'])
    for k, v in (payload.get('completion_definition') or {}).items():
        lines.append(f"- {completion_label_map.get(k, k)}: {_render_completion_value(k, v)}")
    lines.extend(['', '## 下一步动作卡（完整）'])
    next_card_label_map = {
        'priority': '优先级',
        'title': '标题',
        'focus_label': '卡点类型（原始）',
        'focus_label_zh': '卡点类型',
        'dominant_state': '主导状态（原始）',
        'dominant_state_zh': '主导状态',
        'blocker_counts': '阻塞分布（原始）',
        'blocker_counts_zh': '阻塞分布',
        'state_counts': '状态分布（原始）',
        'state_counts_zh': '状态分布',
        'why_now': '当前原因',
        'recommended_actions': '建议动作',
    }
    priority_value_map = {'high': '高', 'medium': '中', 'low': '低'}
    for k, v in next_card.items():
        rendered = priority_value_map.get(v, v) if k == 'priority' else _render_markdown_value(v)
        lines.append(f'- {next_card_label_map.get(k, k)}: {rendered}')
    lines.extend(['', '## 当前剩余缺口'])
    for item in payload.get('remaining_gaps', []):
        lines.append(f'- {item}')
    lines.extend(['', '## 当前允许的表述'])
    for item in payload.get('claims_allowed', []):
        lines.append(f'- {item}')
    lines.extend(['', '## 当前仍不能宣称'])
    for item in payload.get('not_yet_claimable', []):
        lines.append(f'- {item}')
    lines.extend(['', '## 附：内部信号（保留部分原始字段便于排查）'])
    signal_label_map = {
        'official_release_pipeline_state_counts': '正式发布管线状态分布（原始）',
        'official_release_pipeline_state_counts_zh': '正式发布管线状态分布',
        'official_release_pipeline_blocker_counts': '正式发布管线阻塞分布（原始）',
        'official_release_pipeline_blocker_counts_zh': '正式发布管线阻塞分布',
        'official_release_pipeline_focus_label': '正式发布管线卡点类型（原始）',
        'official_release_pipeline_focus_label_zh': '正式发布管线卡点类型',
        'official_release_pipeline_dominant_state': '正式发布管线主导状态（原始）',
        'official_release_pipeline_dominant_state_zh': '正式发布管线主导状态',
        'recommended_focus_gap_id': '当前推荐聚焦缺口（原始）',
        'open_gap_count': '缺口总数',
        'high_priority_gap_count': '高优先级缺口数',
    }
    for k, v in (payload.get('signals') or {}).items():
        lines.append(f'- {signal_label_map.get(k, k)}: {_render_markdown_value(v)}')
    return '\n'.join(lines) + '\n'
