#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import shutil
from pathlib import Path

from artifact_manager import ArtifactManager
from backfill_runtime import backfill_task
from controlled_execution_runtime import acknowledge_execution_request, build_executor_adapter_artifacts, build_executor_admission_artifacts, build_executor_contract_artifacts, build_future_executor_scaffold_artifacts, build_rollout_gate_registry, build_waiver_exception_registry, dry_run_controlled_execution, govern_execution_request, materialize_controlled_executor
from human_approval_runtime import record_human_approval
from official_release_execution_runtime import prepare_execution_path
from release_closure_runtime import _load_json, load_release_closure_snapshot
from task_queue import TaskQueue
from worker_runtime_scheduler import run_cycle

ROOT = Path('/home/admin/.openclaw/workspace/master')
JOBS_ROOT = ROOT / 'traces' / 'jobs'
STATE_ROOT = ROOT / 'reports' / 'worker-runtime' / 'state'
TASK_ID = 'validation_controlled_execution_runtime'


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _reset_task() -> Path:
    task_dir = JOBS_ROOT / TASK_ID
    if task_dir.exists():
        shutil.rmtree(task_dir)
    queue = TaskQueue(JOBS_ROOT)
    queue.create_task({
        'task_id': TASK_ID,
        'role': 'doc-manager',
        'objective': 'validate controlled executor contracts and dry-run receipt protocol',
        'constraints': ['no automatic release', 'no automatic rollback', 'dry-run only'],
        'acceptance_criteria': ['controlled executor artifacts available', 'receipt traceability available'],
        'downstream': 'knowledge-steward',
        'metadata': {'manual_review_required': False},
    })
    (task_dir / 'review.json').write_text(json.dumps({'decision': 'passed', 'issues': [], 'evidence': ['validation fixture']}), encoding='utf-8')
    backfill_task(task_dir)
    manager = ArtifactManager(task_dir)
    manager.write_json('rollback_stub.json', {
        'task_id': TASK_ID,
        'rollback_supported': True,
        'official_release': False,
        'candidate_only': True,
        'rollback_artifacts': ['artifacts/rollback_registry_entry.json'],
    })
    manager.write_json('rollback_registry_entry.json', {
        'task_id': TASK_ID,
        'entry_type': 'candidate_stub',
        'official_release': False,
        'rollback_supported': True,
        'rollback_artifacts': ['artifacts/rollback_registry_entry.json'],
    })
    manager.write_json('approval_checklist.json', {'task_id': TASK_ID, 'checklist_ready': True, 'checks': []})
    manager.write_json('approval_outcome_stub.json', {
        'task_id': TASK_ID,
        'approval_status': 'pending_human_approval',
        'approved': False,
        'requires_human_approval': True,
        'next_step': 'record_human_approval_decision',
    })
    manager.write_json('release_preflight_stub.json', {
        'task_id': TASK_ID,
        'preflight_ready': True,
        'required_artifacts': [],
        'missing_artifacts': [],
        'next_step': 'request_human_approval',
    })
    manager.write_json('pre_release_gate.json', {
        'task_id': TASK_ID,
        'gate_state': 'ready_for_human_release_review',
        'pre_release_ready': True,
        'requires_human_approval': True,
        'approval_status': 'pending_human_approval',
        'formalization_state': 'release_ready_candidate',
        'rollback_supported': True,
        'release_preflight_ready': True,
    })
    manager.write_json('release_artifact_binding.json', {
        'task_id': TASK_ID,
        'binding_ready': True,
        'release_artifacts': ['artifacts/formalization_gate.json', 'artifacts/release_readiness.json'],
        'rollback_artifacts': ['artifacts/rollback_registry_entry.json'],
        'missing_release_artifacts': [],
        'missing_rollback_artifacts': [],
    })
    manager.write_json('release_closure_consistency.json', {
        'task_id': TASK_ID,
        'consistency_ready': True,
        'contradictions': [],
    })
    manager.write_json('official_release_rehearsal.json', {
        'task_id': TASK_ID,
        'rehearsal_ready': True,
        'rehearsal_state': 'validated_manual_only',
    })
    return task_dir


