#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def build_approval_record(task_id: str, *, review: dict[str, Any], boundary: dict[str, Any], formalization_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        'task_id': task_id,
        'approval_required': True,
        'approved': False,
        'approval_state': boundary.get('approval_state'),
        'review_decision': review.get('decision'),
        'formalization_state': formalization_gate.get('formalization_state'),
        'official_release': False,
        'approval_note': 'Human approval is still required before any official release action.',
        'generated_at': _now(),
    }


def build_approval_checklist(task_id: str, *, formalization_gate: dict[str, Any], release_readiness: dict[str, Any], rollback_stub: dict[str, Any]) -> dict[str, Any]:
    checks = [
        {'name': 'technical_validation_passed', 'passed': bool(formalization_gate.get('technical_validation_passed'))},
        {'name': 'quality_gate_passed', 'passed': bool(formalization_gate.get('quality_gate_passed'))},
        {'name': 'release_ready_candidate', 'passed': formalization_gate.get('formalization_state') == 'release_ready_candidate'},
        {'name': 'rollback_stub_present', 'passed': bool(rollback_stub.get('rollback_supported'))},
        {'name': 'human_approval_pending', 'passed': True},
    ]
    checklist_ready = all(item['passed'] for item in checks[:4])
    return {
        'task_id': task_id,
        'checklist_ready': checklist_ready,
        'checks': checks,
        'summary': f"checklist_ready={checklist_ready} formalization_state={formalization_gate.get('formalization_state')} release_ready={release_readiness.get('release_ready')}",
    }


def build_approval_outcome_stub(task_id: str, *, approval_checklist: dict[str, Any]) -> dict[str, Any]:
    if approval_checklist.get('checklist_ready'):
        status = 'pending_human_approval'
        next_step = 'record_human_approval_decision'
    else:
        status = 'not_ready_for_approval'
        next_step = 'fix_checklist_gaps_before_requesting_approval'
    return {
        'task_id': task_id,
        'approval_status': status,
        'approved': False,
        'requires_human_approval': True,
        'next_step': next_step,
        'note': 'Approval outcome remains a stub until a real human approval decision is recorded.',
    }


def build_approval_decision_placeholder(task_id: str, *, approval_outcome: dict[str, Any]) -> dict[str, Any]:
    status = approval_outcome.get('approval_status')
    if status == 'pending_human_approval':
        decision_state = 'pending_human_decision'
        next_step = 'wait_for_human_approval_or_rejection'
        approved = False
    else:
        decision_state = 'rejected_placeholder'
        next_step = 'candidate_not_ready_for_human_decision'
        approved = False
    return {
        'task_id': task_id,
        'decision_recorded': False,
        'decision_state': decision_state,
        'approved': approved,
        'next_step': next_step,
        'note': 'Approval decision is still a placeholder. No real human decision has been recorded.',
    }


def build_approval_transition_stub(task_id: str, *, approval_decision: dict[str, Any]) -> dict[str, Any]:
    if approval_decision.get('decision_state') == 'approved_placeholder':
        state = 'approved_transition_placeholder'
        approved = True
        next_step = 'prepare_official_release_state_placeholder'
    elif approval_decision.get('decision_state') == 'rejected_placeholder':
        state = 'rejected_transition_placeholder'
        approved = False
        next_step = 'keep_candidate_blocked_or_rework'
    else:
        state = 'awaiting_human_decision'
        approved = False
        next_step = 'wait_for_real_human_decision'
    return {
        'task_id': task_id,
        'transition_state': state,
        'decision_recorded': bool(approval_decision.get('decision_recorded')),
        'approved': approved,
        'next_step': next_step,
        'note': 'Approval transition remains a placeholder until a real human decision is recorded.',
    }


def build_human_approval_result_stub(task_id: str, *, approval_transition: dict[str, Any]) -> dict[str, Any]:
    transition_state = approval_transition.get('transition_state')
    decision_recorded_flag = bool(approval_transition.get('decision_recorded'))
    if decision_recorded_flag and transition_state == 'approved_transition_placeholder':
        ingestion_state = 'approved_ingest_placeholder'
        decision_recorded = True
        approved = True
        next_step = 'recompute_release_execution_guardrail_after_real_approval'
    elif decision_recorded_flag and transition_state == 'rejected_transition_placeholder':
        ingestion_state = 'rejected_ingest_placeholder'
        decision_recorded = True
        approved = False
        next_step = 'keep_candidate_blocked_and_rework'
    else:
        ingestion_state = 'no_human_decision_recorded'
        decision_recorded = False
        approved = None  # Use None instead of False for undetermined state
        next_step = 'wait_for_real_human_decision_input'
    return {
        'task_id': task_id,
        'ingestion_state': ingestion_state,
        'decision_recorded': decision_recorded,
        'approved': approved,
        'decision_source': 'human_approval_result_not_connected',
        'next_step': next_step,
        'note': 'Human approval result remains a stub until a real approval/rejection signal is ingested.',
    }


def build_release_action_stub(task_id: str, *, formalization_gate: dict[str, Any]) -> dict[str, Any]:
    state = formalization_gate.get('formalization_state')
    return {
        'task_id': task_id,
        'action_allowed': False,
        'official_release': False,
        'formalization_state': state,
        'next_step': 'request_human_approval' if state == 'release_ready_candidate' else 'improve_candidate_or_wait_for_gate_clearance',
        'release_note': 'This is a release action stub only. No official release action may execute automatically.',
        'generated_at': _now(),
    }