def main() -> int:
    task_dir = _reset_task()
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator', reason='controlled executor dry-run validation')
    prepare_execution_path(task_dir=task_dir)
    materialize_controlled_executor(task_dir, target='release')
    materialize_controlled_executor(task_dir, target='rollback')
    build_executor_adapter_artifacts(task_dir)
    build_future_executor_scaffold_artifacts(task_dir)
    build_executor_contract_artifacts(task_dir)
    build_rollout_gate_registry(task_dir)
    build_waiver_exception_registry(task_dir)
    build_executor_admission_artifacts(task_dir)
    build_executor_contract_artifacts(task_dir)

    release_result = dry_run_controlled_execution(
        task_dir,
        target='release',
        requested_by='validator',
        proposal_ref='proposal://validation/release',
        approval_ref='approval://validation/release',
    )
    rollback_result = dry_run_controlled_execution(
        task_dir,
        target='rollback',
        requested_by='validator',
        proposal_ref='proposal://validation/rollback',
        approval_ref='approval://validation/rollback',
    )
    acknowledge_execution_request(task_dir, target='release', action='acknowledge', acted_by='release-operator', note='release request received for dry-run-only rehearsal')
    govern_execution_request(task_dir, target='release', action='set-expiry-policy', acted_by='validator', timeout_minutes=15, note='release expiry policy armed for governance validation')
    govern_execution_request(task_dir, target='release', action='reassign', acted_by='validator', new_owner='release-backup-operator', reroute_target='release', note='release request rerouted after primary operator delay')
    govern_execution_request(task_dir, target='release', action='escalate', acted_by='validator', escalation_level='high', escalation_reason='release operator timeout risk before rehearsal slot', note='release request escalation for manual review')
    acknowledge_execution_request(task_dir, target='release', action='expire', acted_by='release-governor', note='release request expired without terminal commitment', reason='release operator timeout reached')
    govern_execution_request(task_dir, target='release', action='mark-retry-ready', acted_by='validator', retry_reason='release request governance cleared for manual retry after reassignment', reroute_target='release-backup-operator')
    acknowledge_execution_request(task_dir, target='rollback', action='acknowledge', acted_by='rollback-operator', note='rollback request received for dry-run-only rehearsal')
    govern_execution_request(task_dir, target='rollback', action='set-expiry-policy', acted_by='validator', timeout_minutes=10, note='rollback expiry policy armed for governance validation')
    govern_execution_request(task_dir, target='rollback', action='reassign', acted_by='validator', new_owner='rollback-backup-operator', reroute_target='rollback', note='rollback request rerouted after primary operator delay')
    govern_execution_request(task_dir, target='rollback', action='escalate', acted_by='validator', escalation_level='critical', escalation_reason='rollback readiness drill requires urgent reassignment after timeout risk', note='rollback request escalation for manual review')
    acknowledge_execution_request(task_dir, target='rollback', action='expire', acted_by='rollback-governor', note='rollback request expired without terminal commitment', reason='rollback operator timeout reached')
    govern_execution_request(task_dir, target='rollback', action='mark-retry-ready', acted_by='validator', retry_reason='rollback request governance cleared for manual retry after reassignment', reroute_target='rollback-backup-operator')

    snapshot = load_release_closure_snapshot(task_dir)
    _assert(release_result['dry_run_validated'] is True, 'release dry-run should validate')
    _assert(rollback_result['dry_run_validated'] is True, 'rollback dry-run should validate')
    _assert(release_result['states']['execution_confirmed'] is True, 'release execution_confirmed should be visible')
    _assert(rollback_result['states']['execution_confirmed'] is True, 'rollback execution_confirmed should be visible')
    _assert(snapshot.get('executor_contract_available') is True, 'snapshot should expose executor_contract_available')
    _assert(snapshot.get('dry_run_available') is True, 'snapshot should expose dry_run_available')
    _assert(snapshot.get('execution_receipt_protocol_available') is True, 'snapshot should expose execution_receipt_protocol_available')
    _assert(snapshot.get('handoff_packet_available') is True, 'snapshot should expose handoff_packet_available')
    _assert(snapshot.get('operator_execution_request_available') is True, 'snapshot should expose operator_execution_request_available')
    _assert(snapshot.get('receipt_correlation_ready') is True, 'snapshot should expose receipt_correlation_ready')
    _assert(snapshot.get('executor_readiness_review_visible') is True, 'snapshot should expose executor_readiness_review_visible')
    _assert(snapshot.get('future_executor_scaffold_available') is True, 'snapshot should expose future_executor_scaffold_available')
    _assert(snapshot.get('executor_plugin_interface_available') is True, 'snapshot should expose executor_plugin_interface_available')
    _assert(snapshot.get('transcript_contract_available') is True, 'snapshot should expose transcript_contract_available')
    _assert(snapshot.get('no_op_executor_available') is True, 'snapshot should expose no_op_executor_available')
    _assert(snapshot.get('executor_conformance_available') is True, 'snapshot should expose executor_conformance_available')
    _assert(snapshot.get('executor_error_contract_available') is True, 'snapshot should expose executor_error_contract_available')
    _assert(snapshot.get('release_rollback_parity_available') is True, 'snapshot should expose release_rollback_parity_available')
    _assert(snapshot.get('implementation_blueprint_available') is True, 'snapshot should expose implementation_blueprint_available')
    _assert(snapshot.get('cutover_pack_available') is True, 'snapshot should expose cutover_pack_available')
    _assert(snapshot.get('integration_checklist_available') is True, 'snapshot should expose integration_checklist_available')
    _assert(snapshot.get('risk_register_available') is True, 'snapshot should expose risk_register_available')
    _assert(snapshot.get('handoff_summary_available') is True, 'snapshot should expose handoff_summary_available')
    _assert(snapshot.get('credential_binding_policy_available') is True, 'snapshot should expose credential_binding_policy_available')
    _assert(snapshot.get('target_binding_registry_available') is True, 'snapshot should expose target_binding_registry_available')
    _assert(snapshot.get('cutover_signoff_available') is True, 'snapshot should expose cutover_signoff_available')
    _assert(snapshot.get('blocker_drilldown_available') is True, 'snapshot should expose blocker_drilldown_available')
    _assert(int(snapshot.get('unresolved_credential_binding_count') or 0) > 0, 'snapshot should expose unresolved_credential_binding_count')
    _assert(int(snapshot.get('unresolved_signoff_count') or 0) > 0, 'snapshot should expose unresolved_signoff_count')
    _assert(bool(snapshot.get('top_blocker_categories')), 'snapshot should expose top_blocker_categories')
    _assert(snapshot.get('top_missing_executor_contracts') == [], 'snapshot should expose empty top_missing_executor_contracts for clean fixture')
    _assert(snapshot.get('parity_gaps') == [], 'snapshot should expose empty parity_gaps for clean fixture')
    _assert(sorted(snapshot.get('top_remaining_blockers') or []) == ['credential_target_binding_unresolved', 'cutover_signoff_pending', 'real_release_executor_missing', 'real_rollback_executor_missing'], 'snapshot should expose top_remaining_blockers')
    _assert(bool(snapshot.get('top_executor_risks')), 'snapshot should expose top_executor_risks')
    _assert(sorted(snapshot.get('top_executor_plugin_targets') or []) == ['release', 'rollback'], 'snapshot should expose top_executor_plugin_targets')
    _assert(snapshot.get('handoff_boundary_ready') is True, 'snapshot should expose handoff_boundary_ready')
    _assert(snapshot.get('executor_readiness_state') == 'handoff_boundary_ready', 'snapshot should expose handoff boundary readiness state')
    _assert(int(snapshot.get('executor_readiness_gate_count') or 0) > 0, 'snapshot should expose executor_readiness_gate_count')
    _assert(int(snapshot.get('executor_unmet_gate_count', -1)) == 0, 'snapshot should expose zero unmet gates for validation fixture')
    _assert(snapshot.get('execution_request_lifecycle_visible') is True, 'snapshot should expose execution_request_lifecycle_visible')
    _assert(snapshot.get('operator_acknowledgement_review_visible') is True, 'snapshot should expose operator_acknowledgement_review_visible')
    _assert(any(item.get('action') == 'acknowledged' for item in (snapshot.get('recent_request_actions') or [])), 'snapshot should expose acknowledged request action history')
    _assert(int(snapshot.get('execution_request_expired_count') or 0) >= 2, 'snapshot should expose expired request count')
    _assert(int(snapshot.get('execution_request_reassigned_count') or 0) >= 2, 'snapshot should expose reassigned request count')
    _assert(int(snapshot.get('execution_request_escalated_count') or 0) >= 2, 'snapshot should expose escalated request count')
    _assert(int(snapshot.get('execution_request_retry_ready_count') or 0) >= 2, 'snapshot should expose retry-ready request count')
    _assert(bool(snapshot.get('recent_request_escalations')), 'snapshot should expose recent_request_escalations')
    _assert(bool(snapshot.get('top_request_owners')), 'snapshot should expose top_request_owners')
    _assert(not (task_dir / 'artifacts' / 'official_release_record.json').exists(), 'dry-run must not create official_release_record.json')
    _assert(not (task_dir / 'artifacts' / 'rollback_registration_record.json').exists(), 'dry-run must not create rollback_registration_record.json')

    readiness_review = _load_json(task_dir / 'artifacts' / 'executor_readiness_review.json')
    handoff_boundary = _load_json(task_dir / 'artifacts' / 'real_executor_handoff_boundary.json')
    release_adapter_manifest = _load_json(task_dir / 'artifacts' / 'release_executor_adapter_manifest.json')
    rollback_adapter_manifest = _load_json(task_dir / 'artifacts' / 'rollback_executor_adapter_manifest.json')
    capability_registry = _load_json(task_dir / 'artifacts' / 'executor_capability_registry.json')
    invocation_policy_review = _load_json(task_dir / 'artifacts' / 'invocation_policy_review.json')
    release_plugin_interface = _load_json(task_dir / 'artifacts' / 'release_executor_plugin_interface.json')
    rollback_plugin_interface = _load_json(task_dir / 'artifacts' / 'rollback_executor_plugin_interface.json')
    execution_transcript_contract = _load_json(task_dir / 'artifacts' / 'execution_transcript_contract.json')
    executor_plugin_review = _load_json(task_dir / 'artifacts' / 'executor_plugin_review.json')
    release_no_op_adapter = _load_json(task_dir / 'artifacts' / 'release_no_op_executor_adapter.json')
    rollback_no_op_adapter = _load_json(task_dir / 'artifacts' / 'rollback_no_op_executor_adapter.json')
    request_lifecycle = _load_json(task_dir / 'artifacts' / 'execution_request_lifecycle.json')
    acknowledgement_review = _load_json(task_dir / 'artifacts' / 'operator_acknowledgement_review.json')
    request_registry = _load_json(task_dir / 'artifacts' / 'execution_request_registry.json')
    dispatch_review = _load_json(task_dir / 'artifacts' / 'execution_request_dispatch_review.json')
    escalation_review = _load_json(task_dir / 'artifacts' / 'execution_request_escalation_review.json')
    retry_summary = _load_json(task_dir / 'artifacts' / 'execution_request_retry_summary.json')
    simulated_executor_run = _load_json(task_dir / 'artifacts' / 'simulated_executor_run.json')
    integration_rehearsal = _load_json(task_dir / 'artifacts' / 'executor_integration_rehearsal.json')
    contract_compliance_matrix = _load_json(task_dir / 'artifacts' / 'contract_compliance_matrix.json')
    executor_conformance_matrix = _load_json(task_dir / 'artifacts' / 'executor_conformance_matrix.json')
    executor_error_contract = _load_json(task_dir / 'artifacts' / 'executor_error_contract.json')
    release_rollback_parity_matrix = _load_json(task_dir / 'artifacts' / 'release_rollback_parity_matrix.json')
    implementation_blueprint = _load_json(task_dir / 'artifacts' / 'future_executor_implementation_blueprint.json')
    cutover_readiness_pack = _load_json(task_dir / 'artifacts' / 'executor_cutover_readiness_pack.json')
    real_executor_delivery_backlog = _load_json(task_dir / 'artifacts' / 'real_executor_delivery_backlog.json')
    executor_acceptance_test_pack = _load_json(task_dir / 'artifacts' / 'executor_acceptance_test_pack.json')
    executor_ownership_split = _load_json(task_dir / 'artifacts' / 'executor_ownership_split.json')
    executor_blocker_matrix = _load_json(task_dir / 'artifacts' / 'executor_blocker_matrix.json')
    integration_checklist = _load_json(task_dir / 'artifacts' / 'real_executor_integration_checklist.json')
    executor_risk_register = _load_json(task_dir / 'artifacts' / 'executor_risk_register.json')
    handoff_summary = _load_json(task_dir / 'artifacts' / 'future_executor_handoff_summary.json')
    credential_binding_policy = _load_json(task_dir / 'artifacts' / 'executor_credential_binding_policy.json')
    target_binding_registry = _load_json(task_dir / 'artifacts' / 'executor_target_binding_registry.json')
    cutover_signoff_workflow = _load_json(task_dir / 'artifacts' / 'cutover_signoff_workflow.json')
    blocker_drilldown_review = _load_json(task_dir / 'artifacts' / 'blocker_drilldown_review.json')
    human_action_pack = _load_json(task_dir / 'artifacts' / 'executor_human_action_pack.json')
    credential_binding_evidence_checklist = _load_json(task_dir / 'artifacts' / 'credential_binding_evidence_checklist.json')
    cutover_signoff_evidence_packet = _load_json(task_dir / 'artifacts' / 'cutover_signoff_evidence_packet.json')
    unresolved_blocker_tracker = _load_json(task_dir / 'artifacts' / 'unresolved_blocker_tracker.json')
    pending_human_action_board = _load_json(task_dir / 'artifacts' / 'pending_human_action_board.json')
    credential_binding_runbook = _load_json(task_dir / 'artifacts' / 'credential_binding_runbook.json')
    cutover_signoff_runbook = _load_json(task_dir / 'artifacts' / 'cutover_signoff_runbook.json')
    blocker_resolution_playbook = _load_json(task_dir / 'artifacts' / 'blocker_resolution_playbook.json')
    _assert(bool(readiness_review), 'executor_readiness_review.json should be generated')
    _assert(bool(handoff_boundary), 'real_executor_handoff_boundary.json should be generated')
    _assert(bool(release_adapter_manifest), 'release_executor_adapter_manifest.json should be generated')
    _assert(bool(rollback_adapter_manifest), 'rollback_executor_adapter_manifest.json should be generated')
    _assert(bool(capability_registry), 'executor_capability_registry.json should be generated')
    _assert(bool(invocation_policy_review), 'invocation_policy_review.json should be generated')
    _assert(bool(release_plugin_interface), 'release_executor_plugin_interface.json should be generated')
    _assert(bool(rollback_plugin_interface), 'rollback_executor_plugin_interface.json should be generated')
    _assert(bool(execution_transcript_contract), 'execution_transcript_contract.json should be generated')
    _assert(bool(executor_plugin_review), 'executor_plugin_review.json should be generated')
    _assert(bool(release_no_op_adapter), 'release_no_op_executor_adapter.json should be generated')
    _assert(bool(rollback_no_op_adapter), 'rollback_no_op_executor_adapter.json should be generated')
    _assert(release_adapter_manifest.get('adapter_type') == 'controlled_execution_adapter', 'release adapter manifest should expose adapter_type')
    _assert(rollback_adapter_manifest.get('adapter_type') == 'controlled_execution_adapter', 'rollback adapter manifest should expose shared adapter_type')
    _assert(release_adapter_manifest.get('external_side_effects') is False, 'release adapter manifest should keep external_side_effects false')
    _assert(rollback_adapter_manifest.get('external_side_effects') is False, 'rollback adapter manifest should keep external_side_effects false')
    _assert((release_adapter_manifest.get('environment_guard') or {}).get('guard_ok') is True, 'release adapter environment guard should pass')
    _assert((rollback_adapter_manifest.get('environment_guard') or {}).get('guard_ok') is True, 'rollback adapter environment guard should pass')
    _assert(capability_registry.get('registry_available') is True, 'capability registry should be available')
    _assert(sorted(capability_registry.get('top_executor_adapter_types') or []) == ['controlled_execution_adapter'], 'capability registry should expose shared adapter type')
    _assert(invocation_policy_review.get('policy_available') is True, 'invocation policy should be available')
    _assert(invocation_policy_review.get('external_side_effects') is False, 'invocation policy should keep external_side_effects false')
    _assert(release_plugin_interface.get('execution_target') == 'official_release', 'release plugin interface should target official_release')
    _assert(rollback_plugin_interface.get('execution_target') == 'rollback', 'rollback plugin interface should target rollback')
    _assert(release_plugin_interface.get('shared_transcript_contract_ref') == 'artifacts/execution_transcript_contract.json', 'release plugin should bind shared transcript contract')
    _assert(rollback_plugin_interface.get('shared_transcript_contract_ref') == 'artifacts/execution_transcript_contract.json', 'rollback plugin should bind shared transcript contract')
    _assert(execution_transcript_contract.get('transcript_available') is True, 'transcript contract should be available')
    _assert(release_no_op_adapter.get('real_execution_enabled') is False, 'release no-op adapter must keep real execution disabled')
    _assert(rollback_no_op_adapter.get('real_execution_enabled') is False, 'rollback no-op adapter must keep real execution disabled')
    _assert((release_no_op_adapter.get('mock_transcript') or {}).get('result_state') == 'mocked', 'release no-op adapter should emit mocked transcript state')
    _assert((rollback_no_op_adapter.get('mock_transcript') or {}).get('result_state') == 'mocked', 'rollback no-op adapter should emit mocked transcript state')
    _assert(executor_plugin_review.get('future_executor_scaffold_available') is True, 'plugin review should expose future scaffold availability')
    _assert(executor_plugin_review.get('executor_plugin_interface_available') is True, 'plugin review should expose plugin interface availability')
    _assert(executor_plugin_review.get('transcript_contract_available') is True, 'plugin review should expose transcript contract availability')
    _assert(executor_plugin_review.get('no_op_executor_available') is True, 'plugin review should expose no-op executor availability')
    _assert(readiness_review.get('targets', {}).get('release', {}).get('ready_for_real_executor_handoff') is True, 'release readiness should be generated and ready')
    _assert(readiness_review.get('targets', {}).get('rollback', {}).get('ready_for_real_executor_handoff') is True, 'rollback readiness should be generated and ready')
    _assert(handoff_boundary.get('handoff_boundary_ready') is True, 'handoff boundary should be ready for future executor integration')
    _assert(handoff_boundary.get('real_executor_connected') is False, 'real executor must remain disconnected')
    _assert(handoff_boundary.get('real_execution_enabled') is False, 'real execution must remain disabled')
    rollout_gate_registry = _load_json(task_dir / 'artifacts' / 'rollout_gate_registry.json')
    waiver_exception_registry = _load_json(task_dir / 'artifacts' / 'waiver_exception_registry.json')
    executor_admission_review = _load_json(task_dir / 'artifacts' / 'executor_admission_review.json')
    go_no_go_decision_pack = _load_json(task_dir / 'artifacts' / 'go_no_go_decision_pack.json')
    _assert(bool(rollout_gate_registry), 'rollout_gate_registry.json should be generated')
    _assert(bool(waiver_exception_registry), 'waiver_exception_registry.json should be generated')
    _assert(bool(executor_admission_review), 'executor_admission_review.json should be generated')
    _assert(bool(go_no_go_decision_pack), 'go_no_go_decision_pack.json should be generated')
    _assert(executor_admission_review.get('overall_admission_state') == 'ready_for_future_executor', 'admission review should expose ready_for_future_executor state for validation fixture')
    _assert(go_no_go_decision_pack.get('overall_decision') == 'go', 'go/no-go pack should expose go decision for validation fixture')
    _assert(int(rollout_gate_registry.get('rollout_gate_count', 0) or 0) > 0, 'rollout gate registry should expose rollout_gate_count')
    _assert(int(rollout_gate_registry.get('unmet_count', -1) or 0) == 0, 'rollout gate registry should expose zero unmet gates for validation fixture')
    _assert(int(waiver_exception_registry.get('waiver_exception_count', -1) or 0) == 0, 'waiver registry should expose zero active waivers for validation fixture')
    _assert(executor_admission_review.get('targets', {}).get('release', {}).get('ready_for_future_executor') is True, 'release admission review should be ready')
    _assert(executor_admission_review.get('targets', {}).get('rollback', {}).get('ready_for_future_executor') is True, 'rollback admission review should be ready')
    _assert(go_no_go_decision_pack.get('targets', {}).get('release', {}).get('decision') == 'go', 'release go/no-go should be go')
    _assert(go_no_go_decision_pack.get('targets', {}).get('rollback', {}).get('decision') == 'go', 'rollback go/no-go should be go')
    _assert(bool(request_lifecycle), 'execution_request_lifecycle.json should be generated')
    _assert(bool(acknowledgement_review), 'operator_acknowledgement_review.json should be generated')
    _assert(bool(request_registry), 'execution_request_registry.json should be generated')
    _assert(bool(simulated_executor_run), 'simulated_executor_run.json should be generated')
    _assert(bool(integration_rehearsal), 'executor_integration_rehearsal.json should be generated')
    _assert(bool(contract_compliance_matrix), 'contract_compliance_matrix.json should be generated')
    _assert(bool(executor_conformance_matrix), 'executor_conformance_matrix.json should be generated')
    _assert(bool(executor_error_contract), 'executor_error_contract.json should be generated')
    _assert(bool(release_rollback_parity_matrix), 'release_rollback_parity_matrix.json should be generated')
    _assert(bool(implementation_blueprint), 'future_executor_implementation_blueprint.json should be generated')
    _assert(bool(real_executor_delivery_backlog), 'real_executor_delivery_backlog.json should be generated')
    _assert(bool(executor_acceptance_test_pack), 'executor_acceptance_test_pack.json should be generated')
    _assert(bool(executor_ownership_split), 'executor_ownership_split.json should be generated')
    _assert(bool(executor_blocker_matrix), 'executor_blocker_matrix.json should be generated')
    _assert(bool(cutover_readiness_pack), 'executor_cutover_readiness_pack.json should be generated')
    _assert(bool(integration_checklist), 'real_executor_integration_checklist.json should be generated')
    _assert(bool(executor_risk_register), 'executor_risk_register.json should be generated')
    _assert(bool(handoff_summary), 'future_executor_handoff_summary.json should be generated')
    _assert(bool(credential_binding_policy), 'executor_credential_binding_policy.json should be generated')
    _assert(bool(target_binding_registry), 'executor_target_binding_registry.json should be generated')
    _assert(bool(cutover_signoff_workflow), 'cutover_signoff_workflow.json should be generated')
    _assert(bool(blocker_drilldown_review), 'blocker_drilldown_review.json should be generated')
    _assert(bool(human_action_pack), 'executor_human_action_pack.json should be generated')
    _assert(bool(credential_binding_evidence_checklist), 'credential_binding_evidence_checklist.json should be generated')
    _assert(bool(cutover_signoff_evidence_packet), 'cutover_signoff_evidence_packet.json should be generated')
    _assert(bool(unresolved_blocker_tracker), 'unresolved_blocker_tracker.json should be generated')
    _assert(bool(pending_human_action_board), 'pending_human_action_board.json should be generated')
    _assert(bool(credential_binding_runbook), 'credential_binding_runbook.json should be generated')
    _assert(bool(cutover_signoff_runbook), 'cutover_signoff_runbook.json should be generated')
    _assert(bool(blocker_resolution_playbook), 'blocker_resolution_playbook.json should be generated')
    _assert(int(simulated_executor_run.get('available_count', 0) or 0) >= 2, 'simulation harness should cover release and rollback')
    _assert(int(simulated_executor_run.get('pass_count', 0) or 0) >= 2, 'simulation harness should pass both targets')
    _assert(int(simulated_executor_run.get('fail_count', 0) or 0) == 0, 'simulation harness should report zero failures')
    _assert(simulated_executor_run.get('zero_real_execution_observed') is True, 'simulation harness must preserve zero real execution')
    _assert(integration_rehearsal.get('integration_rehearsal_available') is True, 'integration rehearsal availability should be true')
    _assert(contract_compliance_matrix.get('contract_compliance_available') is True, 'contract compliance availability should be true')
    _assert(executor_conformance_matrix.get('executor_conformance_available') is True, 'executor conformance availability should be true')
    _assert(executor_error_contract.get('executor_error_contract_available') is True, 'executor error contract availability should be true')
    _assert(release_rollback_parity_matrix.get('release_rollback_parity_available') is True, 'release rollback parity availability should be true')
    _assert(implementation_blueprint.get('implementation_blueprint_available') is True, 'implementation blueprint availability should be true')
    _assert(executor_conformance_matrix.get('top_missing_executor_contracts') == [], 'conformance matrix should have no missing contracts for clean fixture')
    _assert(release_rollback_parity_matrix.get('parity_gaps') == [], 'parity matrix should have no gaps for clean fixture')
    _assert(cutover_readiness_pack.get('cutover_pack_available') is True, 'cutover readiness pack availability should be true')
    _assert(integration_checklist.get('integration_checklist_available') is True, 'integration checklist availability should be true')
    _assert(executor_risk_register.get('risk_register_available') is True, 'risk register availability should be true')
    _assert(handoff_summary.get('handoff_summary_available') is True, 'handoff summary availability should be true')
    _assert(credential_binding_policy.get('credential_binding_policy_available') is True, 'credential binding policy availability should be true')
    _assert(target_binding_registry.get('target_binding_registry_available') is True, 'target binding registry availability should be true')
    _assert(cutover_signoff_workflow.get('cutover_signoff_available') is True, 'cutover signoff workflow availability should be true')
    _assert(blocker_drilldown_review.get('blocker_drilldown_available') is True, 'blocker drilldown review availability should be true')
    _assert(human_action_pack.get('human_action_pack_available') is True, 'human action pack availability should be true')
    _assert(credential_binding_evidence_checklist.get('credential_binding_evidence_checklist_available') is True, 'binding evidence checklist availability should be true')
    _assert(cutover_signoff_evidence_packet.get('cutover_signoff_evidence_packet_available') is True, 'signoff evidence packet availability should be true')
    _assert(unresolved_blocker_tracker.get('unresolved_blocker_tracker_available') is True, 'unresolved blocker tracker availability should be true')
    _assert(pending_human_action_board.get('pending_human_action_board_available') is True, 'pending human action board availability should be true')
    _assert(credential_binding_runbook.get('credential_binding_runbook_available') is True, 'credential binding runbook availability should be true')
    _assert(cutover_signoff_runbook.get('signoff_runbook_available') is True, 'signoff runbook availability should be true')
    _assert(blocker_resolution_playbook.get('blocker_resolution_playbook_available') is True, 'blocker resolution playbook availability should be true')
    _assert(bool(human_action_pack.get('top_human_actions')), 'human action pack should expose top_human_actions')
    _assert(bool(human_action_pack.get('top_unresolved_human_blockers')), 'human action pack should expose top_unresolved_human_blockers')
    _assert(int(credential_binding_evidence_checklist.get('binding_evidence_gap_count', 0) or 0) > 0, 'binding evidence checklist should expose binding_evidence_gap_count')
    _assert(int(cutover_signoff_evidence_packet.get('pending_signoff_role_count', 0) or 0) > 0, 'signoff evidence packet should expose pending_signoff_role_count')
    _assert(int(unresolved_blocker_tracker.get('unresolved_blocker_owner_count', 0) or 0) > 0, 'unresolved blocker tracker should expose owner count')
    _assert(bool(pending_human_action_board.get('top_pending_human_actions')), 'pending human action board should expose top_pending_human_actions')
    _assert('executor_human_action_pack' in (cutover_signoff_runbook.get('refs') or {}), 'signoff runbook should link human action pack')
    _assert('blocker_drilldown_review' in (credential_binding_runbook.get('refs') or {}), 'credential binding runbook should link blocker drilldown')
    _assert('cutover_signoff_runbook' in (blocker_resolution_playbook.get('refs') or {}), 'blocker resolution playbook should link signoff runbook')
    _assert('real_executor_delivery_backlog' in (credential_binding_policy.get('refs') or {}), 'credential binding policy should link delivery backlog')
    _assert('executor_acceptance_test_pack' in (cutover_signoff_workflow.get('refs') or {}), 'cutover signoff workflow should link acceptance pack')
    _assert('executor_risk_register' in (blocker_drilldown_review.get('refs') or {}), 'blocker drilldown should link risk register')
    _assert(sorted(cutover_readiness_pack.get('top_remaining_blockers') or []) == ['credential_target_binding_unresolved', 'cutover_signoff_pending', 'real_release_executor_missing', 'real_rollback_executor_missing'], 'cutover readiness pack should expose remaining blockers')
    _assert(sorted(integration_checklist.get('top_remaining_blockers') or []) == ['credential_target_binding_unresolved', 'cutover_signoff_pending', 'real_release_executor_missing', 'real_rollback_executor_missing'], 'integration checklist should expose remaining blockers')
    _assert(bool(executor_risk_register.get('top_executor_risks')), 'risk register should expose top_executor_risks')
    _assert(handoff_summary.get('handoff_state') == 'ready_for_future_implementer_pickup', 'handoff summary should expose pickup-ready state')
    _assert(bool(dispatch_review), 'execution_request_dispatch_review.json should be generated')
    _assert(bool(escalation_review), 'execution_request_escalation_review.json should be generated')
    _assert(bool(retry_summary), 'execution_request_retry_summary.json should be generated')
    _assert((task_dir / 'artifacts' / 'execution_request_history_ledger.jsonl').exists(), 'execution_request_history_ledger.jsonl should be generated')
    release_request = ((request_lifecycle.get('requests') or {}).get('release') or {})
    rollback_request = ((request_lifecycle.get('requests') or {}).get('rollback') or {})
    _assert(release_request.get('request_state') == 'expired', 'release request should reach expired governance state')
    _assert(rollback_request.get('request_state') == 'expired', 'rollback request should reach expired governance state')
    _assert(release_request.get('reassignment_count', 0) >= 1, 'release request should record reassignment count')
    _assert(rollback_request.get('reassignment_count', 0) >= 1, 'rollback request should record reassignment count')
    _assert(release_request.get('escalation_count', 0) >= 1, 'release request should record escalation count')
    _assert(rollback_request.get('escalation_count', 0) >= 1, 'rollback request should record escalation count')
    _assert(release_request.get('retry_ready') is True, 'release request should be marked retry-ready')
    _assert(rollback_request.get('retry_ready') is True, 'rollback request should be marked retry-ready')
    _assert(int((acknowledgement_review or {}).get('execution_request_requested_count') or 0) == 0, 'requested count should be zero after expiry governance')
    _assert(int((acknowledgement_review or {}).get('execution_request_acknowledged_count') or 0) == 0, 'acknowledged count should be zero after expiry governance')
    _assert(int((acknowledgement_review or {}).get('execution_request_expired_count') or 0) >= 2, 'expired count should be visible in acknowledgement review')
    _assert(int((acknowledgement_review or {}).get('request_open_count') or 0) == 0, 'open count should be zero after expiry governance')
    _assert(int((acknowledgement_review or {}).get('request_inflight_count') or 0) == 0, 'inflight count should be zero after expiry governance')
    _assert(int((acknowledgement_review or {}).get('execution_request_reassigned_count') or 0) >= 2, 'reassigned count should be visible in acknowledgement review')
    _assert(int((acknowledgement_review or {}).get('execution_request_escalated_count') or 0) >= 2, 'escalated count should be visible in acknowledgement review')
    _assert(int((acknowledgement_review or {}).get('execution_request_retry_ready_count') or 0) >= 2, 'retry-ready count should be visible in acknowledgement review')

    release_receipt = _load_json(task_dir / 'artifacts' / 'official_release_execution_receipt.json')
    rollback_receipt = _load_json(task_dir / 'artifacts' / 'rollback_execution_receipt.json')
    _assert(release_request.get('batch_id') == release_receipt.get('batch_id'), 'release request traceability should keep batch_id aligned')
    _assert(rollback_request.get('batch_id') == rollback_receipt.get('batch_id'), 'rollback request traceability should keep batch_id aligned')
    _assert(release_request.get('run_id') == release_receipt.get('run_id'), 'release request traceability should keep run_id aligned')
    _assert(rollback_request.get('run_id') == rollback_receipt.get('run_id'), 'rollback request traceability should keep run_id aligned')
    for receipt, expected_proposal, expected_approval in [
        (release_receipt, 'proposal://validation/release', 'approval://validation/release'),
        (rollback_receipt, 'proposal://validation/rollback', 'approval://validation/rollback'),
    ]:
        trace = receipt.get('receipt_trace', {})
        _assert(trace.get('proposal_ref') == expected_proposal, 'receipt should trace proposal_ref')
        _assert(trace.get('approval_ref') == expected_approval, 'receipt should trace approval_ref')
        _assert(trace.get('batch_id') == receipt.get('batch_id'), 'receipt should trace batch_id')
        _assert(trace.get('run_id') == receipt.get('run_id'), 'receipt should trace run_id')
        _assert(bool(trace.get('command_receipt_id')), 'receipt should include command_receipt_id')
        _assert(bool(trace.get('command_digest_sha256')), 'receipt should include command digest')

    run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validator', backfill_missing=True)
    latest_cycle = _load_json(STATE_ROOT / 'latest_cycle.json')
    latest_stage_card = _load_json(STATE_ROOT / 'latest_stage_card.json')

    _assert(latest_cycle.get('executor_contract_available_count', 0) >= 1, 'latest_cycle should aggregate executor contract availability')
    _assert(int(latest_cycle.get('executor_adapter_available_count', 0) or 0) >= 2, 'latest_cycle should expose adapter manifest count')
    _assert(latest_cycle.get('executor_capability_registry_available') is True, 'latest_cycle should expose capability registry availability')
    _assert(latest_cycle.get('invocation_policy_available') is True, 'latest_cycle should expose invocation policy availability')
    _assert(latest_cycle.get('future_executor_scaffold_available') is True, 'latest_cycle should expose future_executor_scaffold_available')
    _assert(latest_cycle.get('executor_plugin_interface_available') is True, 'latest_cycle should expose executor_plugin_interface_available')
    _assert(latest_cycle.get('transcript_contract_available') is True, 'latest_cycle should expose transcript_contract_available')
    _assert(latest_cycle.get('no_op_executor_available') is True, 'latest_cycle should expose no_op_executor_available')
    _assert(latest_cycle.get('executor_conformance_available') is True, 'latest_cycle should expose executor_conformance_available')
    _assert(latest_cycle.get('executor_error_contract_available') is True, 'latest_cycle should expose executor_error_contract_available')
    _assert(latest_cycle.get('release_rollback_parity_available') is True, 'latest_cycle should expose release_rollback_parity_available')
    _assert(latest_cycle.get('implementation_blueprint_available') is True, 'latest_cycle should expose implementation_blueprint_available')
    _assert(latest_cycle.get('executor_delivery_pack_available') is True, 'latest_cycle should expose executor_delivery_pack_available')
    _assert(latest_cycle.get('executor_acceptance_pack_available') is True, 'latest_cycle should expose executor_acceptance_pack_available')
    _assert(latest_cycle.get('ownership_split_available') is True, 'latest_cycle should expose ownership_split_available')
    _assert(int(latest_cycle.get('executor_delivery_item_count', 0) or 0) >= 10, 'latest_cycle should expose executor_delivery_item_count')
    _assert(int(latest_cycle.get('executor_blocker_count', 0) or 0) >= 6, 'latest_cycle should expose executor_blocker_count')
    _assert(latest_cycle.get('cutover_pack_available') is True, 'latest_cycle should expose cutover_pack_available')
    _assert(latest_cycle.get('integration_checklist_available') is True, 'latest_cycle should expose integration_checklist_available')
    _assert(latest_cycle.get('risk_register_available') is True, 'latest_cycle should expose risk_register_available')
    _assert(latest_cycle.get('handoff_summary_available') is True, 'latest_cycle should expose handoff_summary_available')
    _assert(latest_cycle.get('credential_binding_policy_available') is True, 'latest_cycle should expose credential_binding_policy_available')
    _assert(latest_cycle.get('target_binding_registry_available') is True, 'latest_cycle should expose target_binding_registry_available')
    _assert(latest_cycle.get('cutover_signoff_available') is True, 'latest_cycle should expose cutover_signoff_available')
    _assert(latest_cycle.get('blocker_drilldown_available') is True, 'latest_cycle should expose blocker_drilldown_available')
    _assert(latest_cycle.get('human_action_pack_available') is True, 'latest_cycle should expose human_action_pack_available')
    _assert(latest_cycle.get('credential_binding_evidence_checklist_available') is True, 'latest_cycle should expose credential_binding_evidence_checklist_available')
    _assert(latest_cycle.get('signoff_evidence_packet_available') is True, 'latest_cycle should expose signoff_evidence_packet_available')
    _assert(latest_cycle.get('unresolved_blocker_tracker_available') is True, 'latest_cycle should expose unresolved_blocker_tracker_available')
    _assert(latest_cycle.get('pending_human_action_board_available') is True, 'latest_cycle should expose pending_human_action_board_available')
    _assert(latest_cycle.get('credential_binding_runbook_available') is True, 'latest_cycle should expose credential_binding_runbook_available')
    _assert(latest_cycle.get('signoff_runbook_available') is True, 'latest_cycle should expose signoff_runbook_available')
    _assert(latest_cycle.get('blocker_resolution_playbook_available') is True, 'latest_cycle should expose blocker_resolution_playbook_available')
    _assert(int(latest_cycle.get('unresolved_credential_binding_count') or 0) > 0, 'latest_cycle should expose unresolved_credential_binding_count')
    _assert(int(latest_cycle.get('unresolved_signoff_count') or 0) > 0, 'latest_cycle should expose unresolved_signoff_count')
    _assert(int(latest_cycle.get('unresolved_blocker_owner_count') or 0) > 0, 'latest_cycle should expose unresolved_blocker_owner_count')
    _assert(int(latest_cycle.get('pending_signoff_role_count') or 0) > 0, 'latest_cycle should expose pending_signoff_role_count')
    _assert(int(latest_cycle.get('binding_evidence_gap_count') or 0) > 0, 'latest_cycle should expose binding_evidence_gap_count')
    _assert(bool(latest_cycle.get('top_blocker_categories')), 'latest_cycle should expose top_blocker_categories')
    _assert(bool(latest_cycle.get('top_human_actions')), 'latest_cycle should expose top_human_actions')
    _assert(bool(latest_cycle.get('top_pending_human_actions')), 'latest_cycle should expose top_pending_human_actions')
    _assert(bool(latest_cycle.get('top_unresolved_human_blockers')), 'latest_cycle should expose top_unresolved_human_blockers')
    _assert(latest_cycle.get('top_missing_executor_contracts') == [], 'latest_cycle should expose empty top_missing_executor_contracts for clean fixture')
    _assert(latest_cycle.get('parity_gaps') == [], 'latest_cycle should expose empty parity_gaps for clean fixture')
    _assert(sorted(latest_cycle.get('top_remaining_blockers') or []) == ['credential_target_binding_unresolved', 'cutover_signoff_pending', 'real_release_executor_missing', 'real_rollback_executor_missing'], 'latest_cycle should expose top_remaining_blockers')
    _assert(bool(latest_cycle.get('top_executor_risks')), 'latest_cycle should expose top_executor_risks')
    _assert(bool(latest_cycle.get('top_executor_blockers')), 'latest_cycle should expose top_executor_blockers')
    _assert(int(latest_cycle.get('environment_guard_ok_count', 0) or 0) >= 2, 'latest_cycle should expose environment_guard_ok_count')
    _assert(int(latest_cycle.get('environment_guard_unmet_count', -1) or 0) == 0, 'latest_cycle should expose zero unmet environment guards')
    _assert(latest_cycle.get('top_executor_adapter_types') == ['controlled_execution_adapter'], 'latest_cycle should expose shared top executor adapter type')
    _assert(sorted(latest_cycle.get('top_executor_plugin_targets') or []) == ['release', 'rollback'], 'latest_cycle should expose top_executor_plugin_targets')
    _assert(latest_cycle.get('dry_run_available_count', 0) >= 1, 'latest_cycle should aggregate dry-run availability')
    _assert(latest_cycle.get('execution_receipt_protocol_available_count', 0) >= 1, 'latest_cycle should aggregate receipt protocol availability')
    _assert(latest_cycle.get('handoff_packet_available_count', 0) >= 1, 'latest_cycle should aggregate handoff packet availability')
    _assert(latest_cycle.get('operator_execution_request_available_count', 0) >= 1, 'latest_cycle should aggregate operator execution request availability')
    _assert(latest_cycle.get('receipt_correlation_ready_count', 0) >= 1, 'latest_cycle should aggregate receipt correlation readiness')
    _assert(latest_cycle.get('executor_readiness_review_available_count', 0) >= 1, 'latest_cycle should aggregate readiness review availability')
    _assert(latest_cycle.get('handoff_boundary_ready_count', 0) >= 1, 'latest_cycle should aggregate handoff boundary readiness')
    _assert(int(latest_cycle.get('executor_readiness_gate_count', 0) or 0) > 0, 'latest_cycle should expose executor_readiness_gate_count')
    _assert(int(latest_cycle.get('executor_unmet_gate_count', -1)) == 0, 'latest_cycle should expose executor_unmet_gate_count')
    _assert(int(latest_cycle.get('executor_simulation_available_count', 0) or 0) >= 2, 'latest_cycle should expose executor_simulation_available_count')
    _assert(int(latest_cycle.get('executor_simulation_pass_count', 0) or 0) >= 2, 'latest_cycle should expose executor_simulation_pass_count')
    _assert(int(latest_cycle.get('executor_simulation_fail_count', -1) or 0) == 0, 'latest_cycle should expose executor_simulation_fail_count')
    _assert(latest_cycle.get('contract_compliance_available') is True, 'latest_cycle should expose contract_compliance_available')
    _assert(latest_cycle.get('integration_rehearsal_available') is True, 'latest_cycle should expose integration_rehearsal_available')
    _assert(latest_cycle.get('top_executor_contract_gaps') == [], 'latest_cycle should expose empty top_executor_contract_gaps for clean fixture')
    _assert(latest_cycle.get('executor_readiness_state') == 'handoff_boundary_ready', 'latest_cycle should expose handoff boundary readiness state')
    _assert(int(latest_cycle.get('execution_request_requested_count') or 0) == 0, 'latest_cycle should expose zero requested count after expiry governance')
    _assert(int(latest_cycle.get('execution_request_expired_count') or 0) >= 2, 'latest_cycle should expose expired request count')
    _assert(int(latest_cycle.get('request_open_count') or 0) == 0, 'latest_cycle should expose request_open_count')
    _assert(int(latest_cycle.get('request_inflight_count') or 0) == 0, 'latest_cycle should expose request_inflight_count')
    _assert(int(latest_cycle.get('execution_request_reassigned_count') or 0) >= 2, 'latest_cycle should expose reassigned request count')
    _assert(int(latest_cycle.get('execution_request_escalated_count') or 0) >= 2, 'latest_cycle should expose escalated request count')
    _assert(int(latest_cycle.get('execution_request_retry_ready_count') or 0) >= 2, 'latest_cycle should expose retry-ready request count')
    _assert(bool(latest_cycle.get('top_request_states')), 'latest_cycle should expose top_request_states')
    _assert(bool(latest_cycle.get('recent_request_actions')), 'latest_cycle should expose recent_request_actions')
    _assert(bool(latest_cycle.get('recent_request_transitions')), 'latest_cycle should expose recent_request_transitions')
    _assert(bool(latest_cycle.get('recent_request_escalations')), 'latest_cycle should expose recent_request_escalations')
    _assert(bool(latest_cycle.get('top_pending_requests')), 'latest_cycle should expose top_pending_requests')
    _assert(bool(latest_cycle.get('top_request_owners')), 'latest_cycle should expose top_request_owners')
    signals = latest_stage_card.get('signals', {})
    _assert(signals.get('executor_contract_available_count', 0) >= 1, 'stage card should expose executor contract count')
    _assert(int(signals.get('executor_adapter_available_count', 0) or 0) >= 2, 'stage card should expose executor adapter count')
    _assert(signals.get('executor_capability_registry_available') is True, 'stage card should expose capability registry availability')
    _assert(signals.get('invocation_policy_available') is True, 'stage card should expose invocation policy availability')
    _assert(signals.get('future_executor_scaffold_available') is True, 'stage card should expose future_executor_scaffold_available')
    _assert(signals.get('executor_plugin_interface_available') is True, 'stage card should expose executor_plugin_interface_available')
    _assert(signals.get('transcript_contract_available') is True, 'stage card should expose transcript_contract_available')
    _assert(signals.get('no_op_executor_available') is True, 'stage card should expose no_op_executor_available')
    _assert(signals.get('executor_conformance_available') is True, 'stage card should expose executor_conformance_available')
    _assert(signals.get('executor_error_contract_available') is True, 'stage card should expose executor_error_contract_available')
    _assert(signals.get('release_rollback_parity_available') is True, 'stage card should expose release_rollback_parity_available')
    _assert(signals.get('implementation_blueprint_available') is True, 'stage card should expose implementation_blueprint_available')
    _assert(signals.get('executor_delivery_pack_available') is True, 'stage card should expose executor_delivery_pack_available')
    _assert(signals.get('executor_acceptance_pack_available') is True, 'stage card should expose executor_acceptance_pack_available')
    _assert(signals.get('ownership_split_available') is True, 'stage card should expose ownership_split_available')
    _assert(int(signals.get('executor_delivery_item_count', 0) or 0) >= 10, 'stage card should expose executor_delivery_item_count')
    _assert(int(signals.get('executor_blocker_count', 0) or 0) >= 6, 'stage card should expose executor_blocker_count')
    _assert(signals.get('cutover_pack_available') is True, 'stage card should expose cutover_pack_available')
    _assert(signals.get('integration_checklist_available') is True, 'stage card should expose integration_checklist_available')
    _assert(signals.get('risk_register_available') is True, 'stage card should expose risk_register_available')
    _assert(signals.get('handoff_summary_available') is True, 'stage card should expose handoff_summary_available')
    _assert(signals.get('credential_binding_policy_available') is True, 'stage card should expose credential_binding_policy_available')
    _assert(signals.get('target_binding_registry_available') is True, 'stage card should expose target_binding_registry_available')
    _assert(signals.get('cutover_signoff_available') is True, 'stage card should expose cutover_signoff_available')
    _assert(signals.get('blocker_drilldown_available') is True, 'stage card should expose blocker_drilldown_available')
    _assert(signals.get('human_action_pack_available') is True, 'stage card should expose human_action_pack_available')
    _assert(signals.get('credential_binding_evidence_checklist_available') is True, 'stage card should expose credential_binding_evidence_checklist_available')
    _assert(signals.get('signoff_evidence_packet_available') is True, 'stage card should expose signoff_evidence_packet_available')
    _assert(signals.get('unresolved_blocker_tracker_available') is True, 'stage card should expose unresolved_blocker_tracker_available')
    _assert(signals.get('pending_human_action_board_available') is True, 'stage card should expose pending_human_action_board_available')
    _assert(signals.get('credential_binding_runbook_available') is True, 'stage card should expose credential_binding_runbook_available')
    _assert(signals.get('signoff_runbook_available') is True, 'stage card should expose signoff_runbook_available')
    _assert(signals.get('blocker_resolution_playbook_available') is True, 'stage card should expose blocker_resolution_playbook_available')
    _assert(int(signals.get('unresolved_credential_binding_count') or 0) > 0, 'stage card should expose unresolved_credential_binding_count')
    _assert(int(signals.get('unresolved_signoff_count') or 0) > 0, 'stage card should expose unresolved_signoff_count')
    _assert(int(signals.get('unresolved_blocker_owner_count') or 0) > 0, 'stage card should expose unresolved_blocker_owner_count')
    _assert(int(signals.get('pending_signoff_role_count') or 0) > 0, 'stage card should expose pending_signoff_role_count')
    _assert(int(signals.get('binding_evidence_gap_count') or 0) > 0, 'stage card should expose binding_evidence_gap_count')
    _assert(bool(signals.get('top_blocker_categories')), 'stage card should expose top_blocker_categories')
    _assert(bool(signals.get('top_human_actions')), 'stage card should expose top_human_actions')
    _assert(bool(signals.get('top_pending_human_actions')), 'stage card should expose top_pending_human_actions')
    _assert(bool(signals.get('top_unresolved_human_blockers')), 'stage card should expose top_unresolved_human_blockers')
    _assert(signals.get('top_missing_executor_contracts') == [], 'stage card should expose empty top_missing_executor_contracts')
    _assert(signals.get('parity_gaps') == [], 'stage card should expose empty parity_gaps')
    _assert(sorted(signals.get('top_remaining_blockers') or []) == ['credential_target_binding_unresolved', 'cutover_signoff_pending', 'real_release_executor_missing', 'real_rollback_executor_missing'], 'stage card should expose top_remaining_blockers')
    _assert(bool(signals.get('top_executor_risks')), 'stage card should expose top_executor_risks')
    _assert(bool(signals.get('top_executor_blockers')), 'stage card should expose top_executor_blockers')
    _assert(int(signals.get('environment_guard_ok_count', 0) or 0) >= 2, 'stage card should expose environment_guard_ok_count')
    _assert(int(signals.get('environment_guard_unmet_count', -1) or 0) == 0, 'stage card should expose zero unmet environment guards')
    _assert(signals.get('top_executor_adapter_types') == ['controlled_execution_adapter'], 'stage card should expose top executor adapter types')
    _assert(sorted(signals.get('top_executor_plugin_targets') or []) == ['release', 'rollback'], 'stage card should expose top_executor_plugin_targets')
    _assert(signals.get('dry_run_available_count', 0) >= 1, 'stage card should expose dry-run count')
    _assert(signals.get('execution_receipt_protocol_available_count', 0) >= 1, 'stage card should expose receipt protocol count')
    _assert(signals.get('handoff_packet_available_count', 0) >= 1, 'stage card should expose handoff packet count')
    _assert(signals.get('operator_execution_request_available_count', 0) >= 1, 'stage card should expose operator execution request count')
    _assert(signals.get('receipt_correlation_ready_count', 0) >= 1, 'stage card should expose receipt correlation readiness count')
    _assert(signals.get('executor_readiness_review_available_count', 0) >= 1, 'stage card should expose readiness review availability')
    _assert(signals.get('handoff_boundary_ready_count', 0) >= 1, 'stage card should expose handoff boundary readiness count')
    _assert(int(signals.get('executor_readiness_gate_count', 0) or 0) > 0, 'stage card should expose executor_readiness_gate_count')
    _assert(int(signals.get('executor_unmet_gate_count', -1)) == 0, 'stage card should expose executor_unmet_gate_count')
    _assert(int(signals.get('executor_simulation_available_count', 0) or 0) >= 2, 'stage card should expose executor_simulation_available_count')
    _assert(int(signals.get('executor_simulation_pass_count', 0) or 0) >= 2, 'stage card should expose executor_simulation_pass_count')
    _assert(int(signals.get('executor_simulation_fail_count', -1) or 0) == 0, 'stage card should expose executor_simulation_fail_count')
    _assert(signals.get('contract_compliance_available') is True, 'stage card should expose contract_compliance_available')
    _assert(signals.get('integration_rehearsal_available') is True, 'stage card should expose integration_rehearsal_available')
    _assert(signals.get('top_executor_contract_gaps') == [], 'stage card should expose top_executor_contract_gaps')
    _assert(signals.get('top_unmet_executor_gates') == [], 'stage card should expose top_unmet_executor_gates')
    _assert('release' in (signals.get('top_execution_handoff_targets') or []), 'stage card should expose release handoff target')
    _assert('rollback' in (signals.get('top_execution_handoff_targets') or []), 'stage card should expose rollback handoff target')
    _assert(bool(signals.get('top_command_plan_steps')), 'stage card should expose top_command_plan_steps')
    _assert(int(signals.get('execution_request_requested_count') or 0) == 0, 'stage card should expose zero requested count after expiry governance')
    _assert(int(signals.get('execution_request_expired_count') or 0) >= 2, 'stage card should expose expired request count')
    _assert(int(signals.get('request_open_count') or 0) == 0, 'stage card should expose request_open_count')
    _assert(int(signals.get('request_inflight_count') or 0) == 0, 'stage card should expose request_inflight_count')
    _assert(int(signals.get('execution_request_reassigned_count') or 0) >= 2, 'stage card should expose reassigned request count')
    _assert(int(signals.get('execution_request_escalated_count') or 0) >= 2, 'stage card should expose escalated request count')
    _assert(int(signals.get('execution_request_retry_ready_count') or 0) >= 2, 'stage card should expose retry-ready request count')
    _assert(bool(signals.get('top_request_states')), 'stage card should expose top_request_states')
    _assert(bool(signals.get('recent_request_actions')), 'stage card should expose recent_request_actions')
    _assert(bool(signals.get('recent_request_transitions')), 'stage card should expose recent_request_transitions')
    _assert(bool(signals.get('recent_request_escalations')), 'stage card should expose recent_request_escalations')
    _assert(bool(signals.get('top_pending_requests')), 'stage card should expose top_pending_requests')
    _assert(bool(signals.get('top_request_owners')), 'stage card should expose top_request_owners')

    payload = {
        'task_id': TASK_ID,
        'release': {
            'command_receipt_id': release_result.get('command_receipt_id'),
            'states': release_result.get('states'),
            'readiness': readiness_review.get('targets', {}).get('release'),
        },
        'rollback': {
            'command_receipt_id': rollback_result.get('command_receipt_id'),
            'states': rollback_result.get('states'),
            'readiness': readiness_review.get('targets', {}).get('rollback'),
        },
        'snapshot': {
            'executor_contract_available': snapshot.get('executor_contract_available'),
            'executor_adapter_available_count': snapshot.get('executor_adapter_available_count'),
            'executor_capability_registry_available': snapshot.get('executor_capability_registry_available'),
            'invocation_policy_available': snapshot.get('invocation_policy_available'),
            'future_executor_scaffold_available': snapshot.get('future_executor_scaffold_available'),
            'executor_plugin_interface_available': snapshot.get('executor_plugin_interface_available'),
            'transcript_contract_available': snapshot.get('transcript_contract_available'),
            'no_op_executor_available': snapshot.get('no_op_executor_available'),
            'environment_guard_ok_count': snapshot.get('environment_guard_ok_count'),
            'environment_guard_unmet_count': snapshot.get('environment_guard_unmet_count'),
            'top_executor_adapter_types': snapshot.get('top_executor_adapter_types'),
            'top_executor_plugin_targets': snapshot.get('top_executor_plugin_targets'),
            'dry_run_available': snapshot.get('dry_run_available'),
            'execution_receipt_protocol_available': snapshot.get('execution_receipt_protocol_available'),
            'handoff_packet_available': snapshot.get('handoff_packet_available'),
            'operator_execution_request_available': snapshot.get('operator_execution_request_available'),
            'receipt_correlation_ready': snapshot.get('receipt_correlation_ready'),
            'execution_request_requested_count': snapshot.get('execution_request_requested_count'),
            'execution_request_acknowledged_count': snapshot.get('execution_request_acknowledged_count'),
            'execution_request_accepted_count': snapshot.get('execution_request_accepted_count'),
            'execution_request_declined_count': snapshot.get('execution_request_declined_count'),
            'top_request_states': snapshot.get('top_request_states'),
            'recent_request_actions': snapshot.get('recent_request_actions'),
            'executor_readiness_state': snapshot.get('executor_readiness_state'),
            'executor_readiness_gate_count': snapshot.get('executor_readiness_gate_count'),
            'executor_unmet_gate_count': snapshot.get('executor_unmet_gate_count'),
            'top_unmet_executor_gates': snapshot.get('top_unmet_executor_gates'),
            'handoff_boundary_ready': snapshot.get('handoff_boundary_ready'),
        },
        'latest_cycle': {
            'executor_contract_available_count': latest_cycle.get('executor_contract_available_count'),
            'executor_adapter_available_count': latest_cycle.get('executor_adapter_available_count'),
            'executor_capability_registry_available': latest_cycle.get('executor_capability_registry_available'),
            'invocation_policy_available': latest_cycle.get('invocation_policy_available'),
            'future_executor_scaffold_available': latest_cycle.get('future_executor_scaffold_available'),
            'executor_plugin_interface_available': latest_cycle.get('executor_plugin_interface_available'),
            'transcript_contract_available': latest_cycle.get('transcript_contract_available'),
            'no_op_executor_available': latest_cycle.get('no_op_executor_available'),
            'environment_guard_ok_count': latest_cycle.get('environment_guard_ok_count'),
            'environment_guard_unmet_count': latest_cycle.get('environment_guard_unmet_count'),
            'top_executor_adapter_types': latest_cycle.get('top_executor_adapter_types'),
            'top_executor_plugin_targets': latest_cycle.get('top_executor_plugin_targets'),
            'dry_run_available_count': latest_cycle.get('dry_run_available_count'),
            'execution_receipt_protocol_available_count': latest_cycle.get('execution_receipt_protocol_available_count'),
            'handoff_packet_available_count': latest_cycle.get('handoff_packet_available_count'),
            'operator_execution_request_available_count': latest_cycle.get('operator_execution_request_available_count'),
            'receipt_correlation_ready_count': latest_cycle.get('receipt_correlation_ready_count'),
            'executor_readiness_review_available_count': latest_cycle.get('executor_readiness_review_available_count'),
            'handoff_boundary_ready_count': latest_cycle.get('handoff_boundary_ready_count'),
            'executor_readiness_state': latest_cycle.get('executor_readiness_state'),
            'executor_readiness_gate_count': latest_cycle.get('executor_readiness_gate_count'),
            'executor_unmet_gate_count': latest_cycle.get('executor_unmet_gate_count'),
            'executor_simulation_available_count': latest_cycle.get('executor_simulation_available_count'),
            'executor_simulation_pass_count': latest_cycle.get('executor_simulation_pass_count'),
            'executor_simulation_fail_count': latest_cycle.get('executor_simulation_fail_count'),
            'contract_compliance_available': latest_cycle.get('contract_compliance_available'),
            'integration_rehearsal_available': latest_cycle.get('integration_rehearsal_available'),
            'top_executor_contract_gaps': latest_cycle.get('top_executor_contract_gaps'),
            'top_unmet_executor_gates': latest_cycle.get('top_unmet_executor_gates'),
            'top_execution_handoff_targets': latest_cycle.get('top_execution_handoff_targets'),
            'top_command_plan_steps': latest_cycle.get('top_command_plan_steps'),
            'execution_request_requested_count': latest_cycle.get('execution_request_requested_count'),
            'execution_request_acknowledged_count': latest_cycle.get('execution_request_acknowledged_count'),
            'execution_request_accepted_count': latest_cycle.get('execution_request_accepted_count'),
            'execution_request_declined_count': latest_cycle.get('execution_request_declined_count'),
            'top_request_states': latest_cycle.get('top_request_states'),
            'recent_request_actions': latest_cycle.get('recent_request_actions'),
        },
        'stage_card_signals': {
            'executor_adapter_available_count': signals.get('executor_adapter_available_count'),
            'executor_capability_registry_available': signals.get('executor_capability_registry_available'),
            'invocation_policy_available': signals.get('invocation_policy_available'),
            'future_executor_scaffold_available': signals.get('future_executor_scaffold_available'),
            'executor_plugin_interface_available': signals.get('executor_plugin_interface_available'),
            'transcript_contract_available': signals.get('transcript_contract_available'),
            'no_op_executor_available': signals.get('no_op_executor_available'),
            'environment_guard_ok_count': signals.get('environment_guard_ok_count'),
            'environment_guard_unmet_count': signals.get('environment_guard_unmet_count'),
            'top_executor_adapter_types': signals.get('top_executor_adapter_types'),
            'top_executor_plugin_targets': signals.get('top_executor_plugin_targets'),
            'executor_readiness_gate_count': signals.get('executor_readiness_gate_count'),
            'executor_unmet_gate_count': signals.get('executor_unmet_gate_count'),
            'executor_simulation_available_count': signals.get('executor_simulation_available_count'),
            'executor_simulation_pass_count': signals.get('executor_simulation_pass_count'),
            'executor_simulation_fail_count': signals.get('executor_simulation_fail_count'),
            'contract_compliance_available': signals.get('contract_compliance_available'),
            'integration_rehearsal_available': signals.get('integration_rehearsal_available'),
            'top_executor_contract_gaps': signals.get('top_executor_contract_gaps'),
            'top_unmet_executor_gates': signals.get('top_unmet_executor_gates'),
            'top_execution_handoff_targets': signals.get('top_execution_handoff_targets'),
            'top_command_plan_steps': signals.get('top_command_plan_steps'),
            'execution_request_requested_count': signals.get('execution_request_requested_count'),
            'execution_request_acknowledged_count': signals.get('execution_request_acknowledged_count'),
            'execution_request_accepted_count': signals.get('execution_request_accepted_count'),
            'execution_request_declined_count': signals.get('execution_request_declined_count'),
            'top_request_states': signals.get('top_request_states'),
            'recent_request_actions': signals.get('recent_request_actions'),
            'handoff_boundary_ready_count': signals.get('handoff_boundary_ready_count'),
        },
        'request_lifecycle': {
            'summary': request_lifecycle.get('summary'),
            'release': (request_lifecycle.get('requests') or {}).get('release'),
            'rollback': (request_lifecycle.get('requests') or {}).get('rollback'),
        },
        'acknowledgement_review': acknowledgement_review,
        'adapter_layer': {
            'release_manifest_ref': release_adapter_manifest.get('contract_reference'),
            'rollback_manifest_ref': rollback_adapter_manifest.get('contract_reference'),
            'capability_registry_available': capability_registry.get('registry_available'),
            'invocation_policy_available': invocation_policy_review.get('policy_available'),
            'shared_adapter_types': capability_registry.get('top_executor_adapter_types'),
        },
        'handoff_boundary': {
            'handoff_boundary_ready': handoff_boundary.get('handoff_boundary_ready'),
            'future_real_executor_connection_allowed': handoff_boundary.get('future_real_executor_connection_allowed'),
            'real_executor_connected': handoff_boundary.get('real_executor_connected'),
            'real_execution_enabled': handoff_boundary.get('real_execution_enabled'),
            'next_allowed_step': handoff_boundary.get('next_allowed_step'),
        },
        'real_execution_attempted': False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