def build_release_preflight_stub(task_id: str, task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    required_artifacts = [
        'artifacts/formalization_gate.json',
        'artifacts/release_readiness.json',
        'artifacts/approval_record.json',
        'artifacts/approval_checklist.json',
        'artifacts/approval_outcome_stub.json',
        'artifacts/release_action_stub.json',
        'artifacts/rollback_stub.json',
        'artifacts/rollback_registry_entry.json',
    ]
    missing = [item for item in required_artifacts if not (task_dir / item).exists()]
    return {
        'task_id': task_id,
        'preflight_ready': not missing,
        'required_artifacts': required_artifacts,
        'missing_artifacts': missing,
        'next_step': 'request_human_approval' if not missing else 'generate_missing_release_closure_artifacts',
        'note': 'Preflight stub only. Even when preflight_ready=true, official release still requires a real human approval decision and release execution path.',
    }


def build_pre_release_gate(task_id: str, *, formalization_gate: dict[str, Any], approval_outcome: dict[str, Any], release_preflight: dict[str, Any], rollback_registry: dict[str, Any]) -> dict[str, Any]:
    formalization_state = formalization_gate.get('formalization_state')
    approval_status = approval_outcome.get('approval_status')
    release_preflight_ready = bool(release_preflight.get('preflight_ready'))
    rollback_supported = bool(rollback_registry.get('rollback_supported'))
    pre_release_ready = (
        formalization_state == 'release_ready_candidate'
        and approval_status == 'pending_human_approval'
        and release_preflight_ready
        and rollback_supported
    )
    if pre_release_ready:
        gate_state = 'ready_for_human_release_review'
    elif approval_outcome.get('approved'):
        gate_state = 'post_approval_placeholder'
    else:
        gate_state = 'not_ready'
    return {
        'task_id': task_id,
        'gate_state': gate_state,
        'pre_release_ready': pre_release_ready,
        'requires_human_approval': True,
        'approval_status': approval_status,
        'formalization_state': formalization_state,
        'rollback_supported': rollback_supported,
        'release_preflight_ready': release_preflight_ready,
        'summary': f'gate_state={gate_state} approval_status={approval_status} formalization_state={formalization_state}',
    }


def build_official_release_state_placeholder(task_id: str, *, approval_transition: dict[str, Any], release_execution_guardrail: dict[str, Any], human_approval_result: dict[str, Any]) -> dict[str, Any]:
    decision_recorded = human_approval_result.get('decision_recorded')
    approved = human_approval_result.get('approved')
    execution_blocked = release_execution_guardrail.get('execution_blocked')
    
    if decision_recorded and approved is True and not execution_blocked:
        state = 'post_approval_ready'
        next_step = 'official_release_execution_path_not_implemented'
    elif decision_recorded and approved is False:  # Explicit rejection
        state = 'rejected_permanently'
        next_step = 'candidate_rejected_no_release_possible_until_rework'
    elif decision_recorded and approved is True and execution_blocked:
        state = 'post_approval_but_still_blocked'
        next_step = 'address_remaining_block_reasons_then_release'
    else:
        state = 'awaiting_human_decision'
        next_step = 'wait_for_human_decision_then_recompute_guardrails'
    
    return {
        'task_id': task_id,
        'official_release_state': state,
        'official_release': False,
        'next_step': next_step,
        'note': 'Official release state remains a placeholder until a real human decision and a real execution path exist.',
    }


def build_post_approval_guardrail_transition(task_id: str, *, human_approval_result: dict[str, Any], release_execution_guardrail: dict[str, Any]) -> dict[str, Any]:
    block_reasons = list(release_execution_guardrail.get('block_reasons', []) or [])
    decision_recorded = human_approval_result.get('decision_recorded')
    approved = human_approval_result.get('approved')
    
    if decision_recorded and approved is True and not release_execution_guardrail.get('execution_blocked'):
        state = 'unblocked_after_approval'
        execution_unblocked = True
        retained = []
        next_step = 'official_release_execution_path_not_implemented'
    elif decision_recorded and approved is True and release_execution_guardrail.get('execution_blocked'):
        state = 'still_blocked_after_approval'
        execution_unblocked = False
        retained = [reason for reason in block_reasons if reason != 'human_approval_not_recorded']
        next_step = 'address_remaining_block_reasons_after_approval'
    elif decision_recorded and approved is False:
        state = 'permanently_blocked_after_rejection'
        execution_unblocked = False
        retained = block_reasons + ['human_approval_rejected']
        next_step = 'candidate_rejected_no_release_possible_until_rework'
    else:
        state = 'awaiting_real_approval'
        execution_unblocked = False
        retained = block_reasons
        next_step = 'wait_for_real_human_approval_before_any_unblock'
    
    return {
        'task_id': task_id,
        'transition_state': state,
        'execution_unblocked': execution_unblocked,
        'retained_block_reasons': retained,
        'next_step': next_step,
        'note': 'Post-approval guardrail transition remains a placeholder until a real human approval is recorded.',
    }


def build_official_release_pipeline_summary(task_id: str, *, pre_release_gate: dict[str, Any], official_release_rehearsal: dict[str, Any], release_execution_guardrail: dict[str, Any], official_release_state: dict[str, Any], release_artifact_binding: dict[str, Any], rollback_registry: dict[str, Any], human_approval_result: dict[str, Any], approval_recompute_snapshot: dict[str, Any]) -> dict[str, Any]:
    decision_recorded = bool(human_approval_result.get('decision_recorded'))
    approved = human_approval_result.get('approved')
    execution_blocked = bool(release_execution_guardrail.get('execution_blocked'))
    block_reasons = list(release_execution_guardrail.get('block_reasons', []) or [])
    ready_signals = {
        'pre_release_ready': bool(pre_release_gate.get('pre_release_ready')),
        'rehearsal_ready': bool(official_release_rehearsal.get('rehearsal_ready')),
        'artifact_binding_ready': bool(release_artifact_binding.get('binding_ready')),
        'rollback_supported': bool(rollback_registry.get('rollback_supported')),
        'human_decision_recorded': decision_recorded,
        'human_approved': approved is True,
        'recompute_would_unblock': bool(approval_recompute_snapshot.get('would_unblock_execution')),
    }
    blockers: list[str] = []
    if not ready_signals['pre_release_ready']:
        blockers.append('pre_release_gate_not_ready')
    if not ready_signals['rehearsal_ready']:
        blockers.append('official_release_rehearsal_not_ready')
    if not ready_signals['artifact_binding_ready']:
        blockers.append('release_artifact_binding_not_ready')
    if not ready_signals['rollback_supported']:
        blockers.append('rollback_not_ready')
    blockers.extend([reason for reason in block_reasons if reason not in blockers])

    if decision_recorded and approved is False:
        pipeline_state = 'rejected'
        next_step = 'candidate_rejected_no_release_possible_until_rework'
    elif decision_recorded and approved is True and not execution_blocked:
        pipeline_state = 'ready_but_execution_not_implemented'
        next_step = 'official_release_execution_path_not_implemented'
    elif decision_recorded and approved is True and execution_blocked:
        pipeline_state = 'approved_but_blocked'
        next_step = 'address_remaining_block_reasons_then_release'
    elif ready_signals['pre_release_ready'] and ready_signals['rehearsal_ready'] and ready_signals['artifact_binding_ready'] and ready_signals['rollback_supported']:
        pipeline_state = 'awaiting_human_approval'
        next_step = 'record_real_human_approval_before_any_release_execution'
    else:
        pipeline_state = 'candidate_not_ready'
        next_step = 'complete_release_pipeline_prerequisites_before_human_approval'

    return {
        'task_id': task_id,
        'pipeline_state': pipeline_state,
        'official_release_executable': False,
        'ready_signals': ready_signals,
        'blockers': blockers,
        'blocker_count': len(blockers),
        'official_release_state': official_release_state.get('official_release_state'),
        'next_step': next_step,
        'note': 'Official release pipeline summary is still a placeholder-level closure summary. Real execution remains unavailable until approval and execution path are fully implemented.',
    }


def build_release_execution_guardrail(task_id: str, *, approval_decision: dict[str, Any], pre_release_gate: dict[str, Any], human_approval_result: dict[str, Any] = None) -> dict[str, Any]:
    block_reasons: list[str] = []
    if not pre_release_gate.get('pre_release_ready'):
        block_reasons.append('pre_release_gate_not_ready')
    
    # Check the human approval result for the explicit decision
    if human_approval_result:
        approved = human_approval_result.get('approved')
        decision_recorded = human_approval_result.get('decision_recorded')
        
        if not decision_recorded:
            block_reasons.append('human_approval_not_recorded')
        elif decision_recorded and approved is False:  # Explicit rejection
            block_reasons.append('human_approval_rejected')
        elif decision_recorded and approved is None:  # Invalid state
            block_reasons.append('human_approval_invalid_state')
    else:
        # Fallback to approval_decision if human_approval_result not provided
        if not approval_decision.get('approved'):
            block_reasons.append('human_approval_not_recorded')

    execution_blocked = bool(block_reasons)
    
    if 'human_approval_rejected' in block_reasons:
        execution_state = 'blocked_permanently_rejected'
        next_step = 'candidate_rejected_no_release_possible_until_rework'
    elif 'human_approval_not_recorded' in block_reasons:
        execution_state = 'blocked_pending_human_approval'
        next_step = 'record_real_human_approval_before_any_release_execution'
    elif 'pre_release_gate_not_ready' in block_reasons:
        execution_state = 'blocked_pending_prereq'
        next_step = 'complete_prerequisite_checks_before_approval'
    elif 'human_approval_invalid_state' in block_reasons:
        execution_state = 'blocked_invalid_state'
        next_step = 'correct_approval_state_before_continuing'
    else:
        execution_state = 'allowed_placeholder'
        next_step = 'official_release_execution_path_not_implemented'

    return {
        'task_id': task_id,
        'execution_blocked': execution_blocked,
        'block_reasons': block_reasons,
        'execution_state': execution_state,
        'official_release': False,
        'next_step': next_step,
        'note': 'Execution guardrail is intentionally strict. Real release execution is still blocked until a real human approval decision exists.',
    }


def build_rollback_registry_entry(task_id: str, *, rollback_stub: dict[str, Any], formalization_gate: dict[str, Any], official_release: bool = False) -> dict[str, Any]:
    return {
        'task_id': task_id,
        'entry_type': 'official_release_stub' if official_release else 'candidate_stub',
        'official_release': official_release,
        'rollback_supported': bool(rollback_stub.get('rollback_supported')),
        'rollback_artifacts': rollback_stub.get('rollback_artifacts', []),
        'formalization_state': formalization_gate.get('formalization_state'),
        'note': 'Rollback registry entry created for future release closure. Current entry does not imply a real published release exists.' if not official_release else 'Rollback registry entry for official release path placeholder.',
    }


def load_release_closure_snapshot(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    approval = _load_json(task_dir / 'artifacts' / 'approval_record.json')
    approval_checklist = _load_json(task_dir / 'artifacts' / 'approval_checklist.json')
    approval_outcome = _load_json(task_dir / 'artifacts' / 'approval_outcome_stub.json')
    approval_decision = _load_json(task_dir / 'artifacts' / 'approval_decision_placeholder.json')
    approval_transition = _load_json(task_dir / 'artifacts' / 'approval_transition_stub.json')
    human_approval_result = _load_json(task_dir / 'artifacts' / 'human_approval_result_stub.json')
    human_approval_input = _load_json(task_dir / 'artifacts' / 'human_approval_input_slot.json')
    approval_recompute = _load_json(task_dir / 'artifacts' / 'approval_recompute_snapshot.json')
    release_action = _load_json(task_dir / 'artifacts' / 'release_action_stub.json')
    release_preflight = _load_json(task_dir / 'artifacts' / 'release_preflight_stub.json')
    rollback_entry = _load_json(task_dir / 'artifacts' / 'rollback_registry_entry.json')
    release_artifact_binding = _load_json(task_dir / 'artifacts' / 'release_artifact_binding.json')
    pre_release_gate = _load_json(task_dir / 'artifacts' / 'pre_release_gate.json')
    closure_consistency = _load_json(task_dir / 'artifacts' / 'release_closure_consistency.json')
    official_release_rehearsal = _load_json(task_dir / 'artifacts' / 'official_release_rehearsal.json')
    execution_guardrail = _load_json(task_dir / 'artifacts' / 'release_execution_guardrail.json')
    official_release_state = _load_json(task_dir / 'artifacts' / 'official_release_state_placeholder.json')
    official_release_pipeline_summary = _load_json(task_dir / 'artifacts' / 'official_release_pipeline_summary.json')
    official_release_record = _load_json(task_dir / 'artifacts' / 'official_release_record.json')
    rollback_registration_record = _load_json(task_dir / 'artifacts' / 'rollback_registration_record.json')
    release_execution_confirmation = _load_json(task_dir / 'artifacts' / 'official_release_execution_confirmation_record.json')
    release_execution_status = _load_json(task_dir / 'artifacts' / 'official_release_execution_status.json')
    rollback_execution_confirmation = _load_json(task_dir / 'artifacts' / 'rollback_execution_confirmation_record.json')
    rollback_execution_status = _load_json(task_dir / 'artifacts' / 'rollback_execution_status.json')
    official_release_execution_precheck = _load_json(task_dir / 'artifacts' / 'official_release_execution_precheck.json')
    rollback_execution_precheck = _load_json(task_dir / 'artifacts' / 'rollback_execution_precheck.json')
    release_execution_protocol = _load_json(task_dir / 'artifacts' / 'official_release_execution_protocol.json')
    rollback_execution_protocol = _load_json(task_dir / 'artifacts' / 'rollback_execution_protocol.json')
    execution_audit_summary = _load_json(task_dir / 'artifacts' / 'execution_audit_summary.json')
    execution_batch = _load_json(task_dir / 'artifacts' / 'execution_batch.json')
    release_executor_contract = _load_json(task_dir / 'artifacts' / 'release_executor_contract.json')
    rollback_executor_contract = _load_json(task_dir / 'artifacts' / 'rollback_executor_contract.json')
    release_execution_request = _load_json(task_dir / 'artifacts' / 'official_release_execution_request.json')
    rollback_execution_request = _load_json(task_dir / 'artifacts' / 'rollback_execution_request.json')
    release_handoff_packet = _load_json(task_dir / 'artifacts' / 'release_executor_handoff_packet.json')
    rollback_handoff_packet = _load_json(task_dir / 'artifacts' / 'rollback_executor_handoff_packet.json')
    release_operator_execution_request = _load_json(task_dir / 'artifacts' / 'release_operator_execution_request.json')
    rollback_operator_execution_request = _load_json(task_dir / 'artifacts' / 'rollback_operator_execution_request.json')
    release_execution_dry_run = _load_json(task_dir / 'artifacts' / 'official_release_execution_dry_run_result.json')
    rollback_execution_dry_run = _load_json(task_dir / 'artifacts' / 'rollback_execution_dry_run_result.json')
    release_execution_receipt = _load_json(task_dir / 'artifacts' / 'official_release_execution_receipt.json')
    rollback_execution_receipt = _load_json(task_dir / 'artifacts' / 'rollback_execution_receipt.json')
    execution_request_lifecycle = _load_json(task_dir / 'artifacts' / 'execution_request_lifecycle.json')
    execution_request_registry = _load_json(task_dir / 'artifacts' / 'execution_request_registry.json')
    execution_request_dispatch_review = _load_json(task_dir / 'artifacts' / 'execution_request_dispatch_review.json')
    operator_acknowledgement_review = _load_json(task_dir / 'artifacts' / 'operator_acknowledgement_review.json')
    execution_control_summary = _load_json(task_dir / 'artifacts' / 'execution_control_summary.json')
    rollout_gate_registry = _load_json(task_dir / 'artifacts' / 'rollout_gate_registry.json')
    waiver_exception_registry = _load_json(task_dir / 'artifacts' / 'waiver_exception_registry.json')
    executor_admission_review = _load_json(task_dir / 'artifacts' / 'executor_admission_review.json')
    go_no_go_decision_pack = _load_json(task_dir / 'artifacts' / 'go_no_go_decision_pack.json')
    release_adapter_manifest = _load_json(task_dir / 'artifacts' / 'release_executor_adapter_manifest.json')
    rollback_adapter_manifest = _load_json(task_dir / 'artifacts' / 'rollback_executor_adapter_manifest.json')
    executor_capability_registry = _load_json(task_dir / 'artifacts' / 'executor_capability_registry.json')
    invocation_policy_review = _load_json(task_dir / 'artifacts' / 'invocation_policy_review.json')
    execution_request_escalation_review = _load_json(task_dir / 'artifacts' / 'execution_request_escalation_review.json')
    execution_request_retry_summary = _load_json(task_dir / 'artifacts' / 'execution_request_retry_summary.json')
    executor_readiness_review = _load_json(task_dir / 'artifacts' / 'executor_readiness_review.json')
    real_executor_handoff_boundary = _load_json(task_dir / 'artifacts' / 'real_executor_handoff_boundary.json')
    executor_conformance_matrix = _load_json(task_dir / 'artifacts' / 'executor_conformance_matrix.json')
    executor_error_contract = _load_json(task_dir / 'artifacts' / 'executor_error_contract.json')
    release_rollback_parity_matrix = _load_json(task_dir / 'artifacts' / 'release_rollback_parity_matrix.json')
    future_executor_implementation_blueprint = _load_json(task_dir / 'artifacts' / 'future_executor_implementation_blueprint.json')
    real_executor_delivery_backlog = _load_json(task_dir / 'artifacts' / 'real_executor_delivery_backlog.json')
    executor_acceptance_test_pack = _load_json(task_dir / 'artifacts' / 'executor_acceptance_test_pack.json')
    executor_ownership_split = _load_json(task_dir / 'artifacts' / 'executor_ownership_split.json')
    executor_blocker_matrix = _load_json(task_dir / 'artifacts' / 'executor_blocker_matrix.json')
    executor_cutover_readiness_pack = _load_json(task_dir / 'artifacts' / 'executor_cutover_readiness_pack.json')
    real_executor_integration_checklist = _load_json(task_dir / 'artifacts' / 'real_executor_integration_checklist.json')
    executor_risk_register = _load_json(task_dir / 'artifacts' / 'executor_risk_register.json')
    future_executor_handoff_summary = _load_json(task_dir / 'artifacts' / 'future_executor_handoff_summary.json')
    executor_credential_binding_policy = _load_json(task_dir / 'artifacts' / 'executor_credential_binding_policy.json')
    executor_target_binding_registry = _load_json(task_dir / 'artifacts' / 'executor_target_binding_registry.json')
    cutover_signoff_workflow = _load_json(task_dir / 'artifacts' / 'cutover_signoff_workflow.json')
    blocker_drilldown_review = _load_json(task_dir / 'artifacts' / 'blocker_drilldown_review.json')
    executor_human_action_pack = _load_json(task_dir / 'artifacts' / 'executor_human_action_pack.json')
    credential_binding_evidence_checklist = _load_json(task_dir / 'artifacts' / 'credential_binding_evidence_checklist.json')
    cutover_signoff_evidence_packet = _load_json(task_dir / 'artifacts' / 'cutover_signoff_evidence_packet.json')
    unresolved_blocker_tracker = _load_json(task_dir / 'artifacts' / 'unresolved_blocker_tracker.json')
    pending_human_action_board = _load_json(task_dir / 'artifacts' / 'pending_human_action_board.json')
    credential_binding_runbook = _load_json(task_dir / 'artifacts' / 'credential_binding_runbook.json')
    cutover_signoff_runbook = _load_json(task_dir / 'artifacts' / 'cutover_signoff_runbook.json')
    blocker_resolution_playbook = _load_json(task_dir / 'artifacts' / 'blocker_resolution_playbook.json')
    post_execution_observation = _load_json(task_dir / 'artifacts' / 'post_execution_observation.json')
    release_observation_summary = _load_json(task_dir / 'artifacts' / 'release_observation_summary.json')
    rollback_observation_summary = _load_json(task_dir / 'artifacts' / 'rollback_observation_summary.json')
    release_observation_audit = _load_json(task_dir / 'artifacts' / 'release_observation_audit.json')
    rollback_observation_audit = _load_json(task_dir / 'artifacts' / 'rollback_observation_audit.json')
    release_followup_protocol = _load_json(task_dir / 'artifacts' / 'release_observation_followup_protocol.json')
    rollback_followup_protocol = _load_json(task_dir / 'artifacts' / 'rollback_observation_followup_protocol.json')
    post_approval_transition = _load_json(task_dir / 'artifacts' / 'post_approval_guardrail_transition.json')
    human_result_visible = bool(human_approval_result)
    human_result_recorded = bool(human_approval_result.get('decision_recorded')) and human_approval_result.get('decision_source') != 'human_approval_result_not_connected'
    human_result_value = human_approval_result.get('approved') if human_result_recorded else None
    human_input_recorded = bool(human_approval_input.get('input_recorded')) and human_result_recorded
    raw_recompute_state = approval_recompute.get('recompute_state')
    if raw_recompute_state == 'approved_recompute_placeholder':
        approval_recompute_state = 'approved_recompute'
    elif raw_recompute_state == 'rejected_recompute_placeholder' and not human_result_recorded:
        approval_recompute_state = 'awaiting_real_human_decision'
    elif raw_recompute_state == 'rejected_recompute_placeholder':
        approval_recompute_state = 'rejected_recompute'
    else:
        approval_recompute_state = raw_recompute_state
    if human_result_visible:
        if human_result_recorded and human_result_value is True:
            human_approval_state = 'approved'
        elif human_result_recorded and human_result_value is False:
            human_approval_state = 'rejected'
        elif human_result_recorded:
            human_approval_state = 'invalid'
        else:
            human_approval_state = 'awaiting'
    else:
        human_approval_state = None

    release_execution_confirmation_visible = bool(release_execution_confirmation or release_execution_status)
    rollback_execution_confirmation_visible = bool(rollback_execution_confirmation or rollback_execution_status)

    if release_execution_status:
        release_execution_confirmation_state = release_execution_status.get('confirmation_state')
    elif human_approval_state == 'approved' and release_preflight.get('preflight_ready'):
        release_execution_confirmation_state = 'planned_not_started'
    elif human_approval_state == 'rejected':
        release_execution_confirmation_state = 'not_allowed'
    else:
        release_execution_confirmation_state = None

    if rollback_execution_status:
        rollback_execution_confirmation_state = rollback_execution_status.get('confirmation_state')
    elif human_approval_state == 'approved' and rollback_entry.get('rollback_supported'):
        rollback_execution_confirmation_state = 'planned_not_started'
    elif human_approval_state == 'rejected':
        rollback_execution_confirmation_state = 'not_allowed'
    else:
        rollback_execution_confirmation_state = None
    return {
        'approval_required': approval.get('approval_required'),
        'approved': human_result_value if human_result_visible else approval.get('approved'),
        'human_approval_state': human_approval_state,
        'approval_checklist_ready': approval_checklist.get('checklist_ready'),
        'approval_status': approval_outcome.get('approval_status'),
        'approval_decision_recorded': approval_decision.get('decision_recorded'),
        'approval_transition_visible': bool(approval_transition),
        'human_approval_input_slot_visible': bool(human_approval_input),
        'human_approval_input_slot_ready': human_approval_input.get('slot_ready'),
        'human_approval_input_recorded': human_input_recorded,
        'human_approval_result_recorded': human_result_recorded,
        'human_approval_result_visible': human_result_visible,
        'approval_recompute_visible': bool(approval_recompute),
        'approval_recompute_state': approval_recompute_state,
        'approval_recompute_would_unblock': approval_recompute.get('would_unblock_execution'),
        'approval_recompute_official_ready': approval_recompute.get('would_mark_official_release_ready'),
        'release_action_allowed': release_action.get('action_allowed'),
        'release_next_step': release_action.get('next_step'),
        'release_preflight_ready': release_preflight.get('preflight_ready'),
        'pre_release_ready': pre_release_gate.get('pre_release_ready'),
        'pre_release_gate_state': pre_release_gate.get('gate_state'),
        'closure_consistency_ready': closure_consistency.get('consistency_ready'),
        'closure_contradiction_count': len(closure_consistency.get('contradictions', [])) if closure_consistency else None,
        'official_release_rehearsal_ready': official_release_rehearsal.get('rehearsal_ready'),
        'official_release_rehearsal_state': official_release_rehearsal.get('rehearsal_state'),
        'release_execution_blocked': execution_guardrail.get('execution_blocked'),
        'release_execution_state': execution_guardrail.get('execution_state'),
        'release_execution_block_reasons': list(execution_guardrail.get('block_reasons', []) or []),
        'post_approval_transition_visible': bool(post_approval_transition),
        'post_approval_execution_unblocked': post_approval_transition.get('execution_unblocked'),
        'official_release_state_visible': bool(official_release_state),
        'official_release_state': official_release_state.get('official_release_state'),
        'official_release_pipeline_visible': bool(official_release_pipeline_summary),
        'official_release_pipeline_state': official_release_pipeline_summary.get('pipeline_state'),
        'official_release_pipeline_blockers': list(official_release_pipeline_summary.get('blockers', []) or []),
        'official_release_pipeline_executable': official_release_pipeline_summary.get('official_release_executable'),
        'official_release_execution_precheck_visible': bool(official_release_execution_precheck),
        'official_release_execution_precheck_ready': official_release_execution_precheck.get('precheck_ready'),
        'rollback_execution_precheck_visible': bool(rollback_execution_precheck),
        'rollback_execution_precheck_ready': rollback_execution_precheck.get('precheck_ready'),
        'release_execution_confirmation_visible': release_execution_confirmation_visible,
        'release_execution_confirmation_state': release_execution_confirmation_state,
        'release_execution_confirmation_recorded_at': release_execution_status.get('updated_at'),
        'release_execution_confirmation_recorded_by': release_execution_status.get('latest_actor'),
        'rollback_execution_confirmation_visible': rollback_execution_confirmation_visible,
        'rollback_execution_confirmation_state': rollback_execution_confirmation_state,
        'rollback_execution_confirmation_recorded_at': rollback_execution_status.get('updated_at'),
        'rollback_execution_confirmation_recorded_by': rollback_execution_status.get('latest_actor'),
        'execution_batch_visible': bool(execution_batch),
        'execution_batch_id': execution_batch.get('batch_id'),
        'release_run_id': execution_batch.get('release_run_id'),
        'rollback_run_id': execution_batch.get('rollback_run_id'),
        'current_run_id': post_execution_observation.get('run_id') or rollback_execution_protocol.get('run_id') or release_execution_protocol.get('run_id') or release_execution_receipt.get('run_id') or rollback_execution_receipt.get('run_id'),
        'executor_contract_available': bool(release_executor_contract and rollback_executor_contract),
        'release_executor_contract_available': bool(release_executor_contract),
        'rollback_executor_contract_available': bool(rollback_executor_contract),
        'dry_run_available': bool(release_execution_dry_run and rollback_execution_dry_run),
        'release_dry_run_available': bool(release_execution_dry_run),
        'rollback_dry_run_available': bool(rollback_execution_dry_run),
        'execution_receipt_protocol_available': bool(_load_json(task_dir / 'artifacts' / 'execution_receipt.schema.json') or execution_control_summary.get('execution_receipt_protocol_available')),
        'handoff_packet_available': bool(release_handoff_packet and rollback_handoff_packet),
        'operator_execution_request_available': bool(release_operator_execution_request and rollback_operator_execution_request),
        'receipt_correlation_ready': bool((release_handoff_packet.get('receipt_correlation_contract') or {}).get('correlation_ready')) and bool((rollback_handoff_packet.get('receipt_correlation_contract') or {}).get('correlation_ready')),
        'execution_request_lifecycle_visible': bool(execution_request_lifecycle),
        'operator_acknowledgement_review_visible': bool(operator_acknowledgement_review),
        'release_execution_requested': bool(release_execution_request),
        'rollback_execution_requested': bool(rollback_execution_request),
        'execution_request_requested_count': execution_control_summary.get('execution_request_requested_count', operator_acknowledgement_review.get('execution_request_requested_count')),
        'execution_request_acknowledged_count': execution_control_summary.get('execution_request_acknowledged_count', operator_acknowledgement_review.get('execution_request_acknowledged_count')),
        'execution_request_accepted_count': execution_control_summary.get('execution_request_accepted_count', operator_acknowledgement_review.get('execution_request_accepted_count')),
        'execution_request_declined_count': execution_control_summary.get('execution_request_declined_count', operator_acknowledgement_review.get('execution_request_declined_count')),
        'execution_request_expired_count': execution_control_summary.get('execution_request_expired_count', operator_acknowledgement_review.get('execution_request_expired_count')),
        'request_open_count': execution_control_summary.get('request_open_count', execution_request_registry.get('request_open_count', operator_acknowledgement_review.get('request_open_count'))),
        'request_inflight_count': execution_control_summary.get('request_inflight_count', execution_request_registry.get('request_inflight_count', operator_acknowledgement_review.get('request_inflight_count'))),
        'execution_request_reassigned_count': execution_control_summary.get('execution_request_reassigned_count', operator_acknowledgement_review.get('execution_request_reassigned_count', execution_request_escalation_review.get('execution_request_reassigned_count'))),
        'execution_request_escalated_count': execution_control_summary.get('execution_request_escalated_count', operator_acknowledgement_review.get('execution_request_escalated_count', execution_request_escalation_review.get('execution_request_escalated_count'))),
        'execution_request_retry_ready_count': execution_control_summary.get('execution_request_retry_ready_count', operator_acknowledgement_review.get('execution_request_retry_ready_count', execution_request_retry_summary.get('execution_request_retry_ready_count'))),
        'top_request_states': execution_control_summary.get('top_request_states', operator_acknowledgement_review.get('top_request_states', [])),
        'top_pending_requests': execution_control_summary.get('top_pending_requests', execution_request_dispatch_review.get('top_pending_requests', execution_request_registry.get('top_pending_requests', []))),
        'recent_request_actions': execution_control_summary.get('recent_request_actions', operator_acknowledgement_review.get('recent_request_actions', [])),
        'recent_request_transitions': execution_control_summary.get('recent_request_transitions', execution_request_dispatch_review.get('recent_request_transitions', execution_request_registry.get('recent_request_transitions', []))),
        'recent_request_escalations': execution_control_summary.get('recent_request_escalations', execution_request_escalation_review.get('recent_request_escalations', [])),
        'top_request_owners': execution_control_summary.get('top_request_owners', execution_request_escalation_review.get('top_request_owners', [])),
        'release_request_state': ((execution_request_lifecycle.get('requests') or {}).get('release') or {}).get('request_state'),
        'rollback_request_state': ((execution_request_lifecycle.get('requests') or {}).get('rollback') or {}).get('request_state'),
        'release_execution_dry_run_validated': release_execution_dry_run.get('dry_run_validated'),
        'rollback_execution_dry_run_validated': rollback_execution_dry_run.get('dry_run_validated'),
        'release_execution_receipt_recorded': bool(release_execution_receipt),
        'rollback_execution_receipt_recorded': bool(rollback_execution_receipt),
        'executor_readiness_review_visible': bool(executor_readiness_review or execution_control_summary.get('executor_readiness_review_available')),
        'executor_adapter_available_count': execution_control_summary.get('executor_adapter_available_count', sum(1 for payload in (release_adapter_manifest, rollback_adapter_manifest) if payload)),
        'executor_capability_registry_available': bool(executor_capability_registry or execution_control_summary.get('executor_capability_registry_available')),
        'invocation_policy_available': bool(invocation_policy_review or execution_control_summary.get('invocation_policy_available')),
        'future_executor_scaffold_available': bool(execution_control_summary.get('future_executor_scaffold_available') or _load_json(task_dir / 'artifacts' / 'executor_plugin_review.json')),
        'executor_plugin_interface_available': bool(execution_control_summary.get('executor_plugin_interface_available') or (_load_json(task_dir / 'artifacts' / 'release_executor_plugin_interface.json') and _load_json(task_dir / 'artifacts' / 'rollback_executor_plugin_interface.json'))),
        'transcript_contract_available': bool(execution_control_summary.get('transcript_contract_available') or _load_json(task_dir / 'artifacts' / 'execution_transcript_contract.json')),
        'no_op_executor_available': bool(execution_control_summary.get('no_op_executor_available') or (_load_json(task_dir / 'artifacts' / 'release_no_op_executor_adapter.json') and _load_json(task_dir / 'artifacts' / 'rollback_no_op_executor_adapter.json'))),
        'executor_conformance_available': bool(execution_control_summary.get('executor_conformance_available') or executor_conformance_matrix.get('executor_conformance_available')),
        'executor_error_contract_available': bool(execution_control_summary.get('executor_error_contract_available') or executor_error_contract.get('executor_error_contract_available')),
        'release_rollback_parity_available': bool(execution_control_summary.get('release_rollback_parity_available') or release_rollback_parity_matrix.get('release_rollback_parity_available')),
        'implementation_blueprint_available': bool(execution_control_summary.get('implementation_blueprint_available') or future_executor_implementation_blueprint.get('implementation_blueprint_available')),
        'executor_delivery_pack_available': bool(execution_control_summary.get('executor_delivery_pack_available') or real_executor_delivery_backlog.get('executor_delivery_pack_available')),
        'executor_acceptance_pack_available': bool(execution_control_summary.get('executor_acceptance_pack_available') or executor_acceptance_test_pack.get('executor_acceptance_pack_available')),
        'ownership_split_available': bool(execution_control_summary.get('ownership_split_available') or executor_ownership_split.get('ownership_split_available')),
        'executor_blocker_matrix_available': bool(execution_control_summary.get('executor_blocker_matrix_available') or executor_blocker_matrix.get('executor_blocker_matrix_available')),
        'executor_delivery_item_count': execution_control_summary.get('executor_delivery_item_count', real_executor_delivery_backlog.get('delivery_item_count')),
        'executor_acceptance_case_count': execution_control_summary.get('executor_acceptance_case_count', executor_acceptance_test_pack.get('test_case_count')),
        'executor_blocker_count': execution_control_summary.get('executor_blocker_count', executor_blocker_matrix.get('executor_blocker_count')),
        'cutover_pack_available': bool(execution_control_summary.get('cutover_pack_available') or executor_cutover_readiness_pack.get('cutover_pack_available')),
        'integration_checklist_available': bool(execution_control_summary.get('integration_checklist_available') or real_executor_integration_checklist.get('integration_checklist_available')),
        'risk_register_available': bool(execution_control_summary.get('risk_register_available') or executor_risk_register.get('risk_register_available')),
        'handoff_summary_available': bool(execution_control_summary.get('handoff_summary_available') or future_executor_handoff_summary.get('handoff_summary_available')),
        'credential_binding_policy_available': bool(execution_control_summary.get('credential_binding_policy_available') or executor_credential_binding_policy.get('credential_binding_policy_available')),
        'target_binding_registry_available': bool(execution_control_summary.get('target_binding_registry_available') or executor_target_binding_registry.get('target_binding_registry_available')),
        'cutover_signoff_available': bool(execution_control_summary.get('cutover_signoff_available') or cutover_signoff_workflow.get('cutover_signoff_available')),
        'blocker_drilldown_available': bool(execution_control_summary.get('blocker_drilldown_available') or blocker_drilldown_review.get('blocker_drilldown_available')),
        'human_action_pack_available': bool(execution_control_summary.get('human_action_pack_available') or executor_human_action_pack.get('human_action_pack_available')),
        'credential_binding_evidence_checklist_available': bool(execution_control_summary.get('credential_binding_evidence_checklist_available') or credential_binding_evidence_checklist.get('credential_binding_evidence_checklist_available')),
        'signoff_evidence_packet_available': bool(execution_control_summary.get('signoff_evidence_packet_available') or cutover_signoff_evidence_packet.get('cutover_signoff_evidence_packet_available')),
        'unresolved_blocker_tracker_available': bool(execution_control_summary.get('unresolved_blocker_tracker_available') or unresolved_blocker_tracker.get('unresolved_blocker_tracker_available')),
        'pending_human_action_board_available': bool(execution_control_summary.get('pending_human_action_board_available') or pending_human_action_board.get('pending_human_action_board_available')),
        'credential_binding_runbook_available': bool(execution_control_summary.get('credential_binding_runbook_available') or credential_binding_runbook.get('credential_binding_runbook_available')),
        'signoff_runbook_available': bool(execution_control_summary.get('signoff_runbook_available') or cutover_signoff_runbook.get('signoff_runbook_available')),
        'blocker_resolution_playbook_available': bool(execution_control_summary.get('blocker_resolution_playbook_available') or blocker_resolution_playbook.get('blocker_resolution_playbook_available')),
        'unresolved_credential_binding_count': execution_control_summary.get('unresolved_credential_binding_count', int((executor_credential_binding_policy.get('unresolved_binding_count', 0) or 0)) + int((executor_target_binding_registry.get('unresolved_binding_count', 0) or 0))),
        'unresolved_signoff_count': execution_control_summary.get('unresolved_signoff_count', int(cutover_signoff_workflow.get('unresolved_signoff_count', 0) or 0)),
        'unresolved_blocker_owner_count': execution_control_summary.get('unresolved_blocker_owner_count', int(unresolved_blocker_tracker.get('unresolved_blocker_owner_count', 0) or 0)),
        'pending_signoff_role_count': execution_control_summary.get('pending_signoff_role_count', int(cutover_signoff_evidence_packet.get('pending_signoff_role_count', 0) or 0)),
        'binding_evidence_gap_count': execution_control_summary.get('binding_evidence_gap_count', int(credential_binding_evidence_checklist.get('binding_evidence_gap_count', 0) or 0)),
        'top_blocker_categories': execution_control_summary.get('top_blocker_categories', list(blocker_drilldown_review.get('top_blocker_categories') or [])),
        'top_human_actions': execution_control_summary.get('top_human_actions', list(executor_human_action_pack.get('top_human_actions') or [])),
        'top_pending_human_actions': execution_control_summary.get('top_pending_human_actions', list(pending_human_action_board.get('top_pending_human_actions') or [])),
        'top_unresolved_human_blockers': execution_control_summary.get('top_unresolved_human_blockers', list(executor_human_action_pack.get('top_unresolved_human_blockers') or blocker_resolution_playbook.get('top_unresolved_human_blockers') or [])),
        'top_missing_executor_contracts': execution_control_summary.get('top_missing_executor_contracts', [item.get('gap_id') for item in (executor_conformance_matrix.get('top_missing_executor_contracts') or []) if item.get('gap_id')]),
        'parity_gaps': execution_control_summary.get('parity_gaps', list(release_rollback_parity_matrix.get('parity_gaps') or [])),
        'top_executor_risks': execution_control_summary.get('top_executor_risks', list(executor_risk_register.get('top_executor_risks') or [])),
        'top_executor_blockers': execution_control_summary.get('top_executor_blockers', list(executor_blocker_matrix.get('top_executor_blockers') or [])),
        'top_remaining_blockers': execution_control_summary.get('top_remaining_blockers', list(real_executor_integration_checklist.get('top_remaining_blockers') or executor_risk_register.get('top_remaining_blockers') or [])),
        'environment_guard_ok_count': execution_control_summary.get('environment_guard_ok_count', sum(1 for payload in (release_adapter_manifest, rollback_adapter_manifest) if (payload.get('environment_guard') or {}).get('guard_ok'))),
        'environment_guard_unmet_count': execution_control_summary.get('environment_guard_unmet_count', sum(len((payload.get('environment_guard') or {}).get('unmet_guard_checks', [])) for payload in (release_adapter_manifest, rollback_adapter_manifest) if payload)),
        'top_executor_adapter_types': execution_control_summary.get('top_executor_adapter_types', (executor_capability_registry.get('top_executor_adapter_types') if executor_capability_registry else [])),
        'top_executor_plugin_targets': execution_control_summary.get('top_executor_plugin_targets', ((_load_json(task_dir / 'artifacts' / 'executor_plugin_review.json') or {}).get('top_executor_plugin_targets', []))),
        'handoff_boundary_ready': bool(real_executor_handoff_boundary.get('handoff_boundary_ready') if real_executor_handoff_boundary else execution_control_summary.get('handoff_boundary_ready')),
        'top_execution_handoff_targets': [name for name, packet in [('release', release_handoff_packet), ('rollback', rollback_handoff_packet)] if packet],
        'top_command_plan_steps': [step.get('title') for step in (((release_handoff_packet.get('command_plan') or {}).get('steps') or []) + ((rollback_handoff_packet.get('command_plan') or {}).get('steps') or []))[:5]],
        'executor_readiness_gate_count': execution_control_summary.get('executor_readiness_gate_count', executor_readiness_review.get('executor_readiness_gate_count')),
        'executor_unmet_gate_count': execution_control_summary.get('executor_unmet_gate_count', executor_readiness_review.get('executor_unmet_gate_count')),
        'top_unmet_executor_gates': execution_control_summary.get('top_unmet_executor_gates', executor_readiness_review.get('top_unmet_executor_gates', [])),
        'readiness_gate_counts': execution_control_summary.get('readiness_gate_counts', executor_readiness_review.get('readiness_gate_counts', {})),
        'unmet_gate_counts': execution_control_summary.get('unmet_gate_counts', executor_readiness_review.get('unmet_gate_counts', {})),
        'executor_admission_available': bool(executor_admission_review or execution_control_summary.get('executor_admission_available')),
        'go_no_go_available': bool(go_no_go_decision_pack or execution_control_summary.get('go_no_go_available')),
        'rollout_gate_count': execution_control_summary.get('rollout_gate_count', rollout_gate_registry.get('rollout_gate_count', 0)),
        'rollout_unmet_count': execution_control_summary.get('rollout_unmet_count', rollout_gate_registry.get('unmet_count', 0)),
        'waiver_exception_count': execution_control_summary.get('waiver_exception_count', waiver_exception_registry.get('waiver_exception_count', 0)),
        'overall_admission_state': execution_control_summary.get('overall_admission_state', executor_admission_review.get('overall_admission_state')),
        'top_blocking_gates': execution_control_summary.get('top_blocking_gates', executor_admission_review.get('top_blocking_gates', rollout_gate_registry.get('top_blocking_gates', []))),
        'executor_simulation_available_count': execution_control_summary.get('executor_simulation_available_count'),
        'executor_simulation_pass_count': execution_control_summary.get('executor_simulation_pass_count'),
        'executor_simulation_fail_count': execution_control_summary.get('executor_simulation_fail_count'),
        'contract_compliance_available': execution_control_summary.get('contract_compliance_available'),
        'integration_rehearsal_available': execution_control_summary.get('integration_rehearsal_available'),
        'top_executor_contract_gaps': execution_control_summary.get('top_executor_contract_gaps', []),
        'executor_readiness_state': execution_control_summary.get('executor_readiness_state'),
        'release_execution_protocol_visible': bool(release_execution_protocol),
        'release_execution_protocol_state': release_execution_protocol.get('protocol_state'),
        'release_execution_protocol_latest_stage': release_execution_protocol.get('latest_stage'),
        'release_execution_protocol_timeline_event_count': release_execution_protocol.get('timeline_event_count'),
        'release_execution_protocol_run_id': release_execution_protocol.get('run_id'),
        'release_execution_protocol_batch_id': release_execution_protocol.get('batch_id'),
        'release_execution_approved_by': release_execution_protocol.get('approved_for_execution_by'),
        'release_execution_started_by': release_execution_protocol.get('execution_started_by'),
        'release_execution_completed_by': release_execution_protocol.get('execution_completed_by'),
        'release_execution_registered_by': release_execution_protocol.get('execution_registered_by'),
        'rollback_execution_protocol_visible': bool(rollback_execution_protocol),
        'rollback_execution_protocol_state': rollback_execution_protocol.get('protocol_state'),
        'rollback_execution_protocol_latest_stage': rollback_execution_protocol.get('latest_stage'),
        'rollback_execution_protocol_timeline_event_count': rollback_execution_protocol.get('timeline_event_count'),
        'rollback_execution_protocol_run_id': rollback_execution_protocol.get('run_id'),
        'rollback_execution_protocol_batch_id': rollback_execution_protocol.get('batch_id'),
        'rollback_execution_approved_by': rollback_execution_protocol.get('approved_for_execution_by'),
        'rollback_execution_started_by': rollback_execution_protocol.get('execution_started_by'),
        'rollback_execution_completed_by': rollback_execution_protocol.get('execution_completed_by'),
        'rollback_execution_registered_by': rollback_execution_protocol.get('execution_registered_by'),
        'post_execution_observation_visible': bool(post_execution_observation),
        'post_execution_observation_target': post_execution_observation.get('execution_target'),
        'post_execution_observation_state': post_execution_observation.get('observation_state'),
        'post_execution_observation_active': post_execution_observation.get('observation_window_active'),
        'post_execution_observation_completed': post_execution_observation.get('observation_completed'),
        'post_execution_observation_failed': post_execution_observation.get('observation_failed'),
        'post_execution_observation_timed_out': post_execution_observation.get('observation_timed_out'),
        'post_execution_observation_sla_state': post_execution_observation.get('sla_state'),
        'post_execution_observation_is_overdue': post_execution_observation.get('is_overdue'),
        'post_execution_observation_is_timed_out': post_execution_observation.get('is_timed_out'),
        'post_execution_observation_deadline_at': post_execution_observation.get('deadline_at'),
        'post_execution_observation_timeout_at': post_execution_observation.get('timeout_at'),
        'post_execution_observation_requires_manual_followup': post_execution_observation.get('requires_manual_followup'),
        'post_execution_observation_manual_followup_reason': list(post_execution_observation.get('manual_followup_reason', []) or []),
        'post_execution_observation_history_count': len(post_execution_observation.get('history', []) or []) + (1 if post_execution_observation.get('opened_at') else 0),
        'post_execution_observation_latest_result': (post_execution_observation.get('observation_state') or ((post_execution_observation.get('history') or [])[-1].get('observation_state') if (post_execution_observation.get('history') or []) else None)),
        'post_execution_observation_summary_visible': post_execution_observation.get('observation_summary_visible'),
        'post_execution_observation_signal_count': post_execution_observation.get('observation_signal_count'),
        'post_execution_observation_drift_count': post_execution_observation.get('observation_drift_count'),
        'post_execution_observation_mismatch_count': post_execution_observation.get('observation_mismatch_count'),
        'post_execution_observation_anomaly_count': post_execution_observation.get('observation_anomaly_count'),
        'post_execution_observation_run_id': post_execution_observation.get('run_id'),
        'post_execution_observation_batch_id': post_execution_observation.get('batch_id'),
        'post_execution_observation_opened_at': post_execution_observation.get('opened_at'),
        'post_execution_observation_closed_at': post_execution_observation.get('closed_at'),
        'post_execution_observation_escalation_level': (release_followup_protocol or rollback_followup_protocol).get('escalation_level'),
        'post_execution_observation_queue_priority': (release_followup_protocol or rollback_followup_protocol).get('queue_priority'),
        'post_execution_observation_queue_priority_rank': (release_followup_protocol or rollback_followup_protocol).get('queue_priority_rank'),
        'post_execution_observation_recommended_owner': (release_followup_protocol or rollback_followup_protocol).get('recommended_owner'),
        'post_execution_observation_recommended_routing_target': (release_followup_protocol or rollback_followup_protocol).get('recommended_routing_target'),
        'post_execution_observation_routing_targets': list((release_followup_protocol or rollback_followup_protocol).get('routing_targets', []) or []),
        'post_execution_observation_followup_action_count': (release_followup_protocol or rollback_followup_protocol).get('action_count'),
        'post_execution_observation_followup_item_state': (release_followup_protocol or rollback_followup_protocol).get('followup_item_state'),
        'post_execution_observation_followup_item_open': (release_followup_protocol or rollback_followup_protocol).get('followup_item_open'),
        'post_execution_observation_followup_terminal': (release_followup_protocol or rollback_followup_protocol).get('followup_terminal'),
        'post_execution_observation_followup_last_action': (release_followup_protocol or rollback_followup_protocol).get('followup_last_action'),
        'post_execution_observation_followup_last_action_at': (release_followup_protocol or rollback_followup_protocol).get('followup_last_action_at'),
        'post_execution_observation_followup_last_actor': (release_followup_protocol or rollback_followup_protocol).get('followup_last_actor'),
        'post_execution_observation_followup_owner': (release_followup_protocol or rollback_followup_protocol).get('followup_owner'),
        'post_execution_observation_followup_assignee': (release_followup_protocol or rollback_followup_protocol).get('followup_assignee'),
        'post_execution_observation_followup_assignment_status': (release_followup_protocol or rollback_followup_protocol).get('followup_assignment_status'),
        'post_execution_observation_followup_handoff_count': (release_followup_protocol or rollback_followup_protocol).get('followup_handoff_count'),
        'post_execution_observation_followup_handoff_history': (release_followup_protocol or rollback_followup_protocol).get('followup_handoff_history'),
        'post_execution_observation_followup_resolution_category': (release_followup_protocol or rollback_followup_protocol).get('followup_resolution_category'),
        'post_execution_observation_followup_resolution_taxonomy': (release_followup_protocol or rollback_followup_protocol).get('followup_resolution_taxonomy'),
        'post_execution_observation_followup_resolution_summary': (release_followup_protocol or rollback_followup_protocol).get('followup_resolution_summary'),
        'post_execution_observation_followup_closure_audit': (release_followup_protocol or rollback_followup_protocol).get('followup_closure_audit'),
        'post_execution_observation_followup_backfill': (release_followup_protocol or rollback_followup_protocol).get('followup_backfill'),
        'post_execution_observation_followup_manual_classification_required': ((release_followup_protocol or rollback_followup_protocol).get('followup_backfill') or {}).get('manual_classification_required'),
        'post_execution_observation_followup_resolution_review_artifact': (release_followup_protocol or rollback_followup_protocol).get('resolution_review_artifact'),
        'post_execution_observation_manual_classification_workflow': (release_followup_protocol or rollback_followup_protocol).get('manual_classification_workflow'),
        'post_execution_observation_manual_classification_state': ((release_followup_protocol or rollback_followup_protocol).get('manual_classification_workflow') or {}).get('state'),
        'post_execution_observation_followup_status_counts': (release_followup_protocol or rollback_followup_protocol).get('status_counts'),
        'release_observation_summary_visible': bool(release_observation_summary),
        'release_observation_summary_state': release_observation_summary.get('observation_state'),
        'release_observation_anomaly_count': release_observation_summary.get('anomaly_count'),
        'rollback_observation_summary_visible': bool(rollback_observation_summary),
        'rollback_observation_summary_state': rollback_observation_summary.get('observation_state'),
        'rollback_observation_anomaly_count': rollback_observation_summary.get('anomaly_count'),
        'release_observation_audit_visible': bool(release_observation_audit),
        'rollback_observation_audit_visible': bool(rollback_observation_audit),
        'execution_control_summary_visible': bool(execution_control_summary),
        'real_executor_handoff_boundary_visible': bool(real_executor_handoff_boundary),
        'execution_audit_summary_visible': bool(execution_audit_summary),
        'execution_audit_release_registration_expected': execution_audit_summary.get('release_registration_expected'),
        'execution_audit_rollback_registration_expected': execution_audit_summary.get('rollback_registration_expected'),
        'official_release_registered': bool(official_release_record),
        'official_release_record_state': official_release_record.get('record_state'),
        'official_release_version': official_release_record.get('release_version'),
        'official_release_registered_at': official_release_record.get('executed_at'),
        'rollback_registered': bool(rollback_registration_record),
        'rollback_record_state': rollback_registration_record.get('record_state'),
        'rollback_version': rollback_registration_record.get('rollback_version'),
        'rolled_back_release_version': rollback_registration_record.get('rolled_back_release_version'),
        'rollback_registered_at': rollback_registration_record.get('executed_at'),
        'release_artifact_binding_visible': bool(release_artifact_binding),
        'release_artifact_binding_ready': release_artifact_binding.get('binding_ready'),
        'rollback_supported': rollback_entry.get('rollback_supported'),
        'closure_visible': bool(approval or approval_checklist or approval_outcome or approval_decision or approval_transition or human_approval_input or human_approval_result or approval_recompute or release_action or release_preflight or rollback_entry or release_artifact_binding or pre_release_gate or closure_consistency or official_release_rehearsal or execution_guardrail or official_release_state or official_release_pipeline_summary or official_release_record or rollback_registration_record or release_execution_confirmation or release_execution_status or rollback_execution_confirmation or rollback_execution_status or release_execution_protocol or rollback_execution_protocol or execution_control_summary or executor_readiness_review or real_executor_handoff_boundary or execution_audit_summary or execution_batch or release_executor_contract or rollback_executor_contract or release_adapter_manifest or rollback_adapter_manifest or executor_capability_registry or invocation_policy_review or release_execution_request or rollback_execution_request or release_execution_dry_run or rollback_execution_dry_run or release_execution_receipt or rollback_execution_receipt or execution_request_lifecycle or operator_acknowledgement_review or post_execution_observation or release_observation_summary or rollback_observation_summary or release_observation_audit or rollback_observation_audit or post_approval_transition),
    }
