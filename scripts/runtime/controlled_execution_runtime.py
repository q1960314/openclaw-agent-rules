#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from artifact_manager import ArtifactManager
from execution_binding_runtime import ensure_execution_batch, get_execution_run_context
from release_closure_runtime import _load_json, load_release_closure_snapshot

ROOT = Path('/home/admin/.openclaw/workspace/master')
JOBS_ROOT = ROOT / 'traces' / 'jobs'
PROTOCOLS = ROOT / 'protocols'

TARGETS = {
    'release': {
        'label': 'official_release',
        'contract_artifact': 'release_executor_contract.json',
        'request_artifact': 'official_release_execution_request.json',
        'dry_run_artifact': 'official_release_execution_dry_run_result.json',
        'receipt_artifact': 'official_release_execution_receipt.json',
        'review_artifact': 'release_executor_contract_review.md',
        'handoff_artifact': 'release_executor_handoff_packet.json',
        'handoff_review_json': 'release_executor_handoff_packet_review.json',
        'handoff_review_md': 'release_executor_handoff_packet_review.md',
        'operator_request_artifact': 'release_operator_execution_request.json',
        'operator_request_review_json': 'release_operator_execution_request_review.json',
        'operator_request_review_md': 'release_operator_execution_request_review.md',
        'precheck_artifact': 'official_release_execution_precheck.json',
        'executor_name': 'controlled_release_executor',
        'command_template': 'controlled-release --task {task_id} --batch {batch_id} --run {run_id} --mode dry-run',
        'requires_release_record': False,
        'forbidden_real_artifact': 'official_release_record.json',
        'adapter_manifest_artifact': 'release_executor_adapter_manifest.json',
    },
    'rollback': {
        'label': 'rollback',
        'contract_artifact': 'rollback_executor_contract.json',
        'request_artifact': 'rollback_execution_request.json',
        'dry_run_artifact': 'rollback_execution_dry_run_result.json',
        'receipt_artifact': 'rollback_execution_receipt.json',
        'review_artifact': 'rollback_executor_contract_review.md',
        'handoff_artifact': 'rollback_executor_handoff_packet.json',
        'handoff_review_json': 'rollback_executor_handoff_packet_review.json',
        'handoff_review_md': 'rollback_executor_handoff_packet_review.md',
        'operator_request_artifact': 'rollback_operator_execution_request.json',
        'operator_request_review_json': 'rollback_operator_execution_request_review.json',
        'operator_request_review_md': 'rollback_operator_execution_request_review.md',
        'precheck_artifact': 'rollback_execution_precheck.json',
        'executor_name': 'controlled_rollback_executor',
        'command_template': 'controlled-rollback --task {task_id} --batch {batch_id} --run {run_id} --mode dry-run',
        'requires_release_record': False,
        'forbidden_real_artifact': 'rollback_registration_record.json',
        'adapter_manifest_artifact': 'rollback_executor_adapter_manifest.json',
    },
}

SHARED_GATE_DEFINITIONS = [
    {
        'gate_id': 'human_approval_recorded',
        'title': '人工审批结果已记录',
        'severity': 'critical',
        'description': '未来真实执行器接入前，必须先有真实可追溯的人工审批结果。',
    },
    {
        'gate_id': 'human_approval_approved',
        'title': '人工审批状态为 approved',
        'severity': 'critical',
        'description': '真实执行器只能在审批已通过后进入人工触发边界。',
    },
    {
        'gate_id': 'execution_batch_bound',
        'title': 'batch_id / run_id 绑定完成',
        'severity': 'critical',
        'description': 'release / rollback 必须绑定同一批次并各自持有 run_id，保证审计链可回放。',
    },
    {
        'gate_id': 'release_artifact_binding_ready',
        'title': 'release / rollback 产物绑定已就绪',
        'severity': 'critical',
        'description': '正式执行前必须先完成候选产物与回滚产物绑定。',
    },
    {
        'gate_id': 'rollback_supported',
        'title': '回滚支持明确可见',
        'severity': 'critical',
        'description': 'release / rollback 共用一套安全门槛；没有回滚支持时不允许未来真实接入。',
    },
    {
        'gate_id': 'target_precheck_ready',
        'title': '目标侧 preflight/precheck 已通过',
        'severity': 'critical',
        'description': '真实执行器接入前，目标侧 preflight contract 必须先显示 ready。',
    },
    {
        'gate_id': 'executor_contract_materialized',
        'title': '受控执行器契约已物化',
        'severity': 'high',
        'description': '执行器接口契约必须固定，可供 dry-run / receipt / handoff 复核。',
    },
    {
        'gate_id': 'dry_run_validated',
        'title': 'dry-run 已验证通过',
        'severity': 'high',
        'description': '未来真实执行器接入前，必须先经过零副作用 dry-run 验证。',
    },
    {
        'gate_id': 'execution_receipt_recorded',
        'title': 'execution receipt 已登记',
        'severity': 'high',
        'description': 'dry-run 与未来真实执行共用 receipt traceability 协议。',
    },
    {
        'gate_id': 'receipt_trace_complete',
        'title': 'receipt trace 字段完整',
        'severity': 'high',
        'description': 'proposal_ref / approval_ref / batch_id / run_id / command digest 必须完整。',
    },
    {
        'gate_id': 'zero_side_effect_dry_run',
        'title': 'dry-run 零副作用',
        'severity': 'critical',
        'description': '当前阶段只允许 dry-run 且 side_effect_count 必须为 0。',
    },
    {
        'gate_id': 'zero_real_execution_artifacts',
        'title': '零真实执行产物',
        'severity': 'critical',
        'description': '当前阶段不得生成真实正式发布或真实回滚登记产物。',
    },
]


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _expiry_due_at(*, requested_at: str | None, timeout_minutes: int | None) -> str | None:
    requested_dt = _parse_dt(requested_at)
    if requested_dt is None or timeout_minutes is None:
        return None
    return (requested_dt + timedelta(minutes=max(int(timeout_minutes), 0))).isoformat()


def _resolve_task_dir(*, task_dir: str | Path | None = None, task_id: str | None = None, jobs_root: str | Path = JOBS_ROOT) -> Path:
    if task_dir:
        resolved = Path(task_dir)
        if not resolved.exists():
            raise FileNotFoundError(f'task_dir not found: {resolved}')
        return resolved
    if task_id:
        resolved = Path(jobs_root) / task_id
        if not resolved.exists():
            raise FileNotFoundError(f'task_id not found under jobs_root: {resolved}')
        return resolved
    raise ValueError('task_dir or task_id is required')


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _states(*, closure_snapshot: dict[str, Any], request_recorded: bool, dry_run_validated: bool, receipt_recorded: bool, execution_target: str) -> dict[str, bool]:
    confirmation_state_key = 'release_execution_confirmation_state' if execution_target == 'release' else 'rollback_execution_confirmation_state'
    confirmation_state = closure_snapshot.get(confirmation_state_key)
    return {
        'planned': bool(closure_snapshot.get('execution_batch_visible')),
        'approved': closure_snapshot.get('human_approval_state') == 'approved',
        'execution_confirmed': confirmation_state in {'planned_not_started', 'in_progress', 'completed', 'failed', 'aborted'},
        'execution_requested': request_recorded,
        'dry_run_validated': dry_run_validated,
        'execution_receipt_recorded': receipt_recorded,
    }


def _build_contract(task_dir: Path, target: str) -> dict[str, Any]:
    cfg = TARGETS[target]
    closure_snapshot = load_release_closure_snapshot(task_dir)
    run_context = get_execution_run_context(task_dir, target)
    required_refs = [
        'artifacts/execution_batch.json',
        'artifacts/official_release_execution_plan.json',
        'artifacts/human_approval_record.json',
        'artifacts/human_approval_result_stub.json',
        'artifacts/release_artifact_binding.json',
        'protocols/execution_receipt.schema.json',
    ]
    if target == 'release':
        required_refs.append('artifacts/official_release_execution_precheck.json')
    else:
        required_refs.append('artifacts/rollback_execution_precheck.json')
        required_refs.append('artifacts/rollback_registry_entry.json')
    contract = {
        'task_id': task_dir.name,
        'record_type': 'controlled_executor_contract',
        'execution_target': cfg['label'],
        'executor_name': cfg['executor_name'],
        'executor_interface_version': 'v1',
        'execution_mode': 'dry_run_only',
        'auto_execution_enabled': False,
        'external_side_effects_allowed': False,
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'release_run_id': run_context['release_run_id'],
        'rollback_run_id': run_context['rollback_run_id'],
        'command_template': cfg['command_template'],
        'required_trace_fields': ['proposal_ref', 'approval_ref', 'batch_id', 'run_id', 'command_receipt_id', 'command_digest_sha256'],
        'required_references': required_refs,
        'preconditions': {
            'human_approval_state_required': 'approved',
            'execution_batch_visible': bool(closure_snapshot.get('execution_batch_visible')),
            'release_artifact_binding_ready': bool(closure_snapshot.get('release_artifact_binding_ready')),
            'rollback_supported': bool(closure_snapshot.get('rollback_supported')),
            'requires_release_record': cfg['requires_release_record'],
        },
        'allowed_transitions': ['planned', 'approved', 'execution_confirmed', 'execution_requested', 'dry_run_validated', 'execution_receipt_recorded'],
        'receipt_schema_reference': 'protocols/execution_receipt.schema.json',
        'generated_at': _now(),
        'note': 'Controlled executor contract only. It authorizes local contract validation, dry-run request creation, and mock receipt recording. It never executes a real release or rollback action.',
    }
    contract['contract_sha256'] = _sha256(json.dumps(contract, ensure_ascii=False, sort_keys=True))
    return contract




def _build_command_plan(*, task_dir: Path, target: str, run_context: dict[str, Any], command_preview: str, proposal_ref: str, approval_ref: str) -> dict[str, Any]:
    cfg = TARGETS[target]
    command_digest = _sha256(command_preview)
    command_receipt_id = f"receipt-{target}-{command_digest[:12]}"
    return {
        'plan_id': f"{task_dir.name}:{target}:{run_context['run_id']}:dry-run",
        'target': cfg['label'],
        'executor_name': cfg['executor_name'],
        'execution_mode': 'dry_run_only',
        'side_effect_free': True,
        'summary': f"Prepare operator-visible {cfg['label']} dry-run command plan without dispatching any real executor.",
        'steps': [
            {
                'step_id': f'{target}-step-01',
                'title': 'validate_controlled_contract',
                'kind': 'validation',
                'status': 'planned',
                'command_preview': 'validate contract + approval + binding prerequisites',
            },
            {
                'step_id': f'{target}-step-02',
                'title': 'generate_operator_request_envelope',
                'kind': 'envelope',
                'status': 'planned',
                'command_preview': 'materialize operator-facing request and handoff packet',
            },
            {
                'step_id': f'{target}-step-03',
                'title': 'record_mock_receipt_correlation',
                'kind': 'audit',
                'status': 'planned',
                'command_preview': 'bind request, dry-run, receipt, batch_id, and run_id into receipt trace contract',
            },
            {
                'step_id': f'{target}-step-04',
                'title': 'operator_command_preview',
                'kind': 'command_preview',
                'status': 'planned',
                'command_preview': command_preview,
                'command_digest_sha256': command_digest,
                'command_receipt_id': command_receipt_id,
            },
        ],
        'trace': {
            'proposal_ref': proposal_ref,
            'approval_ref': approval_ref,
            'batch_id': run_context['batch_id'],
            'run_id': run_context['run_id'],
            'command_receipt_id': command_receipt_id,
            'command_digest_sha256': command_digest,
        },
    }


def _materialize_handoff_layer(*, task_dir: Path, target: str, requested_by: str, proposal_ref: str, approval_ref: str, command_preview: str) -> dict[str, Any]:
    manager = ArtifactManager(task_dir)
    cfg = TARGETS[target]
    contract = _load_json(task_dir / 'artifacts' / cfg['contract_artifact']) or {}
    precheck = _load_json(task_dir / 'artifacts' / cfg['precheck_artifact']) or {}
    dry_run = _load_json(task_dir / 'artifacts' / cfg['dry_run_artifact']) or {}
    receipt = _load_json(task_dir / 'artifacts' / cfg['receipt_artifact']) or {}
    request = _load_json(task_dir / 'artifacts' / cfg['request_artifact']) or {}
    run_context = get_execution_run_context(task_dir, target)
    command_plan = _build_command_plan(task_dir=task_dir, target=target, run_context=run_context, command_preview=command_preview, proposal_ref=proposal_ref, approval_ref=approval_ref)
    correlation = {
        'correlation_ready': bool(receipt) and _trace_complete(receipt, expected_batch_id=run_context.get('batch_id'), expected_run_id=run_context.get('run_id')),
        'request_ref': f"artifacts/{cfg['request_artifact']}",
        'dry_run_ref': f"artifacts/{cfg['dry_run_artifact']}",
        'receipt_ref': f"artifacts/{cfg['receipt_artifact']}",
        'contract_ref': f"artifacts/{cfg['contract_artifact']}",
        'batch_id': run_context.get('batch_id'),
        'run_id': run_context.get('run_id'),
        'release_run_id': run_context.get('release_run_id'),
        'rollback_run_id': run_context.get('rollback_run_id'),
        'proposal_ref': proposal_ref,
        'approval_ref': approval_ref,
        'command_receipt_id': command_plan['trace']['command_receipt_id'],
        'command_digest_sha256': command_plan['trace']['command_digest_sha256'],
    }
    handoff_packet = {
        'task_id': task_dir.name,
        'record_type': 'executor_handoff_packet',
        'execution_target': cfg['label'],
        'requested_by': requested_by,
        'generated_at': _now(),
        'executor_name': cfg['executor_name'],
        'handoff_target': 'future_operator_or_real_executor_adapter',
        'execution_mode': 'dry_run_only',
        'real_execution_enabled': False,
        'external_side_effects_allowed': False,
        'contract_reference': f"artifacts/{cfg['contract_artifact']}",
        'precheck_reference': f"artifacts/{cfg['precheck_artifact']}",
        'request_reference': f"artifacts/{cfg['request_artifact']}",
        'dry_run_reference': f"artifacts/{cfg['dry_run_artifact']}",
        'receipt_reference': f"artifacts/{cfg['receipt_artifact']}",
        'run_context': run_context,
        'command_plan': command_plan,
        'receipt_correlation_contract': correlation,
        'operator_handoff_checklist': [
            'confirm approval and precheck artifacts are reviewed',
            'use command preview for human/operator rehearsal only',
            'do not dispatch to external system in current phase',
            'record future real receipt using the same correlation keys',
        ],
        'note': 'Executor handoff packet is an operator-ready boundary artifact only. It does not implement or authorize real release/rollback execution.',
    }
    operator_request = {
        'task_id': task_dir.name,
        'record_type': 'operator_execution_request',
        'execution_target': cfg['label'],
        'requested_by': requested_by,
        'requested_at': _now(),
        'execution_mode': 'dry_run_only',
        'operator_action': 'review_and_rehearse_command_plan_only',
        'real_execution_permitted': False,
        'handoff_packet_reference': f"artifacts/{cfg['handoff_artifact']}",
        'request_reference': f"artifacts/{cfg['request_artifact']}",
        'dry_run_reference': f"artifacts/{cfg['dry_run_artifact']}",
        'receipt_reference': f"artifacts/{cfg['receipt_artifact']}",
        'command_plan': command_plan,
        'receipt_correlation_contract': correlation,
        'operator_notes': [
            'current stage is mock/dry-run only',
            'no real formal release or rollback may be executed',
            'future real executor must preserve batch_id, run_id, command_receipt_id, and command_digest_sha256',
        ],
    }
    handoff_review = {
        'task_id': task_dir.name,
        'execution_target': cfg['label'],
        'handoff_packet_available': True,
        'operator_request_available': True,
        'receipt_correlation_ready': correlation['correlation_ready'],
        'command_plan_step_count': len(command_plan.get('steps') or []),
        'top_command_plan_steps': [step.get('title') for step in (command_plan.get('steps') or [])[:5]],
        'handoff_target': handoff_packet['handoff_target'],
        'execution_mode': 'dry_run_only',
        'real_execution_enabled': False,
    }
    manager.write_json(cfg['handoff_artifact'], handoff_packet)
    manager.write_json(cfg['operator_request_artifact'], operator_request)
    manager.write_json(cfg['handoff_review_json'], handoff_review)
    manager.write_json(cfg['operator_request_review_json'], dict(handoff_review, review_type='operator_execution_request'))
    manager.write_text(cfg['handoff_review_md'], "\n".join([
        f"# {cfg['label']} executor handoff packet review",
        '',
        f"- handoff_packet_available: true",
        f"- operator_request_available: true",
        f"- receipt_correlation_ready: {str(correlation['receipt_correlation_ready'] if 'receipt_correlation_ready' in correlation else correlation['correlation_ready']).lower()}",
        f"- handoff_target: {handoff_packet['handoff_target']}",
        f"- command_plan_step_count: {len(command_plan.get('steps') or [])}",
        f"- top_command_plan_steps: {', '.join(handoff_review['top_command_plan_steps'])}",
        '- note: operator-ready review only; no real executor dispatched.',
    ]) + "\n")
    manager.write_text(cfg['operator_request_review_md'], "\n".join([
        f"# {cfg['label']} operator execution request review",
        '',
        f"- operator_action: {operator_request['operator_action']}",
        f"- real_execution_permitted: false",
        f"- command_plan_step_count: {len(command_plan.get('steps') or [])}",
        f"- command_receipt_id: {correlation['command_receipt_id']}",
        f"- command_digest_sha256: {correlation['command_digest_sha256']}",
        '- note: review confirms request/receipt correlation contract is ready for future executor integration.',
    ]) + "\n")
    return {'handoff_packet': handoff_packet, 'operator_request': operator_request, 'review': handoff_review}

def _load_execution_request_lifecycle(task_dir: Path) -> dict[str, Any]:
    payload = _load_json(task_dir / 'artifacts' / 'execution_request_lifecycle.json') or {}
    if not payload:
        return {
            'task_id': task_dir.name,
            'record_type': 'execution_request_lifecycle',
            'requests': {},
            'summary': {},
        }
    payload.setdefault('task_id', task_dir.name)
    payload.setdefault('record_type', 'execution_request_lifecycle')
    payload.setdefault('requests', {})
    payload.setdefault('summary', {})
    return payload


def _request_state_summary(*, lifecycle: dict[str, Any]) -> dict[str, Any]:
    requests = lifecycle.get('requests', {}) or {}
    state_counter: Counter[str] = Counter()
    recent_actions: list[dict[str, Any]] = []
    recent_transitions: list[dict[str, Any]] = []
    recent_escalations: list[dict[str, Any]] = []
    owner_counter: Counter[str] = Counter()
    traceability_ready_count = 0
    reassigned_count = 0
    escalated_count = 0
    retry_ready_count = 0
    open_count = 0
    inflight_count = 0
    pending_requests: list[dict[str, Any]] = []
    for key, request in requests.items():
        state = str(request.get('request_state') or 'unknown')
        state_counter[state] += 1
        if state in {'requested', 'acknowledged'}:
            open_count += 1
        if state in {'requested', 'acknowledged', 'accepted'}:
            inflight_count += 1
        if request.get('traceability_ready'):
            traceability_ready_count += 1
        current_owner = str(request.get('current_owner') or request.get('requested_by') or '').strip()
        if current_owner:
            owner_counter[current_owner] += 1
        if request.get('reassignment_count'):
            reassigned_count += int(request.get('reassignment_count') or 0)
        if request.get('escalation_count'):
            escalated_count += int(request.get('escalation_count') or 0)
        if request.get('retry_ready'):
            retry_ready_count += 1
        if state in {'requested', 'acknowledged', 'accepted'} or request.get('retry_ready'):
            pending_requests.append({
                'target': key,
                'request_state': state,
                'current_owner': current_owner or None,
                'requested_at': request.get('requested_at'),
                'expires_at': request.get('expires_at'),
                'batch_id': request.get('batch_id'),
                'run_id': request.get('run_id'),
                'escalation_level': request.get('escalation_level') or 'none',
                'retry_ready': bool(request.get('retry_ready')),
                'reassignment_count': int(request.get('reassignment_count') or 0),
                'escalation_count': int(request.get('escalation_count') or 0),
                'request_reference': request.get('request_reference'),
                'operator_request_reference': request.get('operator_request_reference'),
            })
        for action in list(request.get('lifecycle_history') or []):
            packed = {
                'target': key,
                'state': action.get('state'),
                'action': action.get('action'),
                'acted_by': action.get('acted_by'),
                'acted_at': action.get('acted_at'),
            }
            recent_actions.append(packed)
            recent_transitions.append({
                **packed,
                'owner': action.get('owner') or request.get('current_owner'),
                'note': action.get('note'),
                'reason': action.get('reason'),
                'batch_id': request.get('batch_id'),
                'run_id': request.get('run_id'),
            })
            if action.get('action') == 'escalated':
                recent_escalations.append({
                    **packed,
                    'escalation_level': action.get('escalation_level'),
                    'escalation_reason': action.get('escalation_reason') or action.get('reason'),
                    'owner': action.get('owner') or request.get('current_owner'),
                })
    recent_actions.sort(key=lambda item: str(item.get('acted_at') or ''), reverse=True)
    recent_transitions.sort(key=lambda item: str(item.get('acted_at') or ''), reverse=True)
    recent_escalations.sort(key=lambda item: str(item.get('acted_at') or ''), reverse=True)
    pending_requests.sort(
        key=lambda item: (
            0 if item.get('retry_ready') else 1,
            {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'none': 4}.get(str(item.get('escalation_level') or 'none'), 5),
            '' if item.get('expires_at') else 'z',
            str(item.get('expires_at') or item.get('requested_at') or ''),
            str(item.get('target') or ''),
        )
    )
    return {
        'request_count': len(requests),
        'requested_count': state_counter.get('requested', 0),
        'acknowledged_count': state_counter.get('acknowledged', 0),
        'accepted_count': state_counter.get('accepted', 0),
        'declined_count': state_counter.get('declined', 0),
        'expired_count': state_counter.get('expired', 0),
        'open_count': open_count,
        'inflight_count': inflight_count,
        'reassigned_count': reassigned_count,
        'escalated_count': escalated_count,
        'retry_ready_count': retry_ready_count,
        'state_counts': dict(state_counter),
        'top_request_states': [state for state, _count in state_counter.most_common(5)],
        'top_pending_requests': pending_requests[:5],
        'recent_request_actions': recent_actions[:8],
        'recent_request_transitions': recent_transitions[:8],
        'recent_request_escalations': recent_escalations[:8],
        'top_request_owners': [{'owner': owner, 'request_count': count} for owner, count in owner_counter.most_common(5)],
        'traceability_ready_count': traceability_ready_count,
    }



def _write_execution_request_registry_artifacts(task_dir: Path, lifecycle: dict[str, Any]) -> None:
    manager = ArtifactManager(task_dir)
    summary = lifecycle.get('summary', {}) or {}
    requests = lifecycle.get('requests', {}) or {}
    generated_at = lifecycle.get('generated_at') or _now()
    registry_items = []
    history_items = []
    for target, request in requests.items():
        registry_items.append({
            'target': target,
            'execution_target': request.get('execution_target'),
            'request_state': request.get('request_state'),
            'current_owner': request.get('current_owner'),
            'requested_by': request.get('requested_by'),
            'requested_at': request.get('requested_at'),
            'acknowledged_by': request.get('acknowledged_by'),
            'acknowledged_at': request.get('acknowledged_at'),
            'accepted_by': request.get('accepted_by'),
            'accepted_at': request.get('accepted_at'),
            'declined_by': request.get('declined_by'),
            'declined_at': request.get('declined_at'),
            'expired_by': request.get('expired_by'),
            'expired_at': request.get('expired_at'),
            'expiry_timeout_minutes': request.get('expiry_timeout_minutes'),
            'expires_at': request.get('expires_at'),
            'retry_ready': request.get('retry_ready', False),
            'retry_reason': request.get('retry_reason'),
            'retry_routed_to': request.get('retry_routed_to'),
            'retry_attempt_count': request.get('retry_attempt_count', 0),
            'escalation_level': request.get('escalation_level') or 'none',
            'escalation_reason': request.get('escalation_reason'),
            'escalation_count': request.get('escalation_count', 0),
            'reassignment_count': request.get('reassignment_count', 0),
            'traceability_ready': request.get('traceability_ready', False),
            'batch_id': request.get('batch_id'),
            'run_id': request.get('run_id'),
            'release_run_id': request.get('release_run_id'),
            'rollback_run_id': request.get('rollback_run_id'),
            'proposal_ref': request.get('proposal_ref'),
            'approval_ref': request.get('approval_ref'),
            'request_reference': request.get('request_reference'),
            'operator_request_reference': request.get('operator_request_reference'),
            'handoff_packet_reference': request.get('handoff_packet_reference'),
            'receipt_reference': request.get('receipt_reference'),
            'command_receipt_id': request.get('command_receipt_id'),
            'command_digest_sha256': request.get('command_digest_sha256'),
            'history_event_count': len(request.get('lifecycle_history') or []),
            'last_transition_at': ((request.get('lifecycle_history') or [{}])[-1] or {}).get('acted_at'),
        })
        for index, event in enumerate(list(request.get('lifecycle_history') or []), start=1):
            history_items.append({
                'task_id': task_dir.name,
                'target': target,
                'sequence': index,
                'action': event.get('action'),
                'state': event.get('state'),
                'acted_by': event.get('acted_by'),
                'acted_at': event.get('acted_at'),
                'operator_role': event.get('operator_role'),
                'owner': event.get('owner') or request.get('current_owner'),
                'note': event.get('note'),
                'reason': event.get('reason'),
                'escalation_level': event.get('escalation_level'),
                'escalation_reason': event.get('escalation_reason'),
                'batch_id': request.get('batch_id'),
                'run_id': request.get('run_id'),
                'release_run_id': request.get('release_run_id'),
                'rollback_run_id': request.get('rollback_run_id'),
                'proposal_ref': request.get('proposal_ref'),
                'approval_ref': request.get('approval_ref'),
                'request_reference': request.get('request_reference'),
                'operator_request_reference': request.get('operator_request_reference'),
                'receipt_reference': request.get('receipt_reference'),
                'retry_ready': request.get('retry_ready', False),
            })
    registry = {
        'task_id': task_dir.name,
        'record_type': 'execution_request_registry',
        'generated_at': generated_at,
        'batch_id': lifecycle.get('batch_id'),
        'release_run_id': lifecycle.get('release_run_id'),
        'rollback_run_id': lifecycle.get('rollback_run_id'),
        'request_count': summary.get('request_count', len(registry_items)),
        'request_open_count': summary.get('open_count', 0),
        'request_inflight_count': summary.get('inflight_count', 0),
        'request_declined_count': summary.get('declined_count', 0),
        'request_expired_count': summary.get('expired_count', 0),
        'retry_ready_count': summary.get('retry_ready_count', 0),
        'top_pending_requests': summary.get('top_pending_requests', []),
        'recent_request_transitions': summary.get('recent_request_transitions', []),
        'items': registry_items,
    }
    manager.write_json('execution_request_registry.json', registry)
    dispatch_review = {
        'task_id': task_dir.name,
        'record_type': 'execution_request_dispatch_review',
        'generated_at': generated_at,
        'request_open_count': registry['request_open_count'],
        'request_inflight_count': registry['request_inflight_count'],
        'request_declined_count': registry['request_declined_count'],
        'request_expired_count': registry['request_expired_count'],
        'retry_ready_count': registry['retry_ready_count'],
        'top_pending_requests': registry['top_pending_requests'],
        'recent_request_transitions': registry['recent_request_transitions'],
        'dispatch_queue': registry['top_pending_requests'],
    }
    manager.write_json('execution_request_dispatch_review.json', dispatch_review)
    md_lines = [
        '# execution request dispatch review',
        '',
        f"- request_open_count: {dispatch_review['request_open_count']}",
        f"- request_inflight_count: {dispatch_review['request_inflight_count']}",
        f"- request_declined_count: {dispatch_review['request_declined_count']}",
        f"- request_expired_count: {dispatch_review['request_expired_count']}",
        f"- retry_ready_count: {dispatch_review['retry_ready_count']}",
        '- top_pending_requests:',
    ]
    if dispatch_review['top_pending_requests']:
        for item in dispatch_review['top_pending_requests']:
            md_lines.append(
                f"  - {item.get('target')}: state={item.get('request_state')} owner={item.get('current_owner')} escalation={item.get('escalation_level')} retry_ready={item.get('retry_ready')} expires_at={item.get('expires_at')} batch_id={item.get('batch_id')} run_id={item.get('run_id')}"
            )
    else:
        md_lines.append('  - none')
    md_lines.append('- recent_request_transitions:')
    if dispatch_review['recent_request_transitions']:
        for item in dispatch_review['recent_request_transitions']:
            md_lines.append(
                f"  - {item.get('acted_at')}: {item.get('target')} -> {item.get('action')} ({item.get('state')}) by {item.get('acted_by')} owner={item.get('owner')}"
            )
    else:
        md_lines.append('  - none')
    manager.write_text('execution_request_dispatch_review.md', '\n'.join(md_lines) + '\n')
    history_items.sort(key=lambda item: (str(item.get('acted_at') or ''), str(item.get('target') or ''), int(item.get('sequence') or 0)))
    ledger_path = task_dir / 'artifacts' / 'execution_request_history_ledger.jsonl'
    lines = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in history_items]
    ledger_path.write_text(('\\n'.join(lines) + ('\\n' if lines else '')).encode('utf-8').decode('unicode_escape'), encoding='utf-8')


def _write_execution_request_lifecycle(task_dir: Path, lifecycle: dict[str, Any]) -> dict[str, Any]:
    manager = ArtifactManager(task_dir)
    lifecycle['task_id'] = task_dir.name
    lifecycle['record_type'] = 'execution_request_lifecycle'
    lifecycle['generated_at'] = _now()
    lifecycle['summary'] = _request_state_summary(lifecycle=lifecycle)
    manager.write_json('execution_request_lifecycle.json', lifecycle)

    review = {
        'task_id': task_dir.name,
        'record_type': 'operator_acknowledgement_review',
        'generated_at': lifecycle['generated_at'],
        'request_count': lifecycle['summary']['request_count'],
        'execution_request_requested_count': lifecycle['summary']['requested_count'],
        'execution_request_acknowledged_count': lifecycle['summary']['acknowledged_count'],
        'execution_request_accepted_count': lifecycle['summary']['accepted_count'],
        'execution_request_declined_count': lifecycle['summary']['declined_count'],
        'execution_request_expired_count': lifecycle['summary']['expired_count'],
        'request_open_count': lifecycle['summary']['open_count'],
        'request_inflight_count': lifecycle['summary']['inflight_count'],
        'execution_request_reassigned_count': lifecycle['summary']['reassigned_count'],
        'execution_request_escalated_count': lifecycle['summary']['escalated_count'],
        'execution_request_retry_ready_count': lifecycle['summary']['retry_ready_count'],
        'top_request_states': lifecycle['summary']['top_request_states'],
        'top_pending_requests': lifecycle['summary']['top_pending_requests'],
        'recent_request_actions': lifecycle['summary']['recent_request_actions'],
        'recent_request_transitions': lifecycle['summary']['recent_request_transitions'],
        'recent_request_escalations': lifecycle['summary']['recent_request_escalations'],
        'top_request_owners': lifecycle['summary']['top_request_owners'],
        'traceability_ready_count': lifecycle['summary']['traceability_ready_count'],
        'targets': {
            key: {
                'request_state': value.get('request_state'),
                'requested_by': value.get('requested_by'),
                'requested_at': value.get('requested_at'),
                'current_owner': value.get('current_owner'),
                'expiry_timeout_minutes': value.get('expiry_timeout_minutes'),
                'expires_at': value.get('expires_at'),
                'acknowledged_by': value.get('acknowledged_by'),
                'acknowledged_at': value.get('acknowledged_at'),
                'accepted_by': value.get('accepted_by'),
                'accepted_at': value.get('accepted_at'),
                'declined_by': value.get('declined_by'),
                'declined_at': value.get('declined_at'),
                'escalation_level': value.get('escalation_level'),
                'escalation_reason': value.get('escalation_reason'),
                'reassignment_count': value.get('reassignment_count', 0),
                'escalation_count': value.get('escalation_count', 0),
                'retry_ready': value.get('retry_ready', False),
                'run_id': value.get('run_id'),
                'batch_id': value.get('batch_id'),
            }
            for key, value in (lifecycle.get('requests') or {}).items()
        },
    }
    manager.write_json('operator_acknowledgement_review.json', review)
    md_lines = [
        '# operator acknowledgement review',
        '',
        f"- execution_request_requested_count: {review['execution_request_requested_count']}",
        f"- execution_request_acknowledged_count: {review['execution_request_acknowledged_count']}",
        f"- execution_request_accepted_count: {review['execution_request_accepted_count']}",
        f"- execution_request_declined_count: {review['execution_request_declined_count']}",
        f"- execution_request_expired_count: {review['execution_request_expired_count']}",
        f"- request_open_count: {review['request_open_count']}",
        f"- request_inflight_count: {review['request_inflight_count']}",
        f"- execution_request_reassigned_count: {review['execution_request_reassigned_count']}",
        f"- execution_request_escalated_count: {review['execution_request_escalated_count']}",
        f"- execution_request_retry_ready_count: {review['execution_request_retry_ready_count']}",
        f"- top_request_states: {', '.join(review['top_request_states']) if review['top_request_states'] else 'none'}",
        "- top_request_owners: " + (', '.join([f"{item.get('owner')}({item.get('request_count')})" for item in review['top_request_owners']]) if review['top_request_owners'] else 'none'),
        f"- traceability_ready_count: {review['traceability_ready_count']}",
        '- recent_request_actions:',
    ]
    if review['recent_request_actions']:
        for item in review['recent_request_actions']:
            md_lines.append(f"  - {item.get('acted_at')}: {item.get('target')} -> {item.get('action')} ({item.get('state')}) by {item.get('acted_by')}")
    else:
        md_lines.append('  - none')
    md_lines.append('- recent_request_escalations:')
    if review['recent_request_escalations']:
        for item in review['recent_request_escalations']:
            md_lines.append(f"  - {item.get('acted_at')}: {item.get('target')} escalation={item.get('escalation_level')} owner={item.get('owner')} reason={item.get('escalation_reason')}")
    else:
        md_lines.append('  - none')
    manager.write_text('operator_acknowledgement_review.md', '\n'.join(md_lines) + '\n')
    _write_execution_request_governance_artifacts(task_dir, lifecycle)
    _write_execution_request_registry_artifacts(task_dir, lifecycle)
    return lifecycle


def _write_execution_request_governance_artifacts(task_dir: Path, lifecycle: dict[str, Any]) -> None:
    manager = ArtifactManager(task_dir)
    requests = lifecycle.get('requests') or {}
    escalation_items = []
    retry_items = []
    for target, request in requests.items():
        escalation_items.append({
            'target': target,
            'request_state': request.get('request_state'),
            'batch_id': request.get('batch_id'),
            'run_id': request.get('run_id'),
            'current_owner': request.get('current_owner'),
            'escalation_level': request.get('escalation_level') or 'none',
            'escalation_reason': request.get('escalation_reason'),
            'escalation_count': request.get('escalation_count', 0),
            'reassignment_count': request.get('reassignment_count', 0),
            'expires_at': request.get('expires_at'),
            'expired_at': request.get('expired_at'),
            'retry_ready': request.get('retry_ready', False),
            'retry_reason': request.get('retry_reason'),
            'last_retry_marked_at': request.get('last_retry_marked_at'),
            'traceability_ready': request.get('traceability_ready', False),
            'proposal_ref': request.get('proposal_ref'),
            'approval_ref': request.get('approval_ref'),
            'request_reference': request.get('request_reference'),
            'operator_request_reference': request.get('operator_request_reference'),
        })
        retry_items.append({
            'target': target,
            'request_state': request.get('request_state'),
            'retry_ready': request.get('retry_ready', False),
            'retry_reason': request.get('retry_reason'),
            'retry_routed_to': request.get('retry_routed_to'),
            'retry_attempt_count': request.get('retry_attempt_count', 0),
            'last_retry_marked_at': request.get('last_retry_marked_at'),
            'current_owner': request.get('current_owner'),
            'batch_id': request.get('batch_id'),
            'run_id': request.get('run_id'),
            'traceability_ready': request.get('traceability_ready', False),
            'request_reference': request.get('request_reference'),
            'operator_request_reference': request.get('operator_request_reference'),
        })
    escalation_review = {
        'task_id': task_dir.name,
        'record_type': 'execution_request_escalation_review',
        'generated_at': lifecycle.get('generated_at') or _now(),
        'execution_request_expired_count': lifecycle.get('summary', {}).get('expired_count', 0),
        'execution_request_reassigned_count': lifecycle.get('summary', {}).get('reassigned_count', 0),
        'execution_request_escalated_count': lifecycle.get('summary', {}).get('escalated_count', 0),
        'execution_request_retry_ready_count': lifecycle.get('summary', {}).get('retry_ready_count', 0),
        'recent_request_escalations': lifecycle.get('summary', {}).get('recent_request_escalations', []),
        'top_request_owners': lifecycle.get('summary', {}).get('top_request_owners', []),
        'items': escalation_items,
    }
    manager.write_json('execution_request_escalation_review.json', escalation_review)
    escalation_md = [
        '# execution request escalation review',
        '',
        f"- execution_request_expired_count: {escalation_review['execution_request_expired_count']}",
        f"- execution_request_reassigned_count: {escalation_review['execution_request_reassigned_count']}",
        f"- execution_request_escalated_count: {escalation_review['execution_request_escalated_count']}",
        f"- execution_request_retry_ready_count: {escalation_review['execution_request_retry_ready_count']}",
        "- top_request_owners: " + (', '.join([f"{item.get('owner')}({item.get('request_count')})" for item in escalation_review['top_request_owners']]) if escalation_review['top_request_owners'] else 'none'),
        '- items:',
    ]
    for item in escalation_items:
        escalation_md.append(f"  - {item.get('target')}: state={item.get('request_state')} owner={item.get('current_owner')} escalation={item.get('escalation_level')} expired_at={item.get('expired_at')} retry_ready={item.get('retry_ready')}")
    manager.write_text('execution_request_escalation_review.md', '\n'.join(escalation_md) + '\n')
    retry_summary = {
        'task_id': task_dir.name,
        'record_type': 'execution_request_retry_summary',
        'generated_at': lifecycle.get('generated_at') or _now(),
        'execution_request_retry_ready_count': lifecycle.get('summary', {}).get('retry_ready_count', 0),
        'execution_request_expired_count': lifecycle.get('summary', {}).get('expired_count', 0),
        'recent_request_escalations': lifecycle.get('summary', {}).get('recent_request_escalations', []),
        'items': retry_items,
    }
    manager.write_json('execution_request_retry_summary.json', retry_summary)
    retry_md = [
        '# execution request retry summary',
        '',
        f"- execution_request_retry_ready_count: {retry_summary['execution_request_retry_ready_count']}",
        f"- execution_request_expired_count: {retry_summary['execution_request_expired_count']}",
        '- items:',
    ]
    for item in retry_items:
        retry_md.append(f"  - {item.get('target')}: state={item.get('request_state')} retry_ready={item.get('retry_ready')} retry_attempt_count={item.get('retry_attempt_count')} retry_reason={item.get('retry_reason')}")
    manager.write_text('execution_request_retry_summary.md', '\n'.join(retry_md) + '\n')


def _record_request_lifecycle_event(*, task_dir: Path, target: str, action: str, state: str, acted_by: str, note: str = '', reason: str = '', operator_role: str = 'human_operator') -> dict[str, Any]:
    cfg = TARGETS[target]
    lifecycle = _load_execution_request_lifecycle(task_dir)
    run_context = get_execution_run_context(task_dir, target)
    request_payload = _load_json(task_dir / 'artifacts' / cfg['request_artifact']) or {}
    operator_request = _load_json(task_dir / 'artifacts' / cfg['operator_request_artifact']) or {}
    receipt = _load_json(task_dir / 'artifacts' / cfg['receipt_artifact']) or {}
    handoff_packet = _load_json(task_dir / 'artifacts' / cfg['handoff_artifact']) or {}
    requests = lifecycle.setdefault('requests', {})
    entry = requests.get(target, {}) or {
        'task_id': task_dir.name,
        'execution_target': cfg['label'],
        'batch_id': run_context.get('batch_id'),
        'run_id': run_context.get('run_id'),
        'release_run_id': run_context.get('release_run_id'),
        'rollback_run_id': run_context.get('rollback_run_id'),
        'request_reference': f"artifacts/{cfg['request_artifact']}",
        'operator_request_reference': f"artifacts/{cfg['operator_request_artifact']}",
        'handoff_packet_reference': f"artifacts/{cfg['handoff_artifact']}",
        'receipt_reference': f"artifacts/{cfg['receipt_artifact']}",
        'proposal_ref': request_payload.get('proposal_ref'),
        'approval_ref': request_payload.get('approval_ref'),
        'command_receipt_id': ((receipt.get('receipt_trace') or {}).get('command_receipt_id')) or ((operator_request.get('receipt_correlation_contract') or {}).get('command_receipt_id')),
        'command_digest_sha256': ((receipt.get('receipt_trace') or {}).get('command_digest_sha256')) or ((operator_request.get('receipt_correlation_contract') or {}).get('command_digest_sha256')),
        'requested_by': request_payload.get('requested_by') or operator_request.get('requested_by'),
        'requested_at': request_payload.get('requested_at') or operator_request.get('requested_at'),
        'current_owner': (operator_request.get('operator_identity') or {}).get('operator_id') or request_payload.get('requested_by') or operator_request.get('requested_by'),
        'expiry_policy': {
            'policy_state': 'armed_on_request',
            'timeout_minutes': 120,
            'applies_to_targets': ['release', 'rollback'],
            'auto_execute': False,
        },
        'expiry_timeout_minutes': 120,
        'expires_at': _expiry_due_at(requested_at=request_payload.get('requested_at') or operator_request.get('requested_at'), timeout_minutes=120),
        'reassignment_count': 0,
        'escalation_count': 0,
        'retry_attempt_count': 0,
        'retry_ready': False,
        'lifecycle_history': [],
    }
    event = {
        'action': action,
        'state': state,
        'acted_by': acted_by,
        'acted_at': _now(),
        'operator_role': operator_role,
        'note': note,
        'reason': reason,
        'owner': entry.get('current_owner'),
        'escalation_level': entry.get('escalation_level'),
        'escalation_reason': entry.get('escalation_reason'),
    }
    entry['request_state'] = state
    entry['traceability_ready'] = _trace_complete(receipt, expected_batch_id=run_context.get('batch_id'), expected_run_id=run_context.get('run_id'))
    if action == 'requested':
        entry['requested_by'] = acted_by
        entry['requested_at'] = event['acted_at']
        entry['current_owner'] = entry.get('current_owner') or acted_by
        entry['expires_at'] = _expiry_due_at(requested_at=entry.get('requested_at'), timeout_minutes=entry.get('expiry_timeout_minutes'))
    elif action == 'acknowledged':
        entry['acknowledged_by'] = acted_by
        entry['acknowledged_at'] = event['acted_at']
    elif action == 'accepted':
        entry['accepted_by'] = acted_by
        entry['accepted_at'] = event['acted_at']
    elif action == 'declined':
        entry['declined_by'] = acted_by
        entry['declined_at'] = event['acted_at']
    elif action == 'expired':
        entry['expired_by'] = acted_by
        entry['expired_at'] = event['acted_at']
        entry['retry_ready'] = True
        entry['retry_reason'] = entry.get('retry_reason') or reason or 'request_expired_before_operator_commitment'
        entry['last_retry_marked_at'] = event['acted_at']
    entry.setdefault('lifecycle_history', []).append(event)
    requests[target] = entry
    lifecycle['batch_id'] = lifecycle.get('batch_id') or run_context.get('batch_id')
    lifecycle['release_run_id'] = lifecycle.get('release_run_id') or run_context.get('release_run_id')
    lifecycle['rollback_run_id'] = lifecycle.get('rollback_run_id') or run_context.get('rollback_run_id')
    manager = ArtifactManager(task_dir)
    manager.write_json(f'{target}_operator_intent_record.json', {
        'task_id': task_dir.name,
        'record_type': 'operator_intent_record',
        'execution_target': cfg['label'],
        'intent_state': state,
        'intent_action': action,
        'actor': acted_by,
        'operator_role': operator_role,
        'batch_id': run_context.get('batch_id'),
        'run_id': run_context.get('run_id'),
        'request_reference': f"artifacts/{cfg['request_artifact']}",
        'operator_request_reference': f"artifacts/{cfg['operator_request_artifact']}",
        'proposal_ref': entry.get('proposal_ref'),
        'approval_ref': entry.get('approval_ref'),
        'generated_at': event['acted_at'],
        'note': note,
        'reason': reason,
    })
    manager.write_json(f'{target}_handoff_acknowledgement.json', {
        'task_id': task_dir.name,
        'record_type': 'handoff_acknowledgement',
        'execution_target': cfg['label'],
        'handoff_target': handoff_packet.get('handoff_target'),
        'handoff_packet_reference': f"artifacts/{cfg['handoff_artifact']}",
        'operator_request_reference': f"artifacts/{cfg['operator_request_artifact']}",
        'acknowledgement_state': state,
        'acknowledged_by': acted_by,
        'acknowledged_at': event['acted_at'],
        'real_execution_enabled': False,
        'note': 'Acknowledges receipt/acceptance of the handoff only. No real executor is called.',
    })
    manager.write_json(f'{target}_request_acceptance_audit.json', {
        'task_id': task_dir.name,
        'record_type': 'request_acceptance_audit',
        'execution_target': cfg['label'],
        'request_state': state,
        'latest_action': action,
        'batch_id': run_context.get('batch_id'),
        'run_id': run_context.get('run_id'),
        'request_reference': f"artifacts/{cfg['request_artifact']}",
        'receipt_reference': f"artifacts/{cfg['receipt_artifact']}",
        'traceability_ready': entry['traceability_ready'],
        'command_receipt_id': entry.get('command_receipt_id'),
        'command_digest_sha256': entry.get('command_digest_sha256'),
        'history_count': len(entry.get('lifecycle_history') or []),
        'generated_at': event['acted_at'],
        'note': 'Acceptance audit covers request receipt/acknowledgement only and explicitly excludes any real execution.',
    })
    return _write_execution_request_lifecycle(task_dir, lifecycle)


def acknowledge_execution_request(task_dir: str | Path, *, target: str, action: str, acted_by: str, note: str = '', reason: str = '', operator_role: str = 'human_operator') -> dict[str, Any]:
    task_dir = Path(task_dir)
    action_to_state = {
        'acknowledge': 'acknowledged',
        'accept': 'accepted',
        'decline': 'declined',
        'expire': 'expired',
    }
    if action not in action_to_state:
        raise ValueError(f'unsupported action: {action}')
    lifecycle = _load_execution_request_lifecycle(task_dir)
    current_state = (((lifecycle.get('requests') or {}).get(target) or {}).get('request_state') or '')
    if action == 'accept' and current_state not in {'requested', 'acknowledged', 'accepted'}:
        raise ValueError(f'cannot accept request from state: {current_state or "missing"}')
    if action == 'decline' and current_state not in {'requested', 'acknowledged', 'declined'}:
        raise ValueError(f'cannot decline request from state: {current_state or "missing"}')
    if action == 'acknowledge' and current_state not in {'requested', 'acknowledged'}:
        raise ValueError(f'cannot acknowledge request from state: {current_state or "missing"}')
    if action == 'expire' and current_state not in {'requested', 'acknowledged', 'expired'}:
        raise ValueError(f'cannot expire request from state: {current_state or "missing"}')
    if action in {'accept', 'decline'} and current_state == 'requested':
        _record_request_lifecycle_event(task_dir=task_dir, target=target, action='acknowledged', state='acknowledged', acted_by=acted_by, note='implicit acknowledgement before terminal acceptance decision', operator_role=operator_role)
    lifecycle = _record_request_lifecycle_event(task_dir=task_dir, target=target, action=action_to_state[action], state=action_to_state[action], acted_by=acted_by, note=note, reason=reason, operator_role=operator_role)
    _write_execution_control_summary(task_dir)
    return (lifecycle.get('requests') or {}).get(target, {})


def govern_execution_request(task_dir: str | Path, *, target: str, action: str, acted_by: str, timeout_minutes: int | None = None, new_owner: str = '', escalation_level: str = '', escalation_reason: str = '', retry_reason: str = '', reroute_target: str = '', note: str = '', operator_role: str = 'request_governor') -> dict[str, Any]:
    task_dir = Path(task_dir)
    lifecycle = _load_execution_request_lifecycle(task_dir)
    requests = lifecycle.setdefault('requests', {})
    if target not in requests:
        raise ValueError(f'missing execution request for target: {target}')
    entry = requests[target]
    now = _now()
    history = entry.setdefault('lifecycle_history', [])
    if action == 'set-expiry-policy':
        timeout = int(timeout_minutes or entry.get('expiry_timeout_minutes') or 120)
        entry['expiry_timeout_minutes'] = timeout
        entry['expiry_policy'] = {
            'policy_state': 'armed_on_request',
            'timeout_minutes': timeout,
            'applies_to_targets': ['release', 'rollback'],
            'auto_execute': False,
            'updated_by': acted_by,
            'updated_at': now,
        }
        entry['expires_at'] = _expiry_due_at(requested_at=entry.get('requested_at'), timeout_minutes=timeout)
        history.append({'action': 'expiry_policy_updated', 'state': entry.get('request_state'), 'acted_by': acted_by, 'acted_at': now, 'timeout_minutes': timeout, 'note': note, 'operator_role': operator_role, 'owner': entry.get('current_owner'), 'escalation_level': entry.get('escalation_level'), 'escalation_reason': entry.get('escalation_reason')})
    elif action == 'reassign':
        if not new_owner:
            raise ValueError('new_owner is required for reassign')
        previous_owner = entry.get('current_owner')
        entry['current_owner'] = new_owner
        entry['last_reassigned_at'] = now
        entry['last_reassigned_by'] = acted_by
        entry['last_reroute_target'] = reroute_target or target
        entry['reassignment_count'] = int(entry.get('reassignment_count') or 0) + 1
        history.append({'action': 'reassigned', 'state': entry.get('request_state'), 'acted_by': acted_by, 'acted_at': now, 'from_owner': previous_owner, 'to_owner': new_owner, 'reroute_target': reroute_target or target, 'note': note, 'operator_role': operator_role, 'owner': new_owner, 'escalation_level': entry.get('escalation_level'), 'escalation_reason': entry.get('escalation_reason')})
    elif action == 'escalate':
        level = escalation_level or 'medium'
        entry['escalation_level'] = level
        entry['escalation_reason'] = escalation_reason or note or 'manual_request_governance_escalation'
        entry['last_escalated_at'] = now
        entry['last_escalated_by'] = acted_by
        entry['escalation_count'] = int(entry.get('escalation_count') or 0) + 1
        history.append({'action': 'escalated', 'state': entry.get('request_state'), 'acted_by': acted_by, 'acted_at': now, 'escalation_level': level, 'escalation_reason': entry.get('escalation_reason'), 'note': note, 'operator_role': operator_role, 'owner': entry.get('current_owner')})
    elif action == 'mark-retry-ready':
        entry['retry_ready'] = True
        entry['retry_reason'] = retry_reason or escalation_reason or note or 'manual_retry_ready_governance'
        entry['retry_routed_to'] = reroute_target or entry.get('current_owner')
        entry['last_retry_marked_at'] = now
        entry['retry_attempt_count'] = int(entry.get('retry_attempt_count') or 0) + 1
        history.append({'action': 'retry_ready', 'state': entry.get('request_state'), 'acted_by': acted_by, 'acted_at': now, 'retry_reason': entry.get('retry_reason'), 'retry_routed_to': entry.get('retry_routed_to'), 'note': note, 'operator_role': operator_role, 'owner': entry.get('current_owner'), 'escalation_level': entry.get('escalation_level'), 'escalation_reason': entry.get('escalation_reason')})
    else:
        raise ValueError(f'unsupported governance action: {action}')
    requests[target] = entry
    _write_execution_request_lifecycle(task_dir, lifecycle)
    _write_execution_control_summary(task_dir)
    return entry


def _trace_complete(receipt: dict[str, Any], *, expected_batch_id: str | None, expected_run_id: str | None) -> bool:
    trace = (receipt or {}).get('receipt_trace') or {}
    required = [
        trace.get('proposal_ref'),
        trace.get('approval_ref'),
        trace.get('batch_id'),
        trace.get('run_id'),
        trace.get('command_receipt_id'),
        trace.get('command_digest_sha256'),
    ]
    if not all(required):
        return False
    if expected_batch_id and trace.get('batch_id') != expected_batch_id:
        return False
    if expected_run_id and trace.get('run_id') != expected_run_id:
        return False
    return True


def _evaluate_gate(*, gate_id: str, task_dir: Path, target: str, closure_snapshot: dict[str, Any], run_context: dict[str, Any], contract: dict[str, Any], precheck: dict[str, Any], dry_run: dict[str, Any], receipt: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    cfg = TARGETS[target]
    forbidden_real_artifact = task_dir / 'artifacts' / cfg['forbidden_real_artifact']
    if gate_id == 'human_approval_recorded':
        return bool(closure_snapshot.get('human_approval_result_recorded')), ['artifacts/human_approval_result_stub.json'], {'human_approval_result_recorded': closure_snapshot.get('human_approval_result_recorded')}
    if gate_id == 'human_approval_approved':
        return closure_snapshot.get('human_approval_state') == 'approved', ['artifacts/human_approval_record.json'], {'human_approval_state': closure_snapshot.get('human_approval_state')}
    if gate_id == 'execution_batch_bound':
        ok = bool(run_context.get('batch_id') and run_context.get('run_id'))
        return ok, ['artifacts/execution_batch.json'], {'batch_id': run_context.get('batch_id'), 'run_id': run_context.get('run_id')}
    if gate_id == 'release_artifact_binding_ready':
        return bool(closure_snapshot.get('release_artifact_binding_ready')), ['artifacts/release_artifact_binding.json'], {'release_artifact_binding_ready': closure_snapshot.get('release_artifact_binding_ready')}
    if gate_id == 'rollback_supported':
        return bool(closure_snapshot.get('rollback_supported')), ['artifacts/rollback_registry_entry.json'], {'rollback_supported': closure_snapshot.get('rollback_supported')}
    if gate_id == 'target_precheck_ready':
        return bool((precheck or {}).get('precheck_ready')), [f"artifacts/{cfg['precheck_artifact']}"], {'precheck_state': (precheck or {}).get('precheck_state'), 'blockers': list((precheck or {}).get('blockers') or [])}
    if gate_id == 'executor_contract_materialized':
        return bool(contract), [f"artifacts/{cfg['contract_artifact']}"], {'execution_mode': (contract or {}).get('execution_mode'), 'auto_execution_enabled': (contract or {}).get('auto_execution_enabled')}
    if gate_id == 'dry_run_validated':
        return bool((dry_run or {}).get('dry_run_validated')), [f"artifacts/{cfg['dry_run_artifact']}"], {'dry_run_validated': (dry_run or {}).get('dry_run_validated')}
    if gate_id == 'execution_receipt_recorded':
        return bool(receipt), [f"artifacts/{cfg['receipt_artifact']}"], {'receipt_state': (receipt or {}).get('receipt_state')}
    if gate_id == 'receipt_trace_complete':
        ok = _trace_complete(receipt or {}, expected_batch_id=run_context.get('batch_id'), expected_run_id=run_context.get('run_id'))
        return ok, [f"artifacts/{cfg['receipt_artifact']}"], {'receipt_trace_complete': ok}
    if gate_id == 'zero_side_effect_dry_run':
        ok = bool(dry_run) and int((dry_run or {}).get('side_effect_count', 0) or 0) == 0 and (dry_run or {}).get('real_execution_attempted') is False
        return ok, [f"artifacts/{cfg['dry_run_artifact']}"], {'side_effect_count': (dry_run or {}).get('side_effect_count'), 'real_execution_attempted': (dry_run or {}).get('real_execution_attempted')}
    if gate_id == 'zero_real_execution_artifacts':
        ok = not forbidden_real_artifact.exists()
        return ok, [f"artifacts/{cfg['forbidden_real_artifact']}"], {'forbidden_artifact_present': forbidden_real_artifact.exists()}
    raise KeyError(f'unsupported gate_id: {gate_id}')


def _build_target_readiness_review(task_dir: Path, *, target: str, closure_snapshot: dict[str, Any]) -> dict[str, Any]:
    cfg = TARGETS[target]
    run_context = get_execution_run_context(task_dir, target)
    contract = _load_json(task_dir / 'artifacts' / cfg['contract_artifact'])
    precheck = _load_json(task_dir / 'artifacts' / cfg['precheck_artifact'])
    dry_run = _load_json(task_dir / 'artifacts' / cfg['dry_run_artifact'])
    receipt = _load_json(task_dir / 'artifacts' / cfg['receipt_artifact'])
    request = _load_json(task_dir / 'artifacts' / cfg['request_artifact'])

    gates: list[dict[str, Any]] = []
    for gate_def in SHARED_GATE_DEFINITIONS:
        passed, evidence_refs, details = _evaluate_gate(
            gate_id=gate_def['gate_id'],
            task_dir=task_dir,
            target=target,
            closure_snapshot=closure_snapshot,
            run_context=run_context,
            contract=contract,
            precheck=precheck,
            dry_run=dry_run,
            receipt=receipt,
        )
        gates.append({
            'gate_id': gate_def['gate_id'],
            'title': gate_def['title'],
            'severity': gate_def['severity'],
            'description': gate_def['description'],
            'status': 'passed' if passed else 'unmet',
            'passed': passed,
            'evidence_refs': evidence_refs,
            'details': details,
        })

    unmet_gates = [gate['gate_id'] for gate in gates if not gate['passed']]
    critical_unmet = [gate['gate_id'] for gate in gates if not gate['passed'] and gate['severity'] == 'critical']
    checklist_items = [
        {
            'check_id': gate['gate_id'],
            'status': gate['status'],
            'required_before_real_executor_handoff': True,
            'severity': gate['severity'],
            'evidence_refs': gate['evidence_refs'],
        }
        for gate in gates
    ]
    return {
        'execution_target': cfg['label'],
        'executor_name': cfg['executor_name'],
        'batch_id': run_context.get('batch_id'),
        'run_id': run_context.get('run_id'),
        'request_recorded': bool(request),
        'gate_count': len(gates),
        'passed_gate_count': len([gate for gate in gates if gate['passed']]),
        'unmet_gate_count': len(unmet_gates),
        'unmet_gate_ids': unmet_gates,
        'critical_unmet_gate_ids': critical_unmet,
        'ready_for_real_executor_handoff': len(unmet_gates) == 0,
        'gates': gates,
        'safety_checklist': {
            'artifact_type': 'executor_safety_checklist',
            'check_count': len(checklist_items),
            'passed_check_count': len([item for item in checklist_items if item['status'] == 'passed']),
            'unmet_check_count': len([item for item in checklist_items if item['status'] != 'passed']),
            'items': checklist_items,
        },
        'preflight_contract_hardening': {
            'precheck_reference': f"artifacts/{cfg['precheck_artifact']}",
            'contract_reference': f"artifacts/{cfg['contract_artifact']}",
            'dry_run_reference': f"artifacts/{cfg['dry_run_artifact']}" if dry_run else None,
            'receipt_reference': f"artifacts/{cfg['receipt_artifact']}" if receipt else None,
            'request_reference': f"artifacts/{cfg['request_artifact']}" if request else None,
            'requires_manual_approval': True,
            'allows_real_execution_now': False,
            'execution_mode_locked': (contract or {}).get('execution_mode'),
            'auto_execution_enabled': (contract or {}).get('auto_execution_enabled'),
            'external_side_effects_allowed': (contract or {}).get('external_side_effects_allowed'),
        },
    }




def _build_environment_guard(*, task_dir: Path, target: str, closure_snapshot: dict[str, Any], contract: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = TARGETS[target]
    contract = contract or _load_json(task_dir / 'artifacts' / cfg['contract_artifact']) or {}
    run_context = get_execution_run_context(task_dir, target)
    required_inputs = [
        'task_id',
        'batch_id',
        'run_id',
        'proposal_ref',
        'approval_ref',
        'command_preview',
        'command_digest_sha256',
    ]
    if target == 'release':
        required_inputs.extend(['official_release_execution_precheck_ref', 'release_artifact_binding_ref'])
    else:
        required_inputs.extend(['rollback_execution_precheck_ref', 'rollback_registry_ref'])
    guard_checks = {
        'manual_trigger_required': True,
        'auto_execution_disabled': contract.get('auto_execution_enabled') is False,
        'dry_run_only_mode': contract.get('execution_mode') == 'dry_run_only',
        'external_side_effects_disabled': contract.get('external_side_effects_allowed') is False,
        'execution_batch_bound': bool(run_context.get('batch_id') and run_context.get('run_id')),
        'human_approval_approved': closure_snapshot.get('human_approval_state') == 'approved',
        'release_artifact_binding_ready': bool(closure_snapshot.get('release_artifact_binding_ready')),
        'rollback_supported': bool(closure_snapshot.get('rollback_supported')),
        'target_precheck_ready': bool((closure_snapshot.get('official_release_execution_precheck_ready') if target == 'release' else closure_snapshot.get('rollback_execution_precheck_ready'))),
        'zero_real_execution_artifacts': not (task_dir / 'artifacts' / cfg['forbidden_real_artifact']).exists(),
    }
    unmet = [key for key, value in guard_checks.items() if not value]
    return {
        'task_id': task_dir.name,
        'execution_target': cfg['label'],
        'guard_type': 'pre_integration_manual_only_environment_guard',
        'supported_modes': ['dry_run', 'mock_receipt', 'future_real_execute'],
        'active_mode': 'dry_run',
        'required_inputs': required_inputs,
        'forbidden_actions': [
            'automatic_real_release_execution',
            'automatic_real_rollback_execution',
            'writing_to_external_systems',
            'creating_real_release_or_rollback_registration_records',
        ],
        'external_side_effects': False,
        'real_execution_enabled': False,
        'guard_checks': guard_checks,
        'guard_ok': len(unmet) == 0,
        'unmet_guard_checks': unmet,
        'request_receipt_compatibility': {
            'request_record_type': 'controlled_execution_request',
            'receipt_record_type': 'controlled_execution_receipt',
            'required_trace_fields': ['proposal_ref', 'approval_ref', 'batch_id', 'run_id', 'command_receipt_id', 'command_digest_sha256'],
        },
        'generated_at': _now(),
    }


def _build_adapter_manifest(*, task_dir: Path, target: str) -> dict[str, Any]:
    cfg = TARGETS[target]
    closure_snapshot = load_release_closure_snapshot(task_dir)
    contract = _load_json(task_dir / 'artifacts' / cfg['contract_artifact']) or _build_contract(task_dir, target)
    environment_guard = _build_environment_guard(task_dir=task_dir, target=target, closure_snapshot=closure_snapshot, contract=contract)
    run_context = get_execution_run_context(task_dir, target)
    precheck_ref = f"artifacts/{cfg['precheck_artifact']}"
    readiness_refs = [
        'artifacts/executor_readiness_review.json',
        'artifacts/real_executor_handoff_boundary.json',
        'artifacts/execution_batch.json',
        precheck_ref,
        'artifacts/release_artifact_binding.json',
        'artifacts/execution_request_lifecycle.json',
    ]
    if target == 'rollback':
        readiness_refs.append('artifacts/rollback_registry_entry.json')
    manifest = {
        'task_id': task_dir.name,
        'record_type': 'executor_adapter_manifest',
        'execution_target': cfg['label'],
        'adapter_name': cfg['executor_name'],
        'adapter_type': 'controlled_execution_adapter',
        'adapter_interface_version': 'v1',
        'supported_modes': ['dry_run', 'mock_receipt', 'future_real_execute'],
        'current_mode': 'dry_run',
        'future_real_execute_ready': False,
        'external_side_effects': False,
        'batch_id': run_context.get('batch_id'),
        'run_id': run_context.get('run_id'),
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'contract_reference': f"artifacts/{cfg['contract_artifact']}",
        'request_reference': f"artifacts/{cfg['request_artifact']}",
        'dry_run_reference': f"artifacts/{cfg['dry_run_artifact']}",
        'receipt_reference': f"artifacts/{cfg['receipt_artifact']}",
        'handoff_reference': f"artifacts/{cfg['handoff_artifact']}",
        'operator_request_reference': f"artifacts/{cfg['operator_request_artifact']}",
        'precheck_reference': precheck_ref,
        'readiness_dependency_refs': readiness_refs,
        'required_inputs': environment_guard.get('required_inputs', []),
        'forbidden_actions': environment_guard.get('forbidden_actions', []),
        'environment_guard': environment_guard,
        'request_receipt_compatibility': {
            'request_record_type': 'controlled_execution_request',
            'receipt_record_type': 'controlled_execution_receipt',
            'protocol_schema_ref': 'artifacts/execution_receipt.schema.json',
            'compatible': True,
            'shared_trace_fields': ['proposal_ref', 'approval_ref', 'batch_id', 'run_id', 'command_receipt_id', 'command_digest_sha256'],
        },
        'zero_real_execution_assertion': {
            'real_execution_enabled': False,
            'forbidden_real_artifact': f"artifacts/{cfg['forbidden_real_artifact']}",
            'forbidden_real_artifact_present': (task_dir / 'artifacts' / cfg['forbidden_real_artifact']).exists(),
        },
        'note': 'Adapter manifest defines metadata and invocation contract only. It does not execute any release/rollback action.',
        'generated_at': _now(),
    }
    return manifest


def build_executor_adapter_artifacts(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    manager = ArtifactManager(task_dir)
    manifests = {target: _build_adapter_manifest(task_dir=task_dir, target=target) for target in ('release', 'rollback')}
    for target, manifest in manifests.items():
        manager.write_json(TARGETS[target]['adapter_manifest_artifact'], manifest)

    capability_registry = {
        'task_id': task_dir.name,
        'record_type': 'executor_capability_registry',
        'generated_at': _now(),
        'shared_policy_family': 'release_rollback_controlled_executor_policy',
        'registry_available': True,
        'adapter_manifest_refs': [f"artifacts/{TARGETS[target]['adapter_manifest_artifact']}" for target in ('release', 'rollback')],
        'adapter_count': len(manifests),
        'top_executor_adapter_types': sorted({manifest.get('adapter_type') for manifest in manifests.values() if manifest.get('adapter_type')}),
        'supported_modes_union': ['dry_run', 'future_real_execute', 'mock_receipt'],
        'environment_guard_ok_count': sum(1 for manifest in manifests.values() if (manifest.get('environment_guard') or {}).get('guard_ok')),
        'environment_guard_unmet_count': sum(len((manifest.get('environment_guard') or {}).get('unmet_guard_checks', [])) for manifest in manifests.values()),
        'external_side_effects': False,
        'targets': {
            target: {
                'execution_target': manifest.get('execution_target'),
                'adapter_type': manifest.get('adapter_type'),
                'supported_modes': manifest.get('supported_modes'),
                'current_mode': manifest.get('current_mode'),
                'future_real_execute_ready': manifest.get('future_real_execute_ready'),
                'manifest_ref': f"artifacts/{TARGETS[target]['adapter_manifest_artifact']}",
                'environment_guard_ok': (manifest.get('environment_guard') or {}).get('guard_ok'),
                'unmet_guard_checks': (manifest.get('environment_guard') or {}).get('unmet_guard_checks', []),
                'request_receipt_compatible': (manifest.get('request_receipt_compatibility') or {}).get('compatible'),
            }
            for target, manifest in manifests.items()
        },
        'note': 'Registry is shared by release/rollback and captures adapter metadata only. No external executor is called.',
    }
    manager.write_json('executor_capability_registry.json', capability_registry)

    invocation_policy = {
        'task_id': task_dir.name,
        'record_type': 'invocation_policy_review',
        'generated_at': _now(),
        'policy_scope': 'executor_adapter_invocation_contract',
        'policy_available': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'allowed_invocation_modes': ['dry_run', 'mock_receipt'],
        'disallowed_invocation_modes': ['real_execute', 'automatic_release', 'automatic_rollback'],
        'external_side_effects': False,
        'manual_trigger_required': True,
        'targets': {
            target: {
                'adapter_manifest_ref': f"artifacts/{TARGETS[target]['adapter_manifest_artifact']}",
                'request_ref': manifest.get('request_reference'),
                'receipt_ref': manifest.get('receipt_reference'),
                'precheck_ref': manifest.get('precheck_reference'),
                'environment_guard_ok': (manifest.get('environment_guard') or {}).get('guard_ok'),
                'required_inputs': manifest.get('required_inputs', []),
                'forbidden_actions': manifest.get('forbidden_actions', []),
            }
            for target, manifest in manifests.items()
        },
        'required_sequence': [
            'prepare_execution_precheck',
            'materialize_executor_contract',
            'materialize_adapter_manifest',
            'dry_run_and_mock_receipt_traceability',
            'operator_handoff_and_request_lifecycle',
            'future_manual_real_executor_integration_only_after_new_implementation',
        ],
        'request_receipt_compatibility': {
            'shared': True,
            'required_trace_fields': ['proposal_ref', 'approval_ref', 'batch_id', 'run_id', 'command_receipt_id', 'command_digest_sha256'],
        },
        'note': 'Invocation policy review documents allowed adapter usage only. Real release and rollback execution remain intentionally unimplemented.',
    }
    manager.write_json('invocation_policy_review.json', invocation_policy)
    md = [
        '# invocation policy review',
        '',
        '- policy_available: true',
        '- manual_trigger_required: true',
        '- external_side_effects: false',
        '- allowed_invocation_modes: dry_run, mock_receipt',
        '- disallowed_invocation_modes: real_execute, automatic_release, automatic_rollback',
        '- required_sequence: prepare_execution_precheck -> materialize_executor_contract -> materialize_adapter_manifest -> dry_run_and_mock_receipt_traceability -> operator_handoff_and_request_lifecycle -> future_manual_real_executor_integration_only_after_new_implementation',
    ]
    for target, manifest in manifests.items():
        guard = manifest.get('environment_guard') or {}
        md.extend([
            '',
            f"## {target}",
            f"- adapter_manifest_ref: artifacts/{TARGETS[target]['adapter_manifest_artifact']}",
            f"- adapter_type: {manifest.get('adapter_type')}",
            f"- supported_modes: {', '.join(manifest.get('supported_modes') or [])}",
            f"- environment_guard_ok: {str(bool(guard.get('guard_ok'))).lower()}",
            f"- unmet_guard_checks: {', '.join(guard.get('unmet_guard_checks') or []) if guard.get('unmet_guard_checks') else 'none'}",
            f"- request_receipt_compatible: {str(bool((manifest.get('request_receipt_compatibility') or {}).get('compatible'))).lower()}",
        ])
    manager.write_text('invocation_policy_review.md', "\n".join(md).rstrip() + "\n")
    return {
        'manifests': manifests,
        'capability_registry': capability_registry,
        'invocation_policy_review': invocation_policy,
    }


def build_future_executor_scaffold_artifacts(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    manager = ArtifactManager(task_dir)
    release_contract = _load_json(task_dir / 'artifacts' / TARGETS['release']['contract_artifact']) or _build_contract(task_dir, 'release')
    rollback_contract = _load_json(task_dir / 'artifacts' / TARGETS['rollback']['contract_artifact']) or _build_contract(task_dir, 'rollback')
    capability_registry = _load_json(task_dir / 'artifacts' / 'executor_capability_registry.json') or build_executor_adapter_artifacts(task_dir)['capability_registry']
    shared_required_trace_fields = ['proposal_ref', 'approval_ref', 'batch_id', 'run_id', 'command_receipt_id', 'command_digest_sha256']
    transcript_contract = {
        'task_id': task_dir.name,
        'record_type': 'execution_transcript_contract',
        'contract_version': 'v1',
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'shared_targets': ['official_release', 'rollback'],
        'transcript_available': True,
        'real_execution_enabled': False,
        'external_side_effects_allowed': False,
        'required_envelope_fields': ['task_id', 'execution_target', 'batch_id', 'run_id', 'plugin_name', 'plugin_version', 'invocation_mode', 'result_state', 'started_at', 'completed_at'],
        'required_trace_fields': shared_required_trace_fields,
        'required_log_fields': ['stream', 'sequence', 'level', 'message', 'emitted_at'],
        'required_error_fields': ['error_code', 'error_summary', 'retryable', 'operator_action_required'],
        'required_receipt_fields': ['receipt_state', 'command_receipt_id', 'command_digest_sha256'],
        'mock_transcript_only': True,
        'note': 'Shared transcript contract for future release/rollback plugins. Current phase allows mock transcript generation only and forbids real execution.',
        'generated_at': _now(),
    }
    manager.write_json('execution_transcript_contract.json', transcript_contract)
    manager.write_text('execution_transcript_contract.md', (
        '# execution transcript contract\n\n'
        '- contract_version: v1\n'
        '- shared_targets: official_release, rollback\n'
        '- mock_transcript_only: true\n'
        '- real_execution_enabled: false\n'
        '- external_side_effects_allowed: false\n'
        f"- required_trace_fields: {', '.join(shared_required_trace_fields)}\n"
        '- required_log_fields: stream, sequence, level, message, emitted_at\n'
        '- required_error_fields: error_code, error_summary, retryable, operator_action_required\n'
        '- note: current layer defines transcript / receipt / error reporting contract only; no real executor is called.\n'
    ))
    plugin_targets = []
    interface_payloads = {}
    no_op_payloads = {}
    for target, contract in [('release', release_contract), ('rollback', rollback_contract)]:
        cfg = TARGETS[target]
        plugin_name = f"future_{target}_executor_plugin"
        interface_payload = {
            'task_id': task_dir.name,
            'record_type': 'executor_plugin_interface',
            'plugin_name': plugin_name,
            'plugin_version': 'v1',
            'execution_target': cfg['label'],
            'shared_transcript_contract_ref': 'artifacts/execution_transcript_contract.json',
            'contract_reference': f"artifacts/{cfg['contract_artifact']}",
            'adapter_manifest_reference': f"artifacts/{cfg['adapter_manifest_artifact']}",
            'input_contract': {
                'required_fields': ['task_id', 'batch_id', 'run_id', 'proposal_ref', 'approval_ref', 'command_preview', 'command_digest_sha256'],
                'target_specific_required_fields': ['official_release_execution_precheck_ref', 'release_artifact_binding_ref'] if target == 'release' else ['rollback_execution_precheck_ref', 'rollback_registry_ref'],
                'optional_fields': ['operator_request_ref', 'handoff_packet_ref', 'environment_guard_ref'],
            },
            'output_contract': {
                'result_state_enum': ['mocked', 'validated_no_op', 'future_real_success', 'future_real_failed'],
                'required_receipt_fields': transcript_contract['required_receipt_fields'],
                'required_transcript_fields': transcript_contract['required_envelope_fields'],
                'required_error_fields': transcript_contract['required_error_fields'],
            },
            'zero_real_execution_assertion': {
                'real_execution_enabled': False,
                'external_side_effects_allowed': False,
                'mock_transcript_only': True,
            },
            'generated_at': _now(),
        }
        manager.write_json(f'{target}_executor_plugin_interface.json', interface_payload)
        interface_payloads[target] = interface_payload
        no_op_payload = {
            'task_id': task_dir.name,
            'record_type': 'no_op_executor_adapter',
            'plugin_name': plugin_name,
            'execution_target': cfg['label'],
            'adapter_mode': 'no_op_mock_transcript',
            'real_execution_enabled': False,
            'external_side_effects_allowed': False,
            'transcript_contract_ref': 'artifacts/execution_transcript_contract.json',
            'plugin_interface_ref': f'artifacts/{target}_executor_plugin_interface.json',
            'mock_transcript': {
                'task_id': task_dir.name,
                'execution_target': cfg['label'],
                'batch_id': contract.get('batch_id'),
                'run_id': contract.get('run_id'),
                'plugin_name': plugin_name,
                'plugin_version': 'v1',
                'invocation_mode': 'no_op',
                'result_state': 'mocked',
                'started_at': _now(),
                'completed_at': _now(),
                'receipt_state': 'mock_transcript_only',
                'command_receipt_id': f'mock-{target}-{str(contract.get("run_id") or "na")[-8:]}',
                'command_digest_sha256': _sha256(json.dumps({'target': target, 'run_id': contract.get('run_id'), 'mode': 'no_op'}, ensure_ascii=False, sort_keys=True)),
                'trace': {
                    'proposal_ref': f'plugin://future/{target}/proposal',
                    'approval_ref': f'plugin://future/{target}/approval',
                    'batch_id': contract.get('batch_id'),
                    'run_id': contract.get('run_id'),
                    'command_receipt_id': f'mock-{target}-{str(contract.get("run_id") or "na")[-8:]}',
                    'command_digest_sha256': _sha256(json.dumps({'target': target, 'run_id': contract.get('run_id'), 'mode': 'no_op'}, ensure_ascii=False, sort_keys=True)),
                },
                'logs': [
                    {'stream': 'stdout', 'sequence': 1, 'level': 'info', 'message': f'{plugin_name} prepared no-op transcript only', 'emitted_at': _now()},
                    {'stream': 'stdout', 'sequence': 2, 'level': 'info', 'message': 'no external system call performed', 'emitted_at': _now()},
                ],
                'error': None,
            },
            'generated_at': _now(),
        }
        manager.write_json(f'{target}_no_op_executor_adapter.json', no_op_payload)
        no_op_payloads[target] = no_op_payload
        plugin_targets.append({
            'target': target,
            'plugin_name': plugin_name,
            'interface_ref': f'artifacts/{target}_executor_plugin_interface.json',
            'no_op_adapter_ref': f'artifacts/{target}_no_op_executor_adapter.json',
            'transcript_contract_ref': 'artifacts/execution_transcript_contract.json',
        })
    review_payload = {
        'task_id': task_dir.name,
        'record_type': 'executor_plugin_review',
        'review_available': True,
        'shared_transcript_contract_ref': 'artifacts/execution_transcript_contract.json',
        'future_executor_scaffold_available': True,
        'executor_plugin_interface_available': True,
        'transcript_contract_available': True,
        'no_op_executor_available': True,
        'top_executor_plugin_targets': [item['target'] for item in plugin_targets],
        'capability_registry_ref': 'artifacts/executor_capability_registry.json',
        'targets': plugin_targets,
        'review_notes': [
            'release and rollback share one plugin boundary and one transcript contract',
            'no-op adapter returns mock transcript only',
            'real execution remains disabled and disconnected',
        ],
        'generated_at': _now(),
    }
    manager.write_json('executor_plugin_review.json', review_payload)
    manager.write_text('executor_plugin_review.md', (
        '# executor plugin review\n\n'
        '- future_executor_scaffold_available: true\n'
        '- executor_plugin_interface_available: true\n'
        '- transcript_contract_available: true\n'
        '- no_op_executor_available: true\n'
        f"- top_executor_plugin_targets: {', '.join(review_payload['top_executor_plugin_targets'])}\n"
        '- note: release / rollback share one scaffold boundary; current adapter is no-op and returns mock transcript only.\n'
    ))
    return {
        'transcript_contract': transcript_contract,
        'plugin_interfaces': interface_payloads,
        'no_op_adapters': no_op_payloads,
        'plugin_review': review_payload,
    }


def _load_execution_control_dependencies(task_dir: Path) -> dict[str, Any]:
    return {
        'readiness_review': _load_json(task_dir / 'artifacts' / 'executor_readiness_review.json') or {},
        'handoff_boundary': _load_json(task_dir / 'artifacts' / 'real_executor_handoff_boundary.json') or {},
        'release_adapter_manifest': _load_json(task_dir / 'artifacts' / TARGETS['release']['adapter_manifest_artifact']) or {},
        'rollback_adapter_manifest': _load_json(task_dir / 'artifacts' / TARGETS['rollback']['adapter_manifest_artifact']) or {},
        'capability_registry': _load_json(task_dir / 'artifacts' / 'executor_capability_registry.json') or {},
        'invocation_policy': _load_json(task_dir / 'artifacts' / 'invocation_policy_review.json') or {},
        'simulated_executor_run': _load_json(task_dir / 'artifacts' / 'simulated_executor_run.json') or {},
        'contract_compliance_matrix': _load_json(task_dir / 'artifacts' / 'contract_compliance_matrix.json') or {},
        'executor_integration_rehearsal': _load_json(task_dir / 'artifacts' / 'executor_integration_rehearsal.json') or {},
        'future_release_plugin_interface': _load_json(task_dir / 'artifacts' / 'release_executor_plugin_interface.json') or {},
        'future_rollback_plugin_interface': _load_json(task_dir / 'artifacts' / 'rollback_executor_plugin_interface.json') or {},
        'execution_transcript_contract': _load_json(task_dir / 'artifacts' / 'execution_transcript_contract.json') or {},
        'executor_plugin_review': _load_json(task_dir / 'artifacts' / 'executor_plugin_review.json') or {},
        'release_no_op_adapter': _load_json(task_dir / 'artifacts' / 'release_no_op_executor_adapter.json') or {},
        'rollback_no_op_adapter': _load_json(task_dir / 'artifacts' / 'rollback_no_op_executor_adapter.json') or {},
        'executor_conformance_matrix': _load_json(task_dir / 'artifacts' / 'executor_conformance_matrix.json') or {},
        'executor_error_contract': _load_json(task_dir / 'artifacts' / 'executor_error_contract.json') or {},
        'release_rollback_parity_matrix': _load_json(task_dir / 'artifacts' / 'release_rollback_parity_matrix.json') or {},
        'future_executor_implementation_blueprint': _load_json(task_dir / 'artifacts' / 'future_executor_implementation_blueprint.json') or {},
        'rollout_gate_registry': _load_json(task_dir / 'artifacts' / 'rollout_gate_registry.json') or {},
        'waiver_exception_registry': _load_json(task_dir / 'artifacts' / 'waiver_exception_registry.json') or {},
        'executor_admission_review': _load_json(task_dir / 'artifacts' / 'executor_admission_review.json') or {},
        'go_no_go_decision_pack': _load_json(task_dir / 'artifacts' / 'go_no_go_decision_pack.json') or {},
    }


def build_executor_contract_artifacts(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    manager = ArtifactManager(task_dir)
    deps = _load_execution_control_dependencies(task_dir)
    release_contract = _load_json(task_dir / 'artifacts' / TARGETS['release']['contract_artifact']) or {}
    rollback_contract = _load_json(task_dir / 'artifacts' / TARGETS['rollback']['contract_artifact']) or {}
    release_request = _load_json(task_dir / 'artifacts' / TARGETS['release']['request_artifact']) or {}
    rollback_request = _load_json(task_dir / 'artifacts' / TARGETS['rollback']['request_artifact']) or {}
    release_handoff = _load_json(task_dir / 'artifacts' / TARGETS['release']['handoff_artifact']) or {}
    rollback_handoff = _load_json(task_dir / 'artifacts' / TARGETS['rollback']['handoff_artifact']) or {}
    release_receipt = _load_json(task_dir / 'artifacts' / TARGETS['release']['receipt_artifact']) or {}
    rollback_receipt = _load_json(task_dir / 'artifacts' / TARGETS['rollback']['receipt_artifact']) or {}
    release_dry_run = _load_json(task_dir / 'artifacts' / TARGETS['release']['dry_run_artifact']) or {}
    rollback_dry_run = _load_json(task_dir / 'artifacts' / TARGETS['rollback']['dry_run_artifact']) or {}
    release_precheck = _load_json(task_dir / 'artifacts' / TARGETS['release']['precheck_artifact']) or {}
    rollback_precheck = _load_json(task_dir / 'artifacts' / TARGETS['rollback']['precheck_artifact']) or {}
    readiness_review = deps['readiness_review']
    handoff_boundary = deps['handoff_boundary']
    transcript_contract = deps['execution_transcript_contract']
    release_plugin = deps['future_release_plugin_interface']
    rollback_plugin = deps['future_rollback_plugin_interface']
    release_manifest = deps['release_adapter_manifest']
    rollback_manifest = deps['rollback_adapter_manifest']
    release_no_op = deps['release_no_op_adapter']
    rollback_no_op = deps['rollback_no_op_adapter']
    contract_compliance = deps['contract_compliance_matrix']
    integration_rehearsal = deps['executor_integration_rehearsal']

    target_specs = [
        ('release', 'official_release', release_contract, release_request, release_handoff, release_receipt, release_dry_run, release_precheck, release_plugin, release_manifest, release_no_op, ['official_release_execution_precheck_ref', 'release_artifact_binding_ref']),
        ('rollback', 'rollback', rollback_contract, rollback_request, rollback_handoff, rollback_receipt, rollback_dry_run, rollback_precheck, rollback_plugin, rollback_manifest, rollback_no_op, ['rollback_execution_precheck_ref', 'rollback_registry_ref']),
    ]
    shared_requirements = [
        ('request_ref_present', 'execution request artifact linked'),
        ('handoff_packet_ref_present', 'handoff packet linked'),
        ('adapter_manifest_ref_present', 'adapter manifest linked'),
        ('plugin_interface_ref_present', 'plugin interface linked'),
        ('transcript_contract_ref_present', 'transcript contract linked'),
        ('precheck_ref_present', 'precheck artifact linked'),
        ('dry_run_ref_present', 'dry-run result linked'),
        ('receipt_ref_present', 'receipt artifact linked'),
        ('run_trace_consistent', 'batch_id/run_id trace consistent across request, contract, handoff, receipt'),
        ('side_effects_reported', 'side-effect reporting explicitly states zero external writes'),
        ('error_contract_addressable', 'error contract can address this target'),
        ('zero_real_execution_enforced', 'real execution remains disabled'),
    ]
    conformance_targets=[]
    missing_counter=Counter()
    for target_key,label,contract,request,handoff,receipt,dry_run,precheck,plugin,manifest,no_op,target_specific in target_specs:
        batch_id = contract.get('batch_id') or request.get('batch_id') or handoff.get('batch_id') or receipt.get('batch_id')
        run_id = contract.get('run_id') or request.get('run_id') or handoff.get('run_id') or receipt.get('run_id')
        trace = receipt.get('receipt_trace') or {}
        checks = {
            'request_ref_present': bool(request),
            'handoff_packet_ref_present': bool(handoff),
            'adapter_manifest_ref_present': bool(manifest),
            'plugin_interface_ref_present': bool(plugin),
            'transcript_contract_ref_present': bool(transcript_contract),
            'precheck_ref_present': bool(precheck),
            'dry_run_ref_present': bool(dry_run),
            'receipt_ref_present': bool(receipt),
            'run_trace_consistent': bool(batch_id and run_id) and batch_id == request.get('batch_id') == contract.get('batch_id') == receipt.get('batch_id') == dry_run.get('batch_id') and run_id == request.get('run_id') == contract.get('run_id') == receipt.get('run_id') == dry_run.get('run_id') and (handoff.get('run_context') or {}).get('batch_id') == batch_id and (handoff.get('run_context') or {}).get('run_id') == run_id and trace.get('batch_id') == batch_id and trace.get('run_id') == run_id,
            'side_effects_reported': int(dry_run.get('side_effect_count', 0) or 0) == 0 and list(dry_run.get('side_effects_performed') or []) == [] and manifest.get('external_side_effects') is False and no_op.get('external_side_effects_allowed') is False,
            'error_contract_addressable': True,
            'zero_real_execution_enforced': contract.get('auto_execution_enabled') is False and contract.get('external_side_effects_allowed') is False and manifest.get('external_side_effects') is False and no_op.get('real_execution_enabled') is False,
        }
        missing = [req_id for req_id,_ in shared_requirements if not checks[req_id]]
        for item in missing:
            missing_counter[item]+=1
        conformance_targets.append({
            'execution_target': label,
            'conformance_passed': not missing,
            'required_plugin_fields': list((plugin.get('input_contract') or {}).get('required_fields') or []),
            'target_specific_required_fields': list((plugin.get('input_contract') or {}).get('target_specific_required_fields') or target_specific),
            'required_transcript_fields': list((transcript_contract.get('required_envelope_fields') or [])),
            'required_receipt_fields': list((transcript_contract.get('required_receipt_fields') or [])),
            'requirements': [{'requirement_id': req_id,'description': desc,'status': 'pass' if checks[req_id] else 'gap'} for req_id,desc in shared_requirements],
            'missing_contracts': missing,
            'evidence_refs': [
                f"artifacts/{TARGETS[target_key]['contract_artifact']}",
                f"artifacts/{TARGETS[target_key]['request_artifact']}",
                f"artifacts/{TARGETS[target_key]['handoff_artifact']}",
                f"artifacts/{TARGETS[target_key]['receipt_artifact']}",
                f"artifacts/{TARGETS[target_key]['dry_run_artifact']}",
                f"artifacts/{TARGETS[target_key]['precheck_artifact']}",
                f"artifacts/{target_key}_executor_plugin_interface.json",
                'artifacts/execution_transcript_contract.json',
            ],
        })
    top_missing = [{'gap_id': gap,'count': count} for gap,count in sorted(missing_counter.items(), key=lambda x:(-x[1],x[0]))[:8]]
    conformance_payload = {
        'task_id': task_dir.name, 'record_type': 'executor_conformance_matrix', 'generated_at': _now(),
        'executor_conformance_available': True, 'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'zero_real_execution_required': True, 'requirement_count': len(shared_requirements), 'target_count': len(conformance_targets),
        'pass_count': sum(1 for t in conformance_targets if t['conformance_passed']), 'fail_count': sum(1 for t in conformance_targets if not t['conformance_passed']),
        'top_missing_executor_contracts': top_missing, 'targets': conformance_targets,
        'refs': {'contract_compliance_matrix':'artifacts/contract_compliance_matrix.json','executor_integration_rehearsal':'artifacts/executor_integration_rehearsal.json','executor_readiness_review':'artifacts/executor_readiness_review.json','real_executor_handoff_boundary':'artifacts/real_executor_handoff_boundary.json'}
    }
    manager.write_json('executor_conformance_matrix.json', conformance_payload)
    manager.write_text('executor_conformance_matrix.md', (
        '# executor conformance matrix\n\n'
        + '\n'.join([
            '- executor_conformance_available: true',
            f"- pass_count: {conformance_payload['pass_count']}",
            f"- fail_count: {conformance_payload['fail_count']}",
            f"- top_missing_executor_contracts: {', '.join([i['gap_id'] for i in top_missing]) if top_missing else 'none'}",
            '- note: future real executor must satisfy these interface contracts before any non-no-op integration.',
        ] + [
            f"\n## {item['execution_target']}\n" + '\n'.join([f"- {req['requirement_id']}: {req['status']}" for req in item['requirements']])
            for item in conformance_targets
        ])
        + '\n'
    ))

    error_codes = [
        {'error_code':'ENVIRONMENT_GUARD_UNMET','retryable':False,'operator_action_required':True,'severity':'blocker','applies_to':['official_release','rollback']},
        {'error_code':'READINESS_GATE_UNMET','retryable':False,'operator_action_required':True,'severity':'blocker','applies_to':['official_release','rollback']},
        {'error_code':'REQUEST_EXPIRED','retryable':True,'operator_action_required':True,'severity':'warning','applies_to':['official_release','rollback']},
        {'error_code':'RECEIPT_CORRELATION_MISMATCH','retryable':False,'operator_action_required':True,'severity':'blocker','applies_to':['official_release','rollback']},
        {'error_code':'TRANSCRIPT_CONTRACT_VIOLATION','retryable':False,'operator_action_required':False,'severity':'blocker','applies_to':['official_release','rollback']},
        {'error_code':'NO_OP_ONLY_PHASE','retryable':False,'operator_action_required':False,'severity':'info','applies_to':['official_release','rollback']},
        {'error_code':'RELEASE_BINDING_MISSING','retryable':False,'operator_action_required':True,'severity':'blocker','applies_to':['official_release']},
        {'error_code':'ROLLBACK_REGISTRY_MISSING','retryable':False,'operator_action_required':True,'severity':'blocker','applies_to':['rollback']},
    ]
    error_payload = {
        'task_id': task_dir.name, 'record_type': 'executor_error_contract', 'generated_at': _now(),
        'executor_error_contract_available': True, 'shared_transcript_contract_ref':'artifacts/execution_transcript_contract.json',
        'shared_receipt_schema_ref':'artifacts/execution_receipt.schema.json',
        'required_error_fields': list(transcript_contract.get('required_error_fields') or []),
        'required_side_effect_report_fields': ['external_side_effects','side_effects_summary','touched_resources','writes_performed'],
        'required_error_envelope': ['error_code','error_summary','retryable','operator_action_required','severity','execution_target','batch_id','run_id'],
        'error_codes': error_codes,
        'error_code_count': len(error_codes),
        'refs': {'release_receipt':'artifacts/official_release_execution_receipt.json','rollback_receipt':'artifacts/rollback_execution_receipt.json','release_no_op_adapter':'artifacts/release_no_op_executor_adapter.json','rollback_no_op_adapter':'artifacts/rollback_no_op_executor_adapter.json'}
    }
    manager.write_json('executor_error_contract.json', error_payload)
    manager.write_text('executor_error_contract.md', (
        '# executor error contract\n\n'
        + '\n'.join([
            '- executor_error_contract_available: true',
            f"- error_code_count: {len(error_codes)}",
            f"- required_error_fields: {', '.join(error_payload['required_error_fields'])}",
            '- required_side_effect_report_fields: external_side_effects, side_effects_summary, touched_resources, writes_performed',
            '- note: future real executor errors must normalize to this envelope; current phase remains dry-run/no-op only.',
        ] + [
            f"- {item['error_code']}: retryable={str(item['retryable']).lower()}, operator_action_required={str(item['operator_action_required']).lower()}, targets={','.join(item['applies_to'])}"
            for item in error_codes
        ])
        + '\n'
    ))

    parity_axes = [
        ('request_envelope','must_match','same request envelope shape and trace fields'),
        ('handoff_packet','must_match','same handoff packet / command plan traceability contract'),
        ('adapter_manifest','must_match','same adapter manifest and environment guard model'),
        ('transcript_contract','must_match','same transcript and receipt envelope'),
        ('error_contract','must_match','same normalized error envelope'),
        ('target_specific_precheck','target_specific','release uses artifact binding, rollback uses rollback registry'),
        ('command_preview','target_specific','actual command preview may differ by target'),
        ('receipt_target_metadata','target_specific','receipt may carry release-only or rollback-only metadata'),
    ]
    parity_rows=[]; gaps=[]
    for axis,mode,desc in parity_axes:
        aligned = True
        if axis=='target_specific_precheck':
            aligned = bool(release_plugin) and bool(rollback_plugin)
        elif axis=='command_preview':
            aligned = bool((release_handoff.get('command_plan') or {}).get('steps')) and bool((rollback_handoff.get('command_plan') or {}).get('steps'))
        elif axis=='receipt_target_metadata':
            aligned = bool(release_receipt) and bool(rollback_receipt)
        else:
            aligned = bool(release_contract and rollback_contract and transcript_contract)
        if not aligned:
            gaps.append(axis)
        parity_rows.append({'capability_axis':axis,'parity_mode':mode,'description':desc,'aligned':aligned})
    parity_payload = {
        'task_id':task_dir.name,
        'record_type':'release_rollback_parity_matrix',
        'generated_at':_now(),
        'release_rollback_parity_available':True,
        'shared_rule_family':'release_rollback_controlled_executor_policy',
        'parity_gaps':gaps,
        'axis_count':len(parity_rows),
        'targets':['official_release','rollback'],
        'axes':parity_rows,
        'refs':{'release_plugin':'artifacts/release_executor_plugin_interface.json','rollback_plugin':'artifacts/rollback_executor_plugin_interface.json','release_contract':'artifacts/release_executor_contract.json','rollback_contract':'artifacts/rollback_executor_contract.json','transcript_contract':'artifacts/execution_transcript_contract.json','error_contract':'artifacts/executor_error_contract.json'}
    }
    manager.write_json('release_rollback_parity_matrix.json', parity_payload)
    manager.write_text('release_rollback_parity_matrix.md', (
        '# release rollback parity matrix\n\n'
        + '\n'.join([
            '- release_rollback_parity_available: true',
            f"- parity_gaps: {', '.join(gaps) if gaps else 'none'}",
            '- must_match axes: request_envelope, handoff_packet, adapter_manifest, transcript_contract, error_contract',
            '- target_specific axes: target_specific_precheck, command_preview, receipt_target_metadata',
        ] + [
            f"- {row['capability_axis']}: {'aligned' if row['aligned'] else 'gap'} ({row['parity_mode']})"
            for row in parity_rows
        ])
        + '\n'
    ))

    blueprint_targets=[]
    for target_key,label,contract,request,handoff,receipt,dry_run,precheck,plugin,manifest,no_op,target_specific in target_specs:
        blueprint_targets.append({
            'execution_target': label,
            'implementation_status': 'blueprint_only',
            'must_reuse_refs': {
                'contract': f"artifacts/{TARGETS[target_key]['contract_artifact']}",
                'adapter_manifest': f"artifacts/{TARGETS[target_key]['adapter_manifest_artifact']}",
                'operator_request': f"artifacts/{TARGETS[target_key]['operator_request_artifact']}",
                'handoff_packet': f"artifacts/{TARGETS[target_key]['handoff_artifact']}",
                'receipt': f"artifacts/{TARGETS[target_key]['receipt_artifact']}",
                'dry_run': f"artifacts/{TARGETS[target_key]['dry_run_artifact']}",
                'precheck': f"artifacts/{TARGETS[target_key]['precheck_artifact']}",
                'plugin_interface': f"artifacts/{target_key}_executor_plugin_interface.json",
            },
            'required_implementation_steps': [
                'implement adapter invoke() behind existing plugin interface',
                'preserve batch_id/run_id/proposal_ref/approval_ref traceability',
                'emit transcript envelope before, during, and after command execution',
                'emit normalized receipt and error payloads with side-effect report',
                'respect invocation policy / environment guard / readiness gates before any external call',
                'keep no-op fallback path available for rehearsal and validation',
            ],
            'target_specific_notes': ['bind release artifact set before execution'] if target_key=='release' else ['bind rollback registry entry before execution'],
            'real_execution_forbidden_until': ['executor_admission_review overall_admission_state=ready_for_future_executor','go_no_go_decision_pack overall_decision=go','manual operator approval recorded outside this blueprint layer'],
        })
    blueprint_payload={
        'task_id':task_dir.name,
        'record_type':'future_executor_implementation_blueprint',
        'generated_at':_now(),
        'implementation_blueprint_available':True,
        'blueprint_state':'blueprint_only_no_real_execution',
        'zero_real_execution_required':True,
        'shared_rule_family':'release_rollback_controlled_executor_policy',
        'shared_dependencies':{'executor_readiness_review':'artifacts/executor_readiness_review.json','real_executor_handoff_boundary':'artifacts/real_executor_handoff_boundary.json','executor_conformance_matrix':'artifacts/executor_conformance_matrix.json','executor_error_contract':'artifacts/executor_error_contract.json','release_rollback_parity_matrix':'artifacts/release_rollback_parity_matrix.json','contract_compliance_matrix':'artifacts/contract_compliance_matrix.json','executor_integration_rehearsal':'artifacts/executor_integration_rehearsal.json'},
        'shared_principles':['do not write to external systems during this blueprint stage','release and rollback must keep one normalized receipt/transcript/error contract','all future executors must preserve request/handoff/receipt correlation IDs','all real execution paths must remain behind existing readiness/admission/go-no-go controls'],
        'targets':blueprint_targets
    }
    delivery_backlog_items=[]
    ownership_split_items=[]
    blocker_items=[]
    acceptance_test_items=[]
    shared_blocker_ids=[]
    shared_references={
        'executor_readiness_review':'artifacts/executor_readiness_review.json',
        'executor_admission_review':'artifacts/executor_admission_review.json',
        'go_no_go_decision_pack':'artifacts/go_no_go_decision_pack.json',
        'executor_conformance_matrix':'artifacts/executor_conformance_matrix.json',
        'executor_error_contract':'artifacts/executor_error_contract.json',
        'release_rollback_parity_matrix':'artifacts/release_rollback_parity_matrix.json',
        'future_executor_implementation_blueprint':'artifacts/future_executor_implementation_blueprint.json',
        'real_executor_delivery_backlog':'artifacts/real_executor_delivery_backlog.json',
        'executor_acceptance_test_pack':'artifacts/executor_acceptance_test_pack.json',
        'executor_ownership_split':'artifacts/executor_ownership_split.json',
        'executor_blocker_matrix':'artifacts/executor_blocker_matrix.json',
        'executor_cutover_readiness_pack':'artifacts/executor_cutover_readiness_pack.json',
        'real_executor_integration_checklist':'artifacts/real_executor_integration_checklist.json',
        'executor_risk_register':'artifacts/executor_risk_register.json',
        'future_executor_handoff_summary':'artifacts/future_executor_handoff_summary.json',
    }
    module_templates=[
        ('transport_adapter_body','实现真实执行 transport / invoke 适配器本体','critical','must_unblock_first','coder','在现有 plugin interface 后实现真实 invoke()，但不得绕过人工审批与 go/no-go。',['plugin interface frozen','environment guard contract reviewed','zero real execution validation pack available'],['new adapter wired behind existing plugin interface','no-op fallback preserved','external side effects remain disabled in this pack'],['artifacts/{target_key}_executor_plugin_interface.json','artifacts/future_executor_implementation_blueprint.json']),
        ('command_builder','实现命令/步骤编排与参数注入模块','high','can_start_now','coder','把 handoff packet / command plan 映射为真实执行器输入，保持 step traceability。',['handoff packet contract available','command plan traceability available'],['command builder reproduces every planned step','proposal_ref/approval_ref/batch_id/run_id carried through'],['artifacts/{target_key}_executor_handoff_packet.json','artifacts/{target_key}_operator_execution_request.json']),
        ('preflight_guard','实现真实外呼前的 preflight/guard 复核模块','critical','must_unblock_first','test-expert','在真实外呼前复用 readiness/admission/go-no-go / environment guard。',['executor readiness review available','executor admission review available','go/no-go decision pack available'],['guard execution blocks when any prerequisite is unmet','waiver handling unchanged','zero bypass evidence captured'],['artifacts/executor_readiness_review.json','artifacts/executor_admission_review.json','artifacts/go_no_go_decision_pack.json']),
        ('receipt_transcript_bridge','实现 transcript / receipt / side-effect report 归一化桥接','high','can_start_now','doc-manager','把真实执行细节归一到现有 transcript / receipt / error contract。',['transcript contract available','receipt contract available','error contract available'],['normalized receipt matches existing schema','transcript stages emitted before/during/after execution','side-effect report included'],['artifacts/execution_transcript_contract.json','artifacts/{receipt_artifact}','artifacts/executor_error_contract.json']),
        ('error_mapping','实现真实错误到标准错误契约的映射模块','high','can_start_now','test-expert','把底层异常转换为既有 executor_error_contract。',['executor error contract available','conformance matrix available'],['every critical failure path maps to normalized error payload','retryable vs terminal errors classified'],['artifacts/executor_error_contract.json','artifacts/executor_conformance_matrix.json']),
        ('rollback_parity_hooks','实现 release/rollback 共用的 parity hook 与能力对齐层','high','can_start_now','coder','保证 release / rollback 复用同一套 implementation pack 规则。',['release rollback parity matrix available','shared rule family frozen'],['parity matrix remains gap-free for shared hooks','shared rule family identifiers preserved'],['artifacts/release_rollback_parity_matrix.json','artifacts/future_executor_implementation_blueprint.json']),
        ('acceptance_replay_harness','扩展真实执行器验收回放/准入测试挂钩','medium','can_start_now','test-expert','为未来真实执行器补齐 acceptance test pack 的自动化挂钩，但当前仅做回放/仿真。',['acceptance test pack available','simulation harness available','integration rehearsal available'],['all acceptance cases runnable in replay/simulated mode','no external write path opened by tests'],['artifacts/executor_acceptance_test_pack.json','artifacts/executor_integration_rehearsal.json','artifacts/contract_compliance_matrix.json']),
    ]
    target_module_notes={'release':['bind release artifact set before execution','support release-specific command plan materialization'],'rollback':['bind rollback registry entry before execution','support rollback-specific recovery command plan materialization']}
    target_blockers={
        'release':[
            ('release_real_executor_missing','真实正式发布执行器本体缺失','critical','must_unblock_first','coder','实现正式发布 invoke() 本体前，真实 cutover 不可开始。',['artifacts/release_executor_plugin_interface.json','artifacts/future_executor_implementation_blueprint.json']),
            ('release_environment_credentials_unbound','正式发布真实环境凭据/目标未受控绑定','high','must_unblock_first','ops-monitor','真实环境信息未进入受控绑定前，禁止接入正式发布执行器。',['artifacts/release_executor_adapter_manifest.json','artifacts/real_executor_handoff_boundary.json']),
            ('release_cutover_signoff_pending','正式发布 cutover 人工签字未完成','high','must_unblock_first','doc-manager','未来真实启用前仍需新的人工切换签字。',['artifacts/executor_cutover_readiness_pack.json','artifacts/future_executor_handoff_summary.json']),
        ],
        'rollback':[
            ('rollback_real_executor_missing','真实回滚执行器本体缺失','critical','must_unblock_first','coder','实现回滚 invoke() 本体前，真实 rollback 不可开始。',['artifacts/rollback_executor_plugin_interface.json','artifacts/future_executor_implementation_blueprint.json']),
            ('rollback_environment_credentials_unbound','回滚真实环境凭据/目标未受控绑定','high','must_unblock_first','ops-monitor','真实回滚目标/权限未进入受控绑定前，禁止接入回滚执行器。',['artifacts/rollback_executor_adapter_manifest.json','artifacts/real_executor_handoff_boundary.json']),
            ('rollback_cutover_signoff_pending','回滚 cutover 人工签字未完成','high','must_unblock_first','doc-manager','未来真实启用前仍需新的回滚切换签字。',['artifacts/executor_cutover_readiness_pack.json','artifacts/future_executor_handoff_summary.json']),
        ],
    }
    target_acceptance_cases={
        'release':['release_real_adapter_wires_plugin_interface','release_receipt_and_transcript_parity','release_guard_blocking_on_failed_gates'],
        'rollback':['rollback_real_adapter_wires_plugin_interface','rollback_receipt_and_transcript_parity','rollback_guard_blocking_on_failed_gates'],
    }
    manager.write_json('future_executor_implementation_blueprint.json', blueprint_payload)
    manager.write_text('future_executor_implementation_blueprint.md', (
        '# future executor implementation blueprint\n\n'
        + '\n'.join([
            '- implementation_blueprint_available: true',
            '- blueprint_state: blueprint_only_no_real_execution',
            '- zero_real_execution_required: true',
            '- note: this blueprint constrains future implementation; it does not implement a real release or rollback executor.',
        ] + [
            f"\n## {item['execution_target']}\n" + '\n'.join([f"- {step}" for step in item['required_implementation_steps']])
            for item in blueprint_targets
        ])
        + '\n'
    ))

    admission_review = deps['executor_admission_review']
    go_no_go_pack = deps['go_no_go_decision_pack']
    rollout_gate_registry = deps['rollout_gate_registry']
    waiver_exception_registry = deps['waiver_exception_registry']
    target_status_map = {item['execution_target']: item for item in conformance_targets}
    target_ready_map = readiness_review.get('targets', {}) or {}
    target_admission_map = admission_review.get('targets', {}) or {}
    target_decision_map = go_no_go_pack.get('targets', {}) or {}
    for target_key, label, _contract, _request, _handoff, _receipt, _dry_run, _precheck, _plugin, _manifest, _no_op, _target_specific in target_specs:
        receipt_artifact = TARGETS[target_key]['receipt_artifact']
        execution_target = 'official_release' if target_key == 'release' else 'rollback'
        for module_id, title, risk_level, blocker_state, owner_role, description, prerequisites, acceptance_criteria, evidence_refs in module_templates:
            item_id = f'{target_key}_{module_id}'
            delivery_backlog_items.append({
                'item_id': item_id,
                'execution_target': execution_target,
                'module_id': module_id,
                'title': title,
                'status': 'ready_for_future_implementation' if blocker_state == 'can_start_now' else 'blocked_until_prereqs_cleared',
                'implementation_status': 'not_implemented_here',
                'risk_level': risk_level,
                'blocker_state': blocker_state,
                'recommended_owner': owner_role,
                'description': description,
                'prerequisites': prerequisites,
                'acceptance_criteria': acceptance_criteria + target_module_notes[target_key],
                'evidence_refs': [ref.format(target_key=target_key, receipt_artifact=receipt_artifact) for ref in evidence_refs],
            })
        ownership_split_items.extend([
            {
                'split_id': f'{target_key}_coder_impl',
                'execution_target': execution_target,
                'workstream': 'real_executor_body_implementation',
                'recommended_owner': 'coder',
                'responsibility': '实现真实 adapter body / command builder / parity hooks，不改变人工审批边界。',
                'handoff_inputs': [f'artifacts/{target_key}_executor_plugin_interface.json', f'artifacts/{target_key}_executor_handoff_packet.json', 'artifacts/future_executor_implementation_blueprint.json'],
                'handoff_outputs': [f'{target_key}_real_executor_body', f'{target_key}_adapter_invoke_tests'],
            },
            {
                'split_id': f'{target_key}_test_acceptance',
                'execution_target': execution_target,
                'workstream': 'acceptance_and_conformance_validation',
                'recommended_owner': 'test-expert',
                'responsibility': '执行 acceptance / conformance / rehearsal / error mapping 验证，确认零越权执行。',
                'handoff_inputs': ['artifacts/executor_acceptance_test_pack.json', 'artifacts/executor_conformance_matrix.json', 'artifacts/executor_error_contract.json'],
                'handoff_outputs': [f'{target_key}_acceptance_report', f'{target_key}_conformance_report'],
            },
            {
                'split_id': f'{target_key}_ops_cutover',
                'execution_target': execution_target,
                'workstream': 'environment_binding_and_cutover_signoff',
                'recommended_owner': 'ops-monitor',
                'responsibility': '受控绑定真实环境/凭据/切换窗口，并维持不自动执行。',
                'handoff_inputs': [f'artifacts/{target_key}_executor_adapter_manifest.json', 'artifacts/executor_cutover_readiness_pack.json', 'artifacts/future_executor_handoff_summary.json'],
                'handoff_outputs': [f'{target_key}_environment_binding_review', f'{target_key}_manual_cutover_signoff'],
            },
        ])
        for blocker_id, title, severity, blocker_state, owner_role, description, evidence_refs in target_blockers[target_key]:
            shared_blocker_ids.append(blocker_id)
            blocker_items.append({
                'blocker_id': blocker_id,
                'execution_target': execution_target,
                'title': title,
                'severity': severity,
                'blocker_state': blocker_state,
                'recommended_owner': owner_role,
                'status': 'open',
                'description': description,
                'must_clear_before_real_execution': blocker_state == 'must_unblock_first',
                'evidence_refs': evidence_refs,
            })
        acceptance_test_items.extend([
            {
                'case_id': f'{target_key}_real_adapter_wires_plugin_interface',
                'execution_target': execution_target,
                'test_type': 'interface_acceptance',
                'status': 'pending_real_executor_body',
                'recommended_owner': 'test-expert',
                'preconditions': ['real executor body implemented in sandbox/test harness', 'plugin interface unchanged', 'manual cutover still disabled'],
                'steps': ['load plugin interface contract', 'invoke adapter in simulated/replay mode', 'verify transcript/receipt correlation ids are preserved'],
                'acceptance_criteria': ['adapter invoke path callable behind existing plugin interface', 'no direct external write performed during acceptance run', 'receipt/transcript/error artifacts remain schema-compatible'],
                'evidence_refs': [f'artifacts/{target_key}_executor_plugin_interface.json', 'artifacts/execution_transcript_contract.json', 'artifacts/executor_error_contract.json'],
            },
            {
                'case_id': f'{target_key}_receipt_and_transcript_parity',
                'execution_target': execution_target,
                'test_type': 'traceability_acceptance',
                'status': 'pending_real_executor_body',
                'recommended_owner': 'test-expert',
                'preconditions': ['real adapter body implemented', 'receipt bridge implemented'],
                'steps': ['execute replay fixture', 'compare receipt/transcript against normalized contract', 'validate batch_id/run_id/proposal_ref/approval_ref propagation'],
                'acceptance_criteria': ['traceability fields preserved end-to-end', 'side-effect report normalized', 'error payload compatible with executor_error_contract'],
                'evidence_refs': [f'artifacts/{receipt_artifact}', 'artifacts/executor_conformance_matrix.json', 'artifacts/release_rollback_parity_matrix.json'],
            },
            {
                'case_id': f'{target_key}_guard_blocking_on_failed_gates',
                'execution_target': execution_target,
                'test_type': 'guardrail_acceptance',
                'status': 'pending_real_executor_body',
                'recommended_owner': 'test-expert',
                'preconditions': ['preflight guard module implemented', 'readiness/admission/go-no-go fixtures available'],
                'steps': ['force readiness or admission failure in fixture', 'attempt invoke()', 'verify execution is blocked and transcript shows guard refusal'],
                'acceptance_criteria': ['real adapter does not execute when any blocking gate fails', 'guard refusal is auditable', 'manual override absent by default'],
                'evidence_refs': ['artifacts/executor_readiness_review.json', 'artifacts/executor_admission_review.json', 'artifacts/go_no_go_decision_pack.json'],
            },
        ])
    top_risks = [
        {
            'risk_id': 'real_release_executor_missing',
            'title': '真实正式发布执行器本体未实现',
            'severity': 'critical',
            'status': 'open_blocker',
            'applies_to': ['official_release'],
        },
        {
            'risk_id': 'real_rollback_executor_missing',
            'title': '真实回滚执行器本体未实现',
            'severity': 'critical',
            'status': 'open_blocker',
            'applies_to': ['rollback'],
        },
        {
            'risk_id': 'external_side_effect_control_breach',
            'title': '未来真实接入若绕过现有门禁，可能破坏零副作用边界',
            'severity': 'high',
            'status': 'managed_by_contracts',
            'applies_to': ['official_release', 'rollback'],
        },
        {
            'risk_id': 'traceability_contract_regression',
            'title': 'batch_id / run_id / proposal_ref / approval_ref 链路回归',
            'severity': 'high',
            'status': 'managed_by_contracts',
            'applies_to': ['official_release', 'rollback'],
        },
    ]
    shared_blockers = [
        'real_release_executor_missing',
        'real_rollback_executor_missing',
        'credential_target_binding_unresolved',
        'cutover_signoff_pending',
    ]
    checklist_items = []
    for target_key, label, *_rest in target_specs:
        readiness_target = target_ready_map.get(target_key, {}) or {}
        admission_target = target_admission_map.get(target_key, {}) or {}
        decision_target = target_decision_map.get(target_key, {}) or {}
        conformance_target = target_status_map.get(label, {}) or {}
        checklist_items.extend([
            {
                'check_id': f'{target_key}_reuse_existing_contract_bundle',
                'title': f'{label}: 复用既有 contract / request / handoff / receipt / transcript 契约',
                'status': 'passed' if conformance_target.get('conformance_passed') else 'pending',
                'blocking': True,
                'evidence_refs': list(conformance_target.get('evidence_refs') or []),
            },
            {
                'check_id': f'{target_key}_readiness_and_admission_locked',
                'title': f'{label}: readiness / admission / go-no-go 保持可回放',
                'status': 'passed' if readiness_target.get('ready_for_real_executor_handoff') and admission_target.get('ready_for_future_executor') and decision_target.get('decision') == 'go' else 'pending',
                'blocking': True,
                'evidence_refs': ['artifacts/executor_readiness_review.json', 'artifacts/executor_admission_review.json', 'artifacts/go_no_go_decision_pack.json'],
            },
            {
                'check_id': f'{target_key}_implement_real_adapter_body',
                'title': f'{label}: 实现真实执行器 invoke() 本体（当前未实现）',
                'status': 'pending',
                'blocking': True,
                'evidence_refs': [f"artifacts/{target_key}_executor_plugin_interface.json", 'artifacts/future_executor_implementation_blueprint.json'],
            },
            {
                'check_id': f'{target_key}_credential_and_target_binding',
                'title': f'{label}: 完成凭据 / 目标受控绑定',
                'status': 'pending',
                'blocking': True,
                'evidence_refs': ['artifacts/executor_credential_binding_policy.json', 'artifacts/executor_target_binding_registry.json'],
            },
            {
                'check_id': f'{target_key}_manual_cutover_signoff',
                'title': f'{label}: 完成 cutover 人工签字与切换窗口确认',
                'status': 'pending',
                'blocking': True,
                'evidence_refs': ['artifacts/cutover_signoff_workflow.json', 'artifacts/executor_cutover_readiness_pack.json', 'artifacts/future_executor_handoff_summary.json'],
            },
        ])
    integration_checklist_payload = {
        'task_id': task_dir.name,
        'record_type': 'real_executor_integration_checklist',
        'generated_at': _now(),
        'integration_checklist_available': True,
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'overall_status': 'pending_real_executor_implementation',
        'blocking_open_count': sum(1 for item in checklist_items if item['blocking'] and item['status'] != 'passed'),
        'passed_count': sum(1 for item in checklist_items if item['status'] == 'passed'),
        'pending_count': sum(1 for item in checklist_items if item['status'] != 'passed'),
        'top_remaining_blockers': shared_blockers,
        'items': checklist_items,
        'refs': {
            'executor_readiness_review': 'artifacts/executor_readiness_review.json',
            'executor_admission_review': 'artifacts/executor_admission_review.json',
            'go_no_go_decision_pack': 'artifacts/go_no_go_decision_pack.json',
            'executor_conformance_matrix': 'artifacts/executor_conformance_matrix.json',
            'future_executor_implementation_blueprint': 'artifacts/future_executor_implementation_blueprint.json',
            'real_executor_delivery_backlog': 'artifacts/real_executor_delivery_backlog.json',
            'executor_acceptance_test_pack': 'artifacts/executor_acceptance_test_pack.json',
            'executor_blocker_matrix': 'artifacts/executor_blocker_matrix.json',
            'executor_ownership_split': 'artifacts/executor_ownership_split.json',
        },
    }
    manager.write_json('real_executor_integration_checklist.json', integration_checklist_payload)
    manager.write_text('real_executor_integration_checklist.md', (
        '# real executor integration checklist\n\n'
        + '\n'.join([
            '- integration_checklist_available: true',
            '- overall_status: pending_real_executor_implementation',
            f"- blocking_open_count: {integration_checklist_payload['blocking_open_count']}",
            f"- top_remaining_blockers: {', '.join(shared_blockers)}",
            '- note: this checklist is the pre-cutover checklist for future real executor work; it does not enable real execution.',
        ] + [f"- {item['check_id']}: {item['status']}" for item in checklist_items])
        + '\n'
    ))

    delivery_backlog_payload = {
        'task_id': task_dir.name,
        'record_type': 'real_executor_delivery_backlog',
        'generated_at': _now(),
        'executor_delivery_pack_available': True,
        'delivery_state': 'implementation_pack_only_no_real_executor_body',
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'delivery_item_count': len(delivery_backlog_items),
        'ready_to_start_count': sum(1 for item in delivery_backlog_items if item['blocker_state'] == 'can_start_now'),
        'blocked_count': sum(1 for item in delivery_backlog_items if item['blocker_state'] != 'can_start_now'),
        'targets': {
            target_key: {
                'execution_target': 'official_release' if target_key == 'release' else 'rollback',
                'module_count': sum(1 for item in delivery_backlog_items if item['execution_target'] == ('official_release' if target_key == 'release' else 'rollback')),
                'ready_to_start_count': sum(1 for item in delivery_backlog_items if item['execution_target'] == ('official_release' if target_key == 'release' else 'rollback') and item['blocker_state'] == 'can_start_now'),
                'blocked_count': sum(1 for item in delivery_backlog_items if item['execution_target'] == ('official_release' if target_key == 'release' else 'rollback') and item['blocker_state'] != 'can_start_now'),
            } for target_key in ('release','rollback')
        },
        'items': delivery_backlog_items,
        'refs': dict(shared_references),
        'note': 'This backlog is the final development delivery pack before future real executor implementation. It does not implement a real executor body.',
    }
    manager.write_json('real_executor_delivery_backlog.json', delivery_backlog_payload)
    manager.write_text('real_executor_delivery_backlog.md', (
        '# real executor delivery backlog\n\n'
        + '\n'.join([
            '- executor_delivery_pack_available: true',
            '- delivery_state: implementation_pack_only_no_real_executor_body',
            f"- delivery_item_count: {delivery_backlog_payload['delivery_item_count']}",
            f"- ready_to_start_count: {delivery_backlog_payload['ready_to_start_count']}",
            f"- blocked_count: {delivery_backlog_payload['blocked_count']}",
        ] + [f"- {item['item_id']}: {item['status']} ({item['risk_level']})" for item in delivery_backlog_items])
        + '\n'
    ))

    acceptance_test_pack_payload = {
        'task_id': task_dir.name,
        'record_type': 'executor_acceptance_test_pack',
        'generated_at': _now(),
        'executor_acceptance_pack_available': True,
        'acceptance_pack_state': 'pending_real_executor_body_for_execution',
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'test_case_count': len(acceptance_test_items),
        'targets': {
            target_key: {
                'execution_target': 'official_release' if target_key == 'release' else 'rollback',
                'case_ids': list(target_acceptance_cases[target_key]),
            } for target_key in ('release','rollback')
        },
        'items': acceptance_test_items,
        'refs': dict(shared_references),
        'note': 'Acceptance tests are packaged here for future real executor implementation. Current phase remains replay/simulation-only.',
    }
    manager.write_json('executor_acceptance_test_pack.json', acceptance_test_pack_payload)
    manager.write_text('executor_acceptance_test_pack.md', (
        '# executor acceptance test pack\n\n'
        + '\n'.join([
            '- executor_acceptance_pack_available: true',
            '- acceptance_pack_state: pending_real_executor_body_for_execution',
            f"- test_case_count: {acceptance_test_pack_payload['test_case_count']}",
        ] + [f"- {item['case_id']}: {item['status']}" for item in acceptance_test_items])
        + '\n'
    ))

    ownership_split_payload = {
        'task_id': task_dir.name,
        'record_type': 'executor_ownership_split',
        'generated_at': _now(),
        'ownership_split_available': True,
        'ownership_state': 'delivery_pack_ready_for_future_executor_implementers',
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'owner_count': len({item['recommended_owner'] for item in ownership_split_items}),
        'split_count': len(ownership_split_items),
        'items': ownership_split_items,
        'refs': dict(shared_references),
    }
    manager.write_json('executor_ownership_split.json', ownership_split_payload)
    manager.write_text('executor_ownership_split.md', (
        '# executor ownership split\n\n'
        + '\n'.join([
            '- ownership_split_available: true',
            '- ownership_state: delivery_pack_ready_for_future_executor_implementers',
            f"- split_count: {ownership_split_payload['split_count']}",
            f"- owner_count: {ownership_split_payload['owner_count']}",
        ] + [f"- {item['split_id']}: owner={item['recommended_owner']}" for item in ownership_split_items])
        + '\n'
    ))

    blocker_matrix_payload = {
        'task_id': task_dir.name,
        'record_type': 'executor_blocker_matrix',
        'generated_at': _now(),
        'executor_blocker_matrix_available': True,
        'blocker_matrix_state': 'implementation_blockers_explicit',
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'executor_blocker_count': len(blocker_items),
        'must_unblock_first_count': sum(1 for item in blocker_items if item['blocker_state'] == 'must_unblock_first'),
        'can_start_now_count': sum(1 for item in delivery_backlog_items if item['blocker_state'] == 'can_start_now'),
        'top_executor_blockers': list(shared_blocker_ids[:5]),
        'items': blocker_items,
        'refs': dict(shared_references),
        'note': 'Blockers classify what may start now versus what must be cleared before any future real execution work can progress to cutover.',
    }
    manager.write_json('executor_blocker_matrix.json', blocker_matrix_payload)
    manager.write_text('executor_blocker_matrix.md', (
        '# executor blocker matrix\n\n'
        + '\n'.join([
            '- executor_blocker_matrix_available: true',
            '- blocker_matrix_state: implementation_blockers_explicit',
            f"- executor_blocker_count: {blocker_matrix_payload['executor_blocker_count']}",
            f"- must_unblock_first_count: {blocker_matrix_payload['must_unblock_first_count']}",
            f"- top_executor_blockers: {', '.join(blocker_matrix_payload['top_executor_blockers'])}",
        ] + [f"- {item['blocker_id']}: {item['status']} ({item['severity']})" for item in blocker_items])
        + '\n'
    ))

    credential_binding_items = []
    target_binding_items = []
    signoff_items = []
    blocker_drilldown_items = []
    blocker_category_counts = Counter()
    blocker_bucket_counts = Counter()
    unresolved_credential_binding_count = 0
    unresolved_signoff_count = 0
    for target_key, execution_target in (('release', 'official_release'), ('rollback', 'rollback')):
        target_label = '正式发布' if target_key == 'release' else '回滚'
        credential_binding_items.extend([
            {
                'binding_id': f'{target_key}_executor_endpoint_secret',
                'execution_target': execution_target,
                'binding_scope': 'credential',
                'binding_category': 'secret',
                'binding_field': 'executor_endpoint_secret_ref',
                'title': f'{target_label}执行器接入凭据引用',
                'required': True,
                'manual_configuration_required': True,
                'future_integration_only': True,
                'current_value_state': 'unbound',
                'allowed_value_shape': 'secret-ref://<provider>/<name>',
                'placeholder_value': '',
                'reason': '真实执行器未接入前只能保留引用位，不得写入真实密钥。',
                'evidence_refs': [f'artifacts/{target_key}_executor_adapter_manifest.json', 'artifacts/real_executor_handoff_boundary.json'],
            },
            {
                'binding_id': f'{target_key}_operator_identity_binding',
                'execution_target': execution_target,
                'binding_scope': 'credential',
                'binding_category': 'operator_identity',
                'binding_field': 'operator_identity_ref',
                'title': f'{target_label}人工执行身份绑定',
                'required': True,
                'manual_configuration_required': True,
                'future_integration_only': False,
                'current_value_state': 'pending_manual_binding',
                'allowed_value_shape': 'operator://<team>/<user_or_group>',
                'placeholder_value': '',
                'reason': '执行请求已存在，但正式 owner/backup owner 仍需人工受控确认。',
                'evidence_refs': [f'artifacts/{target_key}_operator_execution_request.json', 'artifacts/execution_request_registry.json'],
            },
            {
                'binding_id': f'{target_key}_execution_window_policy',
                'execution_target': execution_target,
                'binding_scope': 'policy',
                'binding_category': 'time_window',
                'binding_field': 'approved_execution_window',
                'title': f'{target_label}切换窗口策略绑定',
                'required': True,
                'manual_configuration_required': True,
                'future_integration_only': False,
                'current_value_state': 'pending_manual_binding',
                'allowed_value_shape': 'ISO8601 window + timezone + approver',
                'placeholder_value': '',
                'reason': '切换窗口必须在人工签字时明确，不得默认放开。',
                'evidence_refs': ['artifacts/executor_cutover_readiness_pack.json', 'artifacts/future_executor_handoff_summary.json'],
            },
        ])
        target_binding_items.extend([
            {
                'binding_id': f'{target_key}_target_environment',
                'execution_target': execution_target,
                'binding_scope': 'target',
                'binding_category': 'environment',
                'binding_field': 'target_environment_ref',
                'title': f'{target_label}目标环境绑定',
                'required': True,
                'manual_configuration_required': True,
                'future_integration_only': True,
                'current_value_state': 'unbound',
                'allowed_value_shape': 'env://<tier>/<region>/<cluster>',
                'placeholder_value': '',
                'reason': '真实目标环境尚未进入受控绑定，当前只能保留空位。',
                'evidence_refs': [f'artifacts/{target_key}_executor_adapter_manifest.json', 'artifacts/real_executor_handoff_boundary.json'],
            },
            {
                'binding_id': f'{target_key}_target_change_ticket',
                'execution_target': execution_target,
                'binding_scope': 'target',
                'binding_category': 'change_control',
                'binding_field': 'change_ticket_ref',
                'title': f'{target_label}变更单绑定',
                'required': True,
                'manual_configuration_required': True,
                'future_integration_only': False,
                'current_value_state': 'pending_manual_binding',
                'allowed_value_shape': 'change://<system>/<ticket>',
                'placeholder_value': '',
                'reason': '真实切换前必须有人工登记的变更单据。',
                'evidence_refs': ['artifacts/real_executor_integration_checklist.json', 'artifacts/executor_cutover_readiness_pack.json'],
            },
        ])
        signoff_items.extend([
            {
                'signoff_id': f'{target_key}_ops_binding_review',
                'execution_target': execution_target,
                'step_order': 1,
                'role': 'ops-monitor',
                'title': f'{target_label}凭据/目标绑定复核',
                'status': 'pending',
                'required': True,
                'manual_only': True,
                'evidence_requirements': [f'{target_key}_credential_bindings_complete', f'{target_key}_target_bindings_complete'],
                'evidence_refs': ['artifacts/executor_credential_binding_policy.json', 'artifacts/executor_target_binding_registry.json'],
            },
            {
                'signoff_id': f'{target_key}_qa_traceability_review',
                'execution_target': execution_target,
                'step_order': 2,
                'role': 'test-expert',
                'title': f'{target_label}traceability / acceptance 复核',
                'status': 'pending',
                'required': True,
                'manual_only': True,
                'evidence_requirements': [f'{target_key}_acceptance_cases_ready', f'{target_key}_receipt_transcript_parity_preserved'],
                'evidence_refs': ['artifacts/executor_acceptance_test_pack.json', 'artifacts/release_rollback_parity_matrix.json', 'artifacts/executor_conformance_matrix.json'],
            },
            {
                'signoff_id': f'{target_key}_business_cutover_authorization',
                'execution_target': execution_target,
                'step_order': 3,
                'role': 'master-quant',
                'title': f'{target_label}最终 cutover 授权',
                'status': 'pending',
                'required': True,
                'manual_only': True,
                'evidence_requirements': [f'{target_key}_binding_review_signed', f'{target_key}_qa_review_signed', f'{target_key}_execution_window_confirmed'],
                'evidence_refs': ['artifacts/cutover_signoff_workflow.json', 'artifacts/future_executor_handoff_summary.json', 'artifacts/executor_risk_register.json'],
            },
        ])
        blocker_drilldown_items.extend([
            {
                'blocker_id': f'{target_key}_can_prepare_binding_governance',
                'execution_target': execution_target,
                'bucket': 'can_prepare_now',
                'category': 'governance_preparation',
                'severity': 'medium',
                'title': f'{target_label}凭据/目标绑定治理文档可先做',
                'status': 'ready',
                'why': '不需要真实执行器即可先完成治理面。',
                'evidence_refs': ['artifacts/executor_credential_binding_policy.json', 'artifacts/executor_target_binding_registry.json'],
            },
            {
                'blocker_id': f'{target_key}_wait_for_real_executor_body',
                'execution_target': execution_target,
                'bucket': 'must_wait',
                'category': 'executor_implementation',
                'severity': 'critical',
                'title': f'{target_label}必须等待真实执行器本体',
                'status': 'blocked',
                'why': '严格边界禁止在此阶段实现真实自动执行。',
                'evidence_refs': [f'artifacts/{target_key}_executor_plugin_interface.json', 'artifacts/future_executor_implementation_blueprint.json'],
            },
            {
                'blocker_id': f'{target_key}_high_risk_cutover_without_binding',
                'execution_target': execution_target,
                'bucket': 'highest_risk',
                'category': 'binding_and_signoff',
                'severity': 'critical',
                'title': f'{target_label}未绑定凭据/目标且无签字时切换风险最高',
                'status': 'open',
                'why': '若未来跳过绑定与签字，将直接破坏人工审批和零越权边界。',
                'evidence_refs': ['artifacts/executor_credential_binding_policy.json', 'artifacts/cutover_signoff_workflow.json', 'artifacts/executor_risk_register.json'],
            },
        ])
    unresolved_credential_binding_count = sum(1 for item in credential_binding_items + target_binding_items if item.get('required') and item.get('current_value_state') in {'unbound', 'pending_manual_binding'})
    unresolved_signoff_count = sum(1 for item in signoff_items if item.get('required') and item.get('status') != 'signed')
    for item in blocker_drilldown_items:
        blocker_category_counts[item['category']] += 1
        blocker_bucket_counts[item['bucket']] += 1
    top_blocker_categories = [name for name, _count in sorted(blocker_category_counts.items(), key=lambda pair: (-pair[1], pair[0]))[:5]]

    credential_binding_policy_payload = {
        'task_id': task_dir.name,
        'record_type': 'executor_credential_binding_policy',
        'generated_at': _now(),
        'credential_binding_policy_available': True,
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'applies_to_targets': ['official_release', 'rollback'],
        'required_binding_count': len(credential_binding_items),
        'unresolved_binding_count': unresolved_credential_binding_count,
        'manual_configuration_required_count': sum(1 for item in credential_binding_items if item.get('manual_configuration_required')),
        'future_integration_only_count': sum(1 for item in credential_binding_items if item.get('future_integration_only')),
        'items': credential_binding_items,
        'refs': dict(shared_references),
        'note': '本策略只定义受控绑定字段与空位规则；当前阶段不得填入真实密钥，也不得触发真实执行。',
    }
    manager.write_json('executor_credential_binding_policy.json', credential_binding_policy_payload)
    manager.write_text('executor_credential_binding_policy.md', (
        '# executor credential binding policy\n\n'
        + '\n'.join([
            '- credential_binding_policy_available: true',
            f"- required_binding_count: {credential_binding_policy_payload['required_binding_count']}",
            f"- unresolved_binding_count: {credential_binding_policy_payload['unresolved_binding_count']}",
            '- note: real credentials must remain blank/unbound in this phase; only governance placeholders are allowed.',
        ] + [f"- {item['binding_id']}: {item['current_value_state']}" for item in credential_binding_items])
        + '\n'
    ))

    target_binding_registry_payload = {
        'task_id': task_dir.name,
        'record_type': 'executor_target_binding_registry',
        'generated_at': _now(),
        'target_binding_registry_available': True,
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'target_binding_count': len(target_binding_items),
        'unresolved_binding_count': sum(1 for item in target_binding_items if item.get('required') and item.get('current_value_state') in {'unbound', 'pending_manual_binding'}),
        'items': target_binding_items,
        'refs': dict(shared_references),
        'note': '本 registry 仅登记未来真实环境绑定槽位，不写入任何外部真实目标。',
    }
    manager.write_json('executor_target_binding_registry.json', target_binding_registry_payload)
    manager.write_text('executor_target_binding_registry.md', (
        '# executor target binding registry\n\n'
        + '\n'.join([
            '- target_binding_registry_available: true',
            f"- target_binding_count: {target_binding_registry_payload['target_binding_count']}",
            f"- unresolved_binding_count: {target_binding_registry_payload['unresolved_binding_count']}",
            '- note: target bindings stay governance-only until future real executor cutover.',
        ] + [f"- {item['binding_id']}: {item['current_value_state']}" for item in target_binding_items])
        + '\n'
    ))

    cutover_signoff_workflow_payload = {
        'task_id': task_dir.name,
        'record_type': 'cutover_signoff_workflow',
        'generated_at': _now(),
        'cutover_signoff_available': True,
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'required_signoff_count': len(signoff_items),
        'unresolved_signoff_count': unresolved_signoff_count,
        'role_count': len({item['role'] for item in signoff_items}),
        'steps': signoff_items,
        'refs': dict(shared_references),
        'note': '所有 signoff 当前均保持 pending；此工作流只补齐治理链，不授权真实执行。',
    }
    manager.write_json('cutover_signoff_workflow.json', cutover_signoff_workflow_payload)
    manager.write_text('cutover_signoff_workflow.md', (
        '# cutover signoff workflow\n\n'
        + '\n'.join([
            '- cutover_signoff_available: true',
            f"- required_signoff_count: {cutover_signoff_workflow_payload['required_signoff_count']}",
            f"- unresolved_signoff_count: {cutover_signoff_workflow_payload['unresolved_signoff_count']}",
            '- note: signoff roles, evidence, and ordering are defined here; signatures are intentionally still pending.',
        ] + [f"- {item['signoff_id']}: {item['status']}" for item in signoff_items])
        + '\n'
    ))

    blocker_drilldown_payload = {
        'task_id': task_dir.name,
        'record_type': 'blocker_drilldown_review',
        'generated_at': _now(),
        'blocker_drilldown_available': True,
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'blocker_count': len(blocker_drilldown_items),
        'bucket_counts': dict(blocker_bucket_counts),
        'category_counts': dict(blocker_category_counts),
        'top_blocker_categories': top_blocker_categories,
        'items': blocker_drilldown_items,
        'refs': dict(shared_references),
        'note': '将 blocker 从总数拆分为 can_prepare_now / must_wait / highest_risk 三类，便于后续 cutover drilldown。',
    }
    manager.write_json('blocker_drilldown_review.json', blocker_drilldown_payload)
    manager.write_text('blocker_drilldown_review.md', (
        '# blocker drilldown review\n\n'
        + '\n'.join([
            '- blocker_drilldown_available: true',
            f"- blocker_count: {blocker_drilldown_payload['blocker_count']}",
            f"- bucket_counts: {blocker_drilldown_payload['bucket_counts']}",
            f"- top_blocker_categories: {', '.join(top_blocker_categories)}",
        ] + [f"- {item['blocker_id']}: {item['bucket']} / {item['severity']}" for item in blocker_drilldown_items])
        + '\n'
    ))

    human_action_items = []
    for item in credential_binding_items:
        human_action_items.append({
            'action_id': f"manual_bind::{item['binding_id']}",
            'action_family': 'credential_or_policy_binding',
            'execution_target': item['execution_target'],
            'title': item['title'],
            'manual_only': True,
            'step_kind': 'binding',
            'can_start_now': item.get('future_integration_only') is not True,
            'waits_for_real_executor': item.get('future_integration_only') is True,
            'required_inputs': [item.get('binding_field'), item.get('allowed_value_shape'), 'approver_identity'],
            'required_evidence': list(item.get('evidence_refs') or []),
            'current_state': item.get('current_value_state'),
        })
    for item in target_binding_items:
        human_action_items.append({
            'action_id': f"manual_bind::{item['binding_id']}",
            'action_family': 'target_binding',
            'execution_target': item['execution_target'],
            'title': item['title'],
            'manual_only': True,
            'step_kind': 'binding',
            'can_start_now': item.get('future_integration_only') is not True,
            'waits_for_real_executor': item.get('future_integration_only') is True,
            'required_inputs': [item.get('binding_field'), item.get('allowed_value_shape'), 'change_control_reference'],
            'required_evidence': list(item.get('evidence_refs') or []),
            'current_state': item.get('current_value_state'),
        })
    for item in signoff_items:
        human_action_items.append({
            'action_id': f"manual_signoff::{item['signoff_id']}",
            'action_family': 'cutover_signoff',
            'execution_target': item['execution_target'],
            'title': item['title'],
            'manual_only': True,
            'step_kind': 'signoff',
            'can_start_now': True,
            'waits_for_real_executor': False,
            'required_inputs': list(item.get('evidence_requirements') or []),
            'required_evidence': list(item.get('evidence_refs') or []),
            'current_state': item.get('status'),
        })
    top_human_actions = [item['action_id'] for item in human_action_items[:8]]
    top_unresolved_human_blockers = [
        item['blocker_id']
        for item in blocker_drilldown_items
        if item.get('bucket') in {'must_wait', 'highest_risk'} or item.get('status') in {'blocked', 'open'}
    ][:8]

    binding_evidence_items = []
    for item in credential_binding_items + target_binding_items:
        evidence_refs = list(item.get('evidence_refs') or [])
        missing_evidence_refs = [ref for ref in evidence_refs if not (task_dir / ref).exists()]
        binding_state = item.get('current_value_state')
        evidence_state = 'missing' if missing_evidence_refs else 'ready'
        if binding_state in {'unbound', 'pending_manual_binding'}:
            evidence_state = 'pending_manual_evidence'
        binding_evidence_items.append({
            'binding_id': item.get('binding_id'),
            'execution_target': item.get('execution_target'),
            'binding_kind': item.get('binding_kind'),
            'title': item.get('title'),
            'required': bool(item.get('required')),
            'manual_only': True,
            'shared_rule_family': 'release_rollback_controlled_executor_policy',
            'binding_state': binding_state,
            'evidence_state': evidence_state,
            'needs_manual_binding': binding_state in {'unbound', 'pending_manual_binding'},
            'evidence_refs': evidence_refs,
            'missing_evidence_refs': missing_evidence_refs,
            'required_inputs': list(item.get('allowed_values') or []) or [item.get('binding_field')],
            'source_refs': {
                'binding_policy': 'artifacts/executor_credential_binding_policy.json' if item.get('binding_kind') == 'credential' else 'artifacts/executor_target_binding_registry.json',
                'binding_runbook': 'artifacts/credential_binding_runbook.json',
                'signoff_workflow': 'artifacts/cutover_signoff_workflow.json',
            },
        })
    binding_evidence_gap_count = sum(
        1
        for item in binding_evidence_items
        if item.get('required') and (item.get('needs_manual_binding') or item.get('missing_evidence_refs'))
    )
    credential_binding_evidence_checklist_payload = {
        'task_id': task_dir.name,
        'record_type': 'credential_binding_evidence_checklist',
        'generated_at': _now(),
        'credential_binding_evidence_checklist_available': True,
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'binding_evidence_gap_count': binding_evidence_gap_count,
        'required_item_count': len(binding_evidence_items),
        'pending_manual_binding_count': sum(1 for item in binding_evidence_items if item.get('needs_manual_binding')),
        'missing_evidence_ref_count': sum(len(item.get('missing_evidence_refs') or []) for item in binding_evidence_items),
        'items': binding_evidence_items,
        'refs': {
            'executor_credential_binding_policy': 'artifacts/executor_credential_binding_policy.json',
            'executor_target_binding_registry': 'artifacts/executor_target_binding_registry.json',
            'credential_binding_runbook': 'artifacts/credential_binding_runbook.json',
            'cutover_signoff_workflow': 'artifacts/cutover_signoff_workflow.json',
            'blocker_drilldown_review': 'artifacts/blocker_drilldown_review.json',
        },
        'note': '同一套 checklist 同时适用于 release / rollback；只追踪证据与空位，不写入真实凭据。',
    }
    manager.write_json('credential_binding_evidence_checklist.json', credential_binding_evidence_checklist_payload)
    manager.write_text('credential_binding_evidence_checklist.md', (
        '# credential binding evidence checklist\n\n'
        + '\n'.join([
            '- credential_binding_evidence_checklist_available: true',
            f"- required_item_count: {credential_binding_evidence_checklist_payload['required_item_count']}",
            f"- binding_evidence_gap_count: {credential_binding_evidence_checklist_payload['binding_evidence_gap_count']}",
            '- note: shared evidence checklist for release/rollback manual binding only.',
        ] + [f"- {item['binding_id']}: {item['binding_state']} / {item['evidence_state']}" for item in binding_evidence_items])
        + '\n'
    ))

    signoff_evidence_items = []
    for item in signoff_items:
        evidence_refs = list(item.get('evidence_refs') or [])
        missing_evidence_refs = [ref for ref in evidence_refs if not (task_dir / ref).exists()]
        prerequisite_signoff_ids = []
        if item.get('step_order') == 2:
            prerequisite_signoff_ids.append(f"{'release' if item.get('execution_target') == 'official_release' else 'rollback'}_ops_binding_review")
        elif item.get('step_order') == 3:
            target_key = 'release' if item.get('execution_target') == 'official_release' else 'rollback'
            prerequisite_signoff_ids.extend([f'{target_key}_ops_binding_review', f'{target_key}_qa_traceability_review'])
        signoff_evidence_items.append({
            'signoff_id': item.get('signoff_id'),
            'execution_target': item.get('execution_target'),
            'role': item.get('role'),
            'title': item.get('title'),
            'status': item.get('status'),
            'required': bool(item.get('required')),
            'manual_only': True,
            'shared_rule_family': 'release_rollback_controlled_executor_policy',
            'evidence_requirements': list(item.get('evidence_requirements') or []),
            'evidence_refs': evidence_refs,
            'missing_evidence_refs': missing_evidence_refs,
            'prerequisite_signoff_ids': prerequisite_signoff_ids,
            'evidence_ready': not missing_evidence_refs,
        })
    pending_signoff_role_count = len({item.get('role') for item in signoff_evidence_items if item.get('status') != 'signed' and item.get('role')})
    cutover_signoff_evidence_packet_payload = {
        'task_id': task_dir.name,
        'record_type': 'cutover_signoff_evidence_packet',
        'generated_at': _now(),
        'cutover_signoff_evidence_packet_available': True,
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'pending_signoff_count': sum(1 for item in signoff_evidence_items if item.get('status') != 'signed'),
        'pending_signoff_role_count': pending_signoff_role_count,
        'items': signoff_evidence_items,
        'refs': {
            'cutover_signoff_workflow': 'artifacts/cutover_signoff_workflow.json',
            'credential_binding_evidence_checklist': 'artifacts/credential_binding_evidence_checklist.json',
            'executor_acceptance_test_pack': 'artifacts/executor_acceptance_test_pack.json',
            'release_rollback_parity_matrix': 'artifacts/release_rollback_parity_matrix.json',
            'executor_conformance_matrix': 'artifacts/executor_conformance_matrix.json',
            'future_executor_handoff_summary': 'artifacts/future_executor_handoff_summary.json',
            'executor_risk_register': 'artifacts/executor_risk_register.json',
        },
        'note': '此 evidence packet 只归集 signoff 证据依赖与前后置关系，不形成真实签字。',
    }
    manager.write_json('cutover_signoff_evidence_packet.json', cutover_signoff_evidence_packet_payload)
    manager.write_text('cutover_signoff_evidence_packet.md', (
        '# cutover signoff evidence packet\n\n'
        + '\n'.join([
            '- cutover_signoff_evidence_packet_available: true',
            f"- pending_signoff_count: {cutover_signoff_evidence_packet_payload['pending_signoff_count']}",
            f"- pending_signoff_role_count: {cutover_signoff_evidence_packet_payload['pending_signoff_role_count']}",
            '- note: shared signoff evidence packet for release/rollback governance only.',
        ] + [f"- {item['signoff_id']}: {item['status']} / evidence_ready={str(item['evidence_ready']).lower()}" for item in signoff_evidence_items])
        + '\n'
    ))

    executor_human_action_pack_payload = {
        'task_id': task_dir.name,
        'record_type': 'executor_human_action_pack',
        'generated_at': _now(),
        'human_action_pack_available': True,
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'shared_rules': {
            'manual_steps_only': True,
            'external_writes_forbidden': True,
            'real_executor_bodies_still_missing': True,
        },
        'action_count': len(human_action_items),
        'top_human_actions': top_human_actions,
        'top_unresolved_human_blockers': top_unresolved_human_blockers,
        'actions': human_action_items,
        'refs': {
            **dict(shared_references),
            'executor_credential_binding_policy': 'artifacts/executor_credential_binding_policy.json',
            'executor_target_binding_registry': 'artifacts/executor_target_binding_registry.json',
            'cutover_signoff_workflow': 'artifacts/cutover_signoff_workflow.json',
            'blocker_drilldown_review': 'artifacts/blocker_drilldown_review.json',
            'executor_cutover_readiness_pack': 'artifacts/executor_cutover_readiness_pack.json',
        },
        'note': '该 action pack 只把后续必须人工做的动作显式化，不触发真实执行，也不写入任何外部系统。',
    }
    manager.write_json('executor_human_action_pack.json', executor_human_action_pack_payload)
    manager.write_text('executor_human_action_pack.md', (
        '# executor human action pack\n\n'
        + '\n'.join([
            '- human_action_pack_available: true',
            f"- action_count: {executor_human_action_pack_payload['action_count']}",
            f"- top_human_actions: {', '.join(top_human_actions)}",
            f"- top_unresolved_human_blockers: {', '.join(top_unresolved_human_blockers)}",
            '- note: manual execution/configuration pack only; zero real execution is preserved.',
        ])
        + '\n'
    ))

    pending_human_action_items = []
    for item in human_action_items:
        current_state = str(item.get('current_state') or '')
        if item.get('step_kind') == 'binding':
            state = 'waiting' if item.get('waits_for_real_executor') else 'ready'
            if current_state not in {'unbound', 'pending_manual_binding'}:
                state = 'in_review'
        else:
            prerequisite_ids = next((entry.get('prerequisite_signoff_ids') for entry in signoff_evidence_items if entry.get('signoff_id') == item.get('action_id', '').split('::')[-1]), []) or []
            has_open_prereq = any(
                entry.get('signoff_id') in prerequisite_ids and entry.get('status') != 'signed'
                for entry in signoff_evidence_items
            )
            state = 'blocked' if has_open_prereq else 'ready'
        pending_human_action_items.append({
            **item,
            'state': state,
            'source_refs': {
                'human_action_pack': 'artifacts/executor_human_action_pack.json',
                'credential_binding_evidence_checklist': 'artifacts/credential_binding_evidence_checklist.json',
                'cutover_signoff_evidence_packet': 'artifacts/cutover_signoff_evidence_packet.json',
            },
        })
    pending_human_action_state_counts = {
        'ready': sum(1 for item in pending_human_action_items if item.get('state') == 'ready'),
        'blocked': sum(1 for item in pending_human_action_items if item.get('state') == 'blocked'),
        'waiting': sum(1 for item in pending_human_action_items if item.get('state') == 'waiting'),
        'in_review': sum(1 for item in pending_human_action_items if item.get('state') == 'in_review'),
    }
    top_pending_human_actions = [item['action_id'] for item in pending_human_action_items if item.get('state') in {'ready', 'blocked', 'waiting'}][:8]
    pending_human_action_board_payload = {
        'task_id': task_dir.name,
        'record_type': 'pending_human_action_board',
        'generated_at': _now(),
        'pending_human_action_board_available': True,
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'state_counts': pending_human_action_state_counts,
        'top_pending_human_actions': top_pending_human_actions,
        'items': pending_human_action_items,
        'refs': {
            'executor_human_action_pack': 'artifacts/executor_human_action_pack.json',
            'credential_binding_evidence_checklist': 'artifacts/credential_binding_evidence_checklist.json',
            'cutover_signoff_evidence_packet': 'artifacts/cutover_signoff_evidence_packet.json',
            'unresolved_blocker_tracker': 'artifacts/unresolved_blocker_tracker.json',
        },
        'note': 'board 只标记 ready / blocked / waiting / in_review，不触发任何真实执行。',
    }
    manager.write_json('pending_human_action_board.json', pending_human_action_board_payload)
    manager.write_text('pending_human_action_board.md', (
        '# pending human action board\n\n'
        + '\n'.join([
            '- pending_human_action_board_available: true',
            f"- state_counts: {pending_human_action_state_counts}",
            f"- top_pending_human_actions: {', '.join(top_pending_human_actions)}",
            '- note: manual board only; ready/blocked/waiting states remain internal governance states.',
        ] + [f"- {item['action_id']}: {item['state']}" for item in pending_human_action_items])
        + '\n'
    ))

    unresolved_blocker_items = []
    owner_map = {
        'executor_implementation': 'coder',
        'binding_and_signoff': 'ops-monitor',
        'governance_preparation': 'doc-manager',
    }
    for item in blocker_drilldown_items:
        owner = owner_map.get(item.get('category'))
        evidence_refs = list(item.get('evidence_refs') or [])
        missing_evidence_refs = [ref for ref in evidence_refs if not (task_dir / ref).exists()]
        prerequisite_refs = []
        if item.get('category') == 'binding_and_signoff':
            prerequisite_refs = [
                'artifacts/credential_binding_evidence_checklist.json',
                'artifacts/cutover_signoff_evidence_packet.json',
            ]
        elif item.get('category') == 'executor_implementation':
            prerequisite_refs = ['artifacts/future_executor_implementation_blueprint.json']
        unresolved_blocker_items.append({
            'blocker_id': item.get('blocker_id'),
            'execution_target': item.get('execution_target'),
            'category': item.get('category'),
            'severity': item.get('severity'),
            'status': item.get('status'),
            'owner': owner,
            'owner_missing': owner is None,
            'evidence_refs': evidence_refs,
            'missing_evidence_refs': missing_evidence_refs,
            'prerequisite_refs': prerequisite_refs,
            'prerequisite_missing': [ref for ref in prerequisite_refs if not (task_dir / ref).exists()],
            'shared_rule_family': 'release_rollback_controlled_executor_policy',
            'source_refs': {
                'blocker_drilldown_review': 'artifacts/blocker_drilldown_review.json',
                'blocker_resolution_playbook': 'artifacts/blocker_resolution_playbook.json',
                'credential_binding_evidence_checklist': 'artifacts/credential_binding_evidence_checklist.json',
                'cutover_signoff_evidence_packet': 'artifacts/cutover_signoff_evidence_packet.json',
            },
        })
    unresolved_blocker_owner_count = len({item['owner'] for item in unresolved_blocker_items if item.get('owner')})
    unresolved_blocker_tracker_payload = {
        'task_id': task_dir.name,
        'record_type': 'unresolved_blocker_tracker',
        'generated_at': _now(),
        'unresolved_blocker_tracker_available': True,
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'blocker_count': len(unresolved_blocker_items),
        'unresolved_blocker_owner_count': unresolved_blocker_owner_count,
        'owner_missing_count': sum(1 for item in unresolved_blocker_items if item.get('owner_missing')),
        'evidence_missing_count': sum(1 for item in unresolved_blocker_items if item.get('missing_evidence_refs')),
        'prerequisite_missing_count': sum(1 for item in unresolved_blocker_items if item.get('prerequisite_missing')),
        'items': unresolved_blocker_items,
        'refs': {
            'blocker_drilldown_review': 'artifacts/blocker_drilldown_review.json',
            'blocker_resolution_playbook': 'artifacts/blocker_resolution_playbook.json',
            'credential_binding_evidence_checklist': 'artifacts/credential_binding_evidence_checklist.json',
            'cutover_signoff_evidence_packet': 'artifacts/cutover_signoff_evidence_packet.json',
            'pending_human_action_board': 'artifacts/pending_human_action_board.json',
        },
        'note': 'tracker 只做 blocker 可追踪化，不改变 blocker 本身，不接触外部系统。',
    }
    manager.write_json('unresolved_blocker_tracker.json', unresolved_blocker_tracker_payload)
    manager.write_text('unresolved_blocker_tracker.md', (
        '# unresolved blocker tracker\n\n'
        + '\n'.join([
            '- unresolved_blocker_tracker_available: true',
            f"- blocker_count: {unresolved_blocker_tracker_payload['blocker_count']}",
            f"- unresolved_blocker_owner_count: {unresolved_blocker_tracker_payload['unresolved_blocker_owner_count']}",
            f"- evidence_missing_count: {unresolved_blocker_tracker_payload['evidence_missing_count']}",
            '- note: tracks owner/evidence/prerequisite gaps only.',
        ] + [f"- {item['blocker_id']}: owner={item['owner'] or 'none'} / status={item['status']}" for item in unresolved_blocker_items])
        + '\n'
    ))

    credential_binding_runbook_payload = {
        'task_id': task_dir.name,
        'record_type': 'credential_binding_runbook',
        'generated_at': _now(),
        'credential_binding_runbook_available': True,
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'must_be_done_manually': True,
        'steps_by_target': {
            target_key: {
                'execution_target': 'official_release' if target_key == 'release' else 'rollback',
                'steps': [
                    {
                        'step_id': f"{target_key}_collect_binding_inputs",
                        'title': '收集待绑定输入与审批上下文',
                        'manual_only': True,
                        'required_inputs': ['operator_identity', 'change_ticket_ref', 'approved_execution_window'],
                        'required_evidence': [
                            'artifacts/executor_cutover_readiness_pack.json',
                            'artifacts/future_executor_handoff_summary.json',
                        ],
                    },
                    {
                        'step_id': f"{target_key}_bind_credentials_and_targets",
                        'title': '人工填写 credential / target 槽位并保留证据',
                        'manual_only': True,
                        'required_inputs': [item.get('binding_id') for item in credential_binding_items + target_binding_items if item.get('execution_target') == ('official_release' if target_key == 'release' else 'rollback')],
                        'required_evidence': [
                            'artifacts/executor_credential_binding_policy.json',
                            'artifacts/executor_target_binding_registry.json',
                        ],
                    },
                    {
                        'step_id': f"{target_key}_binding_review_and_archive",
                        'title': '人工复核绑定结果并归档审计证据',
                        'manual_only': True,
                        'required_inputs': ['binding_snapshot', 'reviewer_identity', 'review_timestamp'],
                        'required_evidence': [
                            'artifacts/cutover_signoff_workflow.json',
                            'artifacts/blocker_drilldown_review.json',
                        ],
                    },
                ],
            }
            for target_key in ('release', 'rollback')
        },
        'top_unresolved_human_blockers': top_unresolved_human_blockers,
        'refs': {
            'executor_credential_binding_policy': 'artifacts/executor_credential_binding_policy.json',
            'executor_target_binding_registry': 'artifacts/executor_target_binding_registry.json',
            'executor_cutover_readiness_pack': 'artifacts/executor_cutover_readiness_pack.json',
            'cutover_signoff_workflow': 'artifacts/cutover_signoff_workflow.json',
            'blocker_drilldown_review': 'artifacts/blocker_drilldown_review.json',
        },
    }
    manager.write_json('credential_binding_runbook.json', credential_binding_runbook_payload)
    manager.write_text('credential_binding_runbook.md', (
        '# credential binding runbook\n\n'
        + '\n'.join([
            '- credential_binding_runbook_available: true',
            '- must_be_done_manually: true',
            f"- top_unresolved_human_blockers: {', '.join(top_unresolved_human_blockers)}",
            '- note: use this runbook to complete governed binding without enabling any real executor.',
        ])
        + '\n'
    ))

    cutover_signoff_runbook_payload = {
        'task_id': task_dir.name,
        'record_type': 'cutover_signoff_runbook',
        'generated_at': _now(),
        'signoff_runbook_available': True,
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'required_role_count': len({item['role'] for item in signoff_items}),
        'roles': sorted({item['role'] for item in signoff_items}),
        'steps_by_target': {
            target_key: {
                'execution_target': 'official_release' if target_key == 'release' else 'rollback',
                'steps': [item for item in signoff_items if item.get('execution_target') == ('official_release' if target_key == 'release' else 'rollback')]
            }
            for target_key in ('release', 'rollback')
        },
        'top_human_actions': [action_id for action_id in top_human_actions if action_id.startswith('manual_signoff::')][:6],
        'refs': {
            'cutover_signoff_workflow': 'artifacts/cutover_signoff_workflow.json',
            'executor_cutover_readiness_pack': 'artifacts/executor_cutover_readiness_pack.json',
            'future_executor_handoff_summary': 'artifacts/future_executor_handoff_summary.json',
            'executor_risk_register': 'artifacts/executor_risk_register.json',
            'executor_human_action_pack': 'artifacts/executor_human_action_pack.json',
        },
    }
    manager.write_json('cutover_signoff_runbook.json', cutover_signoff_runbook_payload)
    manager.write_text('cutover_signoff_runbook.md', (
        '# cutover signoff runbook\n\n'
        + '\n'.join([
            '- signoff_runbook_available: true',
            f"- required_role_count: {cutover_signoff_runbook_payload['required_role_count']}",
            f"- roles: {', '.join(cutover_signoff_runbook_payload['roles'])}",
            '- note: signoff ordering is defined here; all signatures remain pending until future manual cutover.',
        ])
        + '\n'
    ))

    blocker_resolution_playbook_payload = {
        'task_id': task_dir.name,
        'record_type': 'blocker_resolution_playbook',
        'generated_at': _now(),
        'blocker_resolution_playbook_available': True,
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'top_unresolved_human_blockers': top_unresolved_human_blockers,
        'resolution_buckets': {
            'can_prepare_now': [item for item in blocker_drilldown_items if item.get('bucket') == 'can_prepare_now'],
            'must_wait_for_real_executor': [item for item in blocker_drilldown_items if item.get('bucket') == 'must_wait'],
            'highest_risk': [item for item in blocker_drilldown_items if item.get('bucket') == 'highest_risk'],
        },
        'refs': {
            'blocker_drilldown_review': 'artifacts/blocker_drilldown_review.json',
            'real_executor_integration_checklist': 'artifacts/real_executor_integration_checklist.json',
            'executor_risk_register': 'artifacts/executor_risk_register.json',
            'executor_human_action_pack': 'artifacts/executor_human_action_pack.json',
            'cutover_signoff_runbook': 'artifacts/cutover_signoff_runbook.json',
        },
    }
    manager.write_json('blocker_resolution_playbook.json', blocker_resolution_playbook_payload)
    manager.write_text('blocker_resolution_playbook.md', (
        '# blocker resolution playbook\n\n'
        + '\n'.join([
            '- blocker_resolution_playbook_available: true',
            f"- top_unresolved_human_blockers: {', '.join(top_unresolved_human_blockers)}",
            '- note: separates blockers that can be resolved now from blockers that must wait for real executor implementation.',
        ])
        + '\n'
    ))

    risk_items = [
        {
            'risk_id': 'real_release_executor_missing',
            'title': '真实正式发布执行器本体缺失',
            'severity': 'critical',
            'likelihood': 'certain_until_implemented',
            'impact': 'no_real_release_cutover',
            'status': 'open',
            'mitigation': '仅允许 blueprint / checklist / handoff，待未来实现者按现有 plugin interface 与 contract 落地真实执行器。',
            'evidence_refs': ['artifacts/future_executor_implementation_blueprint.json', 'artifacts/real_executor_integration_checklist.json'],
        },
        {
            'risk_id': 'real_rollback_executor_missing',
            'title': '真实回滚执行器本体缺失',
            'severity': 'critical',
            'likelihood': 'certain_until_implemented',
            'impact': 'no_real_rollback_cutover',
            'status': 'open',
            'mitigation': 'release / rollback 需保持对称；在 rollback invoke() 实现前不得宣称 cutover ready。',
            'evidence_refs': ['artifacts/future_executor_implementation_blueprint.json', 'artifacts/release_rollback_parity_matrix.json'],
        },
        {
            'risk_id': 'credential_target_binding_unresolved',
            'title': '真实环境凭据/目标绑定仍未受控落地',
            'severity': 'critical',
            'likelihood': 'certain_until_manually_bound',
            'impact': 'unsafe_or_unknown_execution_target',
            'status': 'open',
            'mitigation': '先完成 credential binding policy / target registry 的人工配置，再进入未来 cutover。',
            'evidence_refs': ['artifacts/executor_credential_binding_policy.json', 'artifacts/executor_target_binding_registry.json'],
        },
        {
            'risk_id': 'cutover_signoff_pending',
            'title': 'cutover 人工签字工作流仍未完成',
            'severity': 'critical',
            'likelihood': 'certain_until_signed',
            'impact': 'no_authorized_cutover',
            'status': 'open',
            'mitigation': '按新的 signoff workflow 完成 ops / qa / final authorization 三层人工签字。',
            'evidence_refs': ['artifacts/cutover_signoff_workflow.json', 'artifacts/executor_cutover_readiness_pack.json'],
        },
        {
            'risk_id': 'gate_bypass_on_future_cutover',
            'title': '未来 cutover 若绕过 readiness/admission/go-no-go，会失去人工审批边界',
            'severity': 'high',
            'likelihood': 'possible',
            'impact': 'unsafe_external_write',
            'status': 'managed',
            'mitigation': '强制复用 rollout/admission/go-no-go 产物并在切换前再次逐项核对。',
            'evidence_refs': ['artifacts/executor_admission_review.json', 'artifacts/go_no_go_decision_pack.json', 'artifacts/rollout_gate_registry.json'],
        },
        {
            'risk_id': 'traceability_regression_on_real_adapter',
            'title': '真实适配器实现若破坏 traceability，会导致 receipt / handoff 审计断链',
            'severity': 'high',
            'likelihood': 'possible',
            'impact': 'audit_replay_loss',
            'status': 'managed',
            'mitigation': '实现时必须复用 transcript / receipt / error contract，并通过 conformance + compliance + rehearsal。',
            'evidence_refs': ['artifacts/executor_conformance_matrix.json', 'artifacts/contract_compliance_matrix.json', 'artifacts/executor_integration_rehearsal.json'],
        },
    ]
    risk_register_payload = {
        'task_id': task_dir.name,
        'record_type': 'executor_risk_register',
        'generated_at': _now(),
        'risk_register_available': True,
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'risk_count': len(risk_items),
        'open_count': sum(1 for item in risk_items if item['status'] == 'open'),
        'top_executor_risks': [item['risk_id'] for item in risk_items[:4]],
        'top_remaining_blockers': shared_blockers,
        'items': risk_items,
        'refs': {
            'executor_readiness_review': 'artifacts/executor_readiness_review.json',
            'executor_admission_review': 'artifacts/executor_admission_review.json',
            'executor_conformance_matrix': 'artifacts/executor_conformance_matrix.json',
            'future_executor_implementation_blueprint': 'artifacts/future_executor_implementation_blueprint.json',
            'real_executor_integration_checklist': 'artifacts/real_executor_integration_checklist.json',
            'real_executor_delivery_backlog': 'artifacts/real_executor_delivery_backlog.json',
            'executor_blocker_matrix': 'artifacts/executor_blocker_matrix.json',
        },
    }
    manager.write_json('executor_risk_register.json', risk_register_payload)
    manager.write_text('executor_risk_register.md', (
        '# executor risk register\n\n'
        + '\n'.join([
            '- risk_register_available: true',
            f"- risk_count: {risk_register_payload['risk_count']}",
            f"- open_count: {risk_register_payload['open_count']}",
            f"- top_remaining_blockers: {', '.join(shared_blockers)}",
        ] + [f"- {item['risk_id']}: severity={item['severity']}, status={item['status']}" for item in risk_items])
        + '\n'
    ))

    cutover_pack_payload = {
        'task_id': task_dir.name,
        'record_type': 'executor_cutover_readiness_pack',
        'generated_at': _now(),
        'cutover_pack_available': True,
        'cutover_state': 'final_pre_implementation_handoff_pack',
        'zero_real_execution_required': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'shared_status': {
            'handoff_boundary_ready': bool(handoff_boundary.get('handoff_boundary_ready')),
            'overall_admission_state': admission_review.get('overall_admission_state'),
            'overall_go_no_go_decision': go_no_go_pack.get('overall_decision'),
            'rollout_unmet_count': rollout_gate_registry.get('unmet_count', 0),
            'waiver_exception_count': waiver_exception_registry.get('waiver_exception_count', 0),
            'executor_unmet_gate_count': readiness_review.get('executor_unmet_gate_count', 0),
            'top_missing_executor_contracts': [item.get('gap_id') for item in (conformance_payload.get('top_missing_executor_contracts') or []) if item.get('gap_id')],
            'parity_gaps': list(parity_payload.get('parity_gaps') or []),
        },
        'targets': {
            target_key: {
                'execution_target': target_ready_map.get(target_key, {}).get('execution_target'),
                'ready_for_real_executor_handoff': bool((target_ready_map.get(target_key, {}) or {}).get('ready_for_real_executor_handoff')),
                'ready_for_future_executor': bool((target_admission_map.get(target_key, {}) or {}).get('ready_for_future_executor')),
                'go_no_go_decision': (target_decision_map.get(target_key, {}) or {}).get('decision'),
                'implementation_status': 'pending_real_executor_body',
                'remaining_blockers': [f'{target_key}_real_executor_missing'],
            }
            for target_key in ('release', 'rollback')
        },
        'top_executor_risks': [item['risk_id'] for item in risk_items[:4]],
        'top_remaining_blockers': shared_blockers,
        'refs': {
            'executor_readiness_review': 'artifacts/executor_readiness_review.json',
            'executor_admission_review': 'artifacts/executor_admission_review.json',
            'go_no_go_decision_pack': 'artifacts/go_no_go_decision_pack.json',
            'executor_conformance_matrix': 'artifacts/executor_conformance_matrix.json',
            'release_rollback_parity_matrix': 'artifacts/release_rollback_parity_matrix.json',
            'real_executor_integration_checklist': 'artifacts/real_executor_integration_checklist.json',
            'executor_risk_register': 'artifacts/executor_risk_register.json',
            'future_executor_handoff_summary': 'artifacts/future_executor_handoff_summary.json',
            'real_executor_delivery_backlog': 'artifacts/real_executor_delivery_backlog.json',
            'executor_acceptance_test_pack': 'artifacts/executor_acceptance_test_pack.json',
            'executor_blocker_matrix': 'artifacts/executor_blocker_matrix.json',
            'executor_ownership_split': 'artifacts/executor_ownership_split.json',
        },
        'note': 'This is the final cutover readiness pack before any future real executor implementation. It does not authorize or perform real execution.',
    }
    manager.write_json('executor_cutover_readiness_pack.json', cutover_pack_payload)
    manager.write_text('executor_cutover_readiness_pack.md', (
        '# executor cutover readiness pack\n\n'
        + '\n'.join([
            '- cutover_pack_available: true',
            '- cutover_state: final_pre_implementation_handoff_pack',
            f"- overall_admission_state: {cutover_pack_payload['shared_status']['overall_admission_state']}",
            f"- overall_go_no_go_decision: {cutover_pack_payload['shared_status']['overall_go_no_go_decision']}",
            f"- top_remaining_blockers: {', '.join(shared_blockers)}",
            '- note: this pack is the last delivery layer before future real executor implementation; current phase remains zero real execution.',
        ])
        + '\n'
    ))

    handoff_summary_payload = {
        'task_id': task_dir.name,
        'record_type': 'future_executor_handoff_summary',
        'generated_at': _now(),
        'handoff_summary_available': True,
        'handoff_state': 'ready_for_future_implementer_pickup',
        'zero_real_execution_required': True,
        'what_is_done': [
            'shared readiness/admission/go-no-go path is materialized',
            'release and rollback dry-run / receipt / handoff / traceability contracts are in place',
            'conformance / parity / error / rehearsal / compliance artifacts are generated',
            'cutover readiness pack / integration checklist / risk register are generated for final pre-implementation handoff',
        ],
        'what_is_not_done': [
            'real official release executor body is not implemented',
            'real rollback executor body is not implemented',
            'no external system writes are enabled or attempted',
        ],
        'next_implementer_must_do': [
            'implement real release and rollback adapter bodies behind the existing plugin interfaces',
            're-run checklist / conformance / rehearsal with the new adapters while preserving zero unauthorized execution',
            'obtain fresh manual cutover sign-off before enabling any real execution path',
        ],
        'top_executor_risks': [item['risk_id'] for item in risk_items[:4]],
        'top_remaining_blockers': shared_blockers,
        'refs': {
            'executor_cutover_readiness_pack': 'artifacts/executor_cutover_readiness_pack.json',
            'real_executor_integration_checklist': 'artifacts/real_executor_integration_checklist.json',
            'executor_risk_register': 'artifacts/executor_risk_register.json',
            'future_executor_implementation_blueprint': 'artifacts/future_executor_implementation_blueprint.json',
            'real_executor_delivery_backlog': 'artifacts/real_executor_delivery_backlog.json',
            'executor_acceptance_test_pack': 'artifacts/executor_acceptance_test_pack.json',
            'executor_blocker_matrix': 'artifacts/executor_blocker_matrix.json',
            'executor_ownership_split': 'artifacts/executor_ownership_split.json',
        },
    }
    manager.write_json('future_executor_handoff_summary.json', handoff_summary_payload)
    manager.write_text('future_executor_handoff_summary.md', (
        '# future executor handoff summary\n\n'
        + '\n'.join([
            '- handoff_summary_available: true',
            '- handoff_state: ready_for_future_implementer_pickup',
            f"- top_remaining_blockers: {', '.join(shared_blockers)}",
            '- note: handoff is complete for the packaging layer only; no real executor is implemented here.',
        ] + [f"- done: {item}" for item in handoff_summary_payload['what_is_done']] + [f"- not_done: {item}" for item in handoff_summary_payload['what_is_not_done']])
        + '\n'
    ))
    return {'executor_conformance_matrix': conformance_payload,'executor_error_contract': error_payload,'release_rollback_parity_matrix': parity_payload,'future_executor_implementation_blueprint': blueprint_payload,'real_executor_delivery_backlog': delivery_backlog_payload,'executor_acceptance_test_pack': acceptance_test_pack_payload,'executor_ownership_split': ownership_split_payload,'executor_blocker_matrix': blocker_matrix_payload,'executor_credential_binding_policy': credential_binding_policy_payload,'executor_target_binding_registry': target_binding_registry_payload,'credential_binding_evidence_checklist': credential_binding_evidence_checklist_payload,'cutover_signoff_workflow': cutover_signoff_workflow_payload,'cutover_signoff_evidence_packet': cutover_signoff_evidence_packet_payload,'blocker_drilldown_review': blocker_drilldown_payload,'executor_human_action_pack': executor_human_action_pack_payload,'pending_human_action_board': pending_human_action_board_payload,'unresolved_blocker_tracker': unresolved_blocker_tracker_payload,'credential_binding_runbook': credential_binding_runbook_payload,'cutover_signoff_runbook': cutover_signoff_runbook_payload,'blocker_resolution_playbook': blocker_resolution_playbook_payload,'real_executor_integration_checklist': integration_checklist_payload,'executor_risk_register': risk_register_payload,'executor_cutover_readiness_pack': cutover_pack_payload,'future_executor_handoff_summary': handoff_summary_payload}


def build_rollout_gate_registry(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    manager = ArtifactManager(task_dir)
    deps = _load_execution_control_dependencies(task_dir)
    readiness_review = deps['readiness_review']
    handoff_boundary = deps['handoff_boundary']
    capability_registry = deps['capability_registry']
    invocation_policy = deps['invocation_policy']
    simulated_executor_run = deps['simulated_executor_run']
    contract_compliance_matrix = deps['contract_compliance_matrix']
    executor_integration_rehearsal = deps['executor_integration_rehearsal']
    release_manifest = deps['release_adapter_manifest']
    rollback_manifest = deps['rollback_adapter_manifest']

    shared_defs = [
        {
            'gate_id': 'shared_readiness_gates_passed',
            'title': 'Shared readiness gates passed',
            'severity': 'blocker',
            'waiver_allowed': False,
            'details': 'Release and rollback must both have zero unmet readiness gates.',
            'passed': int(readiness_review.get('executor_unmet_gate_count', 0) or 0) == 0,
            'evidence_refs': ['artifacts/executor_readiness_review.json'],
        },
        {
            'gate_id': 'handoff_boundary_ready',
            'title': 'Handoff boundary ready',
            'severity': 'blocker',
            'waiver_allowed': False,
            'details': 'Future executor integration may only proceed after the shared handoff boundary is ready.',
            'passed': bool(handoff_boundary.get('handoff_boundary_ready')),
            'evidence_refs': ['artifacts/real_executor_handoff_boundary.json'],
        },
        {
            'gate_id': 'adapter_manifests_present',
            'title': 'Adapter manifests present',
            'severity': 'blocker',
            'waiver_allowed': False,
            'details': 'Both release and rollback must publish adapter manifests and capability metadata.',
            'passed': bool(release_manifest) and bool(rollback_manifest) and bool(capability_registry.get('registry_available')),
            'evidence_refs': [
                f"artifacts/{TARGETS['release']['adapter_manifest_artifact']}",
                f"artifacts/{TARGETS['rollback']['adapter_manifest_artifact']}",
                'artifacts/executor_capability_registry.json',
            ],
        },
        {
            'gate_id': 'environment_guards_clean',
            'title': 'Environment guards clean',
            'severity': 'blocker',
            'waiver_allowed': False,
            'details': 'Manual-only environment guards must pass on both sides.',
            'passed': bool((release_manifest.get('environment_guard') or {}).get('guard_ok')) and bool((rollback_manifest.get('environment_guard') or {}).get('guard_ok')),
            'evidence_refs': [
                f"artifacts/{TARGETS['release']['adapter_manifest_artifact']}",
                f"artifacts/{TARGETS['rollback']['adapter_manifest_artifact']}",
            ],
        },
        {
            'gate_id': 'invocation_policy_reviewed',
            'title': 'Invocation policy reviewed',
            'severity': 'blocker',
            'waiver_allowed': False,
            'details': 'The shared invocation policy must exist and still disallow real execution.',
            'passed': bool(invocation_policy.get('policy_available')) and 'real_execute' in list(invocation_policy.get('disallowed_invocation_modes') or []),
            'evidence_refs': ['artifacts/invocation_policy_review.json'],
        },
        {
            'gate_id': 'simulation_rehearsal_complete',
            'title': 'Simulation rehearsal complete',
            'severity': 'waiverable',
            'waiver_allowed': True,
            'details': 'Both targets should complete simulation rehearsal before future admission.',
            'passed': int(simulated_executor_run.get('available_count', 0) or 0) >= 2 and int(simulated_executor_run.get('fail_count', 0) or 0) == 0 and bool(executor_integration_rehearsal.get('integration_rehearsal_available')),
            'evidence_refs': ['artifacts/simulated_executor_run.json', 'artifacts/executor_integration_rehearsal.json'],
        },
        {
            'gate_id': 'contract_compliance_proven',
            'title': 'Contract compliance proven',
            'severity': 'waiverable',
            'waiver_allowed': True,
            'details': 'Contract compliance matrix should confirm protocol fit for future executor wiring.',
            'passed': bool(contract_compliance_matrix.get('contract_compliance_available')) and not list(contract_compliance_matrix.get('top_executor_contract_gaps') or []),
            'evidence_refs': ['artifacts/contract_compliance_matrix.json'],
        },
        {
            'gate_id': 'zero_real_execution_preserved',
            'title': 'Zero real execution preserved',
            'severity': 'blocker',
            'waiver_allowed': False,
            'details': 'Admission governance never overrides the no-real-execution boundary of the current runtime.',
            'passed': bool(handoff_boundary.get('boundary_assertions', {}).get('zero_real_execution_observed', True)) and bool(simulated_executor_run.get('zero_real_execution_observed', True)),
            'evidence_refs': ['artifacts/real_executor_handoff_boundary.json', 'artifacts/simulated_executor_run.json'],
        },
    ]

    targets = {}
    for target in ('release', 'rollback'):
        target_readiness = ((readiness_review.get('targets') or {}).get(target) or {})
        target_manifest = deps[f'{target}_adapter_manifest']
        target_gates = []
        for gate in shared_defs:
            target_gates.append({
                'gate_id': gate['gate_id'],
                'title': gate['title'],
                'severity': gate['severity'],
                'waiver_allowed': gate['waiver_allowed'],
                'status': 'passed' if gate['passed'] else 'unmet',
                'passed': gate['passed'],
                'evidence_refs': gate['evidence_refs'],
            })
        # target-local traceability annotation
        targets[target] = {
            'execution_target': target,
            'executor_name': TARGETS[target]['executor_name'],
            'batch_id': target_readiness.get('batch_id'),
            'run_id': target_readiness.get('run_id'),
            'gate_count': len(target_gates),
            'unmet_gate_count': len([g for g in target_gates if not g['passed']]),
            'blocking_gate_ids': [g['gate_id'] for g in target_gates if (not g['passed']) and g['severity'] == 'blocker'],
            'waiver_candidate_gate_ids': [g['gate_id'] for g in target_gates if (not g['passed']) and g['waiver_allowed']],
            'readiness_reference': 'artifacts/executor_readiness_review.json',
            'handoff_reference': f"artifacts/{TARGETS[target]['handoff_artifact']}",
            'adapter_manifest_reference': f"artifacts/{TARGETS[target]['adapter_manifest_artifact']}",
            'simulation_reference': 'artifacts/simulated_executor_run.json',
            'gates': target_gates,
            'environment_guard_ok': bool((target_manifest.get('environment_guard') or {}).get('guard_ok')),
        }

    all_gates = [g for t in targets.values() for g in t['gates']]
    unmet = [g for g in all_gates if not g['passed']]
    top_blocking = []
    seen = set()
    for gate in unmet:
        if gate['severity'] == 'blocker' and gate['gate_id'] not in seen:
            seen.add(gate['gate_id']); top_blocking.append(gate['gate_id'])
    registry = {
        'task_id': task_dir.name,
        'record_type': 'rollout_gate_registry',
        'generated_at': _now(),
        'shared_rule_family': 'release_rollback_executor_admission_governance',
        'current_scope': 'future_real_executor_integration_only',
        'gate_catalog': [{k: gate[k] for k in ('gate_id', 'title', 'severity', 'waiver_allowed', 'details')} for gate in shared_defs],
        'targets': targets,
        'rollout_gate_count': len(shared_defs),
        'unmet_count': len({g['gate_id'] for g in unmet}),
        'blocking_unmet_count': len({g['gate_id'] for g in unmet if g['severity'] == 'blocker'}),
        'waiver_candidate_count': len({g['gate_id'] for g in unmet if g['waiver_allowed']}),
        'top_blocking_gates': top_blocking[:5],
        'top_unmet_gates': list(dict.fromkeys([g['gate_id'] for g in unmet]))[:5],
        'zero_real_execution_enforced': True,
        'automatic_release_or_rollback_still_forbidden': True,
        'note': 'Registry defines rollout admission gates only; it does not perform any release/rollback action.',
    }
    manager.write_json('rollout_gate_registry.json', registry)
    return registry


def build_waiver_exception_registry(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    manager = ArtifactManager(task_dir)
    rollout = _load_json(task_dir / 'artifacts' / 'rollout_gate_registry.json') or build_rollout_gate_registry(task_dir)
    protocol = {
        'waiver_allowed_only_for': ['simulation_rehearsal_complete', 'contract_compliance_proven'],
        'waiver_never_allows': [
            'automatic_real_release_execution',
            'automatic_real_rollback_execution',
            'writing_to_external_systems',
            'bypassing_human_approval',
        ],
        'approval_rule': 'record_only_manual_exception_tracking_no_automatic_pass_through',
        'expiry_rule': 'all waivers require explicit expiry and reviewer note before future implementation work can continue',
    }
    items = []
    for target, info in (rollout.get('targets') or {}).items():
        for gate_id in list(info.get('waiver_candidate_gate_ids') or []):
            items.append({
                'waiver_id': f'waiver-{target}-{gate_id}',
                'execution_target': target,
                'gate_id': gate_id,
                'waiver_state': 'open',
                'status': 'recorded_not_approved',
                'automatic_pass_through': False,
                'future_executor_unblocked': False,
                'reason_required': True,
                'reviewer_required': True,
                'evidence_refs': ['artifacts/rollout_gate_registry.json'],
            })
    registry = {
        'task_id': task_dir.name,
        'record_type': 'waiver_exception_registry',
        'generated_at': _now(),
        'shared_rule_family': 'release_rollback_executor_admission_governance',
        'protocol': protocol,
        'waiver_exception_count': len(items),
        'open_waiver_count': len(items),
        'approved_waiver_count': 0,
        'expired_waiver_count': 0,
        'active_waivers': items,
        'note': 'Waivers are tracked as governance exceptions only. They never auto-authorize real execution.',
    }
    manager.write_json('waiver_exception_registry.json', registry)
    return registry


def build_executor_admission_artifacts(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    manager = ArtifactManager(task_dir)
    readiness_review = _load_json(task_dir / 'artifacts' / 'executor_readiness_review.json') or build_executor_readiness_artifacts(task_dir)['review']
    rollout = _load_json(task_dir / 'artifacts' / 'rollout_gate_registry.json') or build_rollout_gate_registry(task_dir)
    waiver = _load_json(task_dir / 'artifacts' / 'waiver_exception_registry.json') or build_waiver_exception_registry(task_dir)
    simulated = _load_json(task_dir / 'artifacts' / 'simulated_executor_run.json') or {}
    compliance = _load_json(task_dir / 'artifacts' / 'contract_compliance_matrix.json') or {}
    rehearsal = _load_json(task_dir / 'artifacts' / 'executor_integration_rehearsal.json') or {}

    top_blocking = list(rollout.get('top_blocking_gates') or [])
    if top_blocking:
        overall = 'blocked'
    elif int(waiver.get('open_waiver_count', 0) or 0) > 0:
        overall = 'conditional'
    else:
        overall = 'ready_for_future_executor'
    target_reviews = {}
    for target in ('release', 'rollback'):
        readiness_target = ((readiness_review.get('targets') or {}).get(target) or {})
        rollout_target = ((rollout.get('targets') or {}).get(target) or {})
        waiver_items = [item for item in list(waiver.get('active_waivers') or []) if item.get('execution_target') == target]
        target_blockers = list(rollout_target.get('blocking_gate_ids') or [])
        if target_blockers:
            state = 'blocked'
        elif waiver_items:
            state = 'conditional'
        else:
            state = 'ready_for_future_executor'
        target_reviews[target] = {
            'execution_target': target,
            'admission_state': state,
            'ready_for_future_executor': state == 'ready_for_future_executor',
            'blocking_gate_ids': target_blockers,
            'waiver_exception_ids': [item['waiver_id'] for item in waiver_items],
            'run_id': readiness_target.get('run_id'),
            'batch_id': readiness_target.get('batch_id'),
            'references': {
                'readiness_review': 'artifacts/executor_readiness_review.json',
                'handoff_packet': f"artifacts/{TARGETS[target]['handoff_artifact']}",
                'adapter_manifest': f"artifacts/{TARGETS[target]['adapter_manifest_artifact']}",
                'rollout_gate_registry': 'artifacts/rollout_gate_registry.json',
                'waiver_exception_registry': 'artifacts/waiver_exception_registry.json',
                'simulation_harness': 'artifacts/simulated_executor_run.json',
            },
        }
    admission = {
        'task_id': task_dir.name,
        'record_type': 'executor_admission_review',
        'generated_at': _now(),
        'shared_rule_family': 'release_rollback_executor_admission_governance',
        'review_scope': 'future_real_executor_integration_only',
        'overall_admission_state': overall,
        'executor_admission_available': True,
        'rollout_gate_count': rollout.get('rollout_gate_count', 0),
        'rollout_unmet_count': rollout.get('unmet_count', 0),
        'waiver_exception_count': waiver.get('waiver_exception_count', 0),
        'top_blocking_gates': top_blocking,
        'targets': target_reviews,
        'shared_references': {
            'readiness_review': 'artifacts/executor_readiness_review.json',
            'rollout_gate_registry': 'artifacts/rollout_gate_registry.json',
            'waiver_exception_registry': 'artifacts/waiver_exception_registry.json',
            'simulation_harness': 'artifacts/simulated_executor_run.json',
            'contract_compliance_matrix': 'artifacts/contract_compliance_matrix.json',
            'integration_rehearsal': 'artifacts/executor_integration_rehearsal.json',
        },
        'zero_real_execution_assertion': {
            'real_execution_enabled': False,
            'external_side_effects': False,
            'simulation_zero_real_execution_observed': bool(simulated.get('zero_real_execution_observed', True)),
            'contract_compliance_available': bool(compliance.get('contract_compliance_available')),
            'integration_rehearsal_available': bool(rehearsal.get('integration_rehearsal_available')),
        },
        'note': 'Admission review is a governance decision layer for future executor connection only; it does not execute release or rollback.',
    }
    go_no_go = {
        'task_id': task_dir.name,
        'record_type': 'go_no_go_decision_pack',
        'generated_at': _now(),
        'decision_scope': 'future_real_executor_integration_only',
        'go_no_go_available': True,
        'overall_admission_state': overall,
        'overall_decision': 'go' if overall == 'ready_for_future_executor' else 'no_go',
        'top_blocking_gates': top_blocking,
        'waiver_exception_count': waiver.get('waiver_exception_count', 0),
        'targets': {
            target: {
                'decision': 'go' if review['admission_state'] == 'ready_for_future_executor' else 'no_go',
                'admission_state': review['admission_state'],
                'blocking_gate_ids': review['blocking_gate_ids'],
                'waiver_exception_ids': review['waiver_exception_ids'],
                'future_executor_only': True,
                'real_execution_still_disabled': True,
            }
            for target, review in target_reviews.items()
        },
        'required_human_followthrough': [
            'separate future implementation of real release executor',
            'separate future implementation of real rollback executor',
            'manual review of any waiver before future integration',
        ],
        'references': admission['shared_references'],
        'note': 'No-go/go pack records governance posture only. It never flips the runtime into real execution.',
    }
    manager.write_json('executor_admission_review.json', admission)
    manager.write_text('executor_admission_review.md', "\n".join([
        '# executor admission review', '',
        f"- overall_admission_state: {overall}",
        "- executor_admission_available: true",
        f"- rollout_gate_count: {admission['rollout_gate_count']}",
        f"- rollout_unmet_count: {admission['rollout_unmet_count']}",
        f"- waiver_exception_count: {admission['waiver_exception_count']}",
        f"- top_blocking_gates: {', '.join(top_blocking) if top_blocking else 'none'}",
        '- note: future real executor integration governance only; zero real execution remains enforced.',
    ]) + "\n")
    manager.write_json('go_no_go_decision_pack.json', go_no_go)
    manager.write_text('go_no_go_decision_pack.md', "\n".join([
        '# go/no-go decision pack', '',
        f"- overall_decision: {go_no_go['overall_decision']}",
        f"- overall_admission_state: {overall}",
        "- go_no_go_available: true",
        f"- waiver_exception_count: {go_no_go['waiver_exception_count']}",
        f"- top_blocking_gates: {', '.join(top_blocking) if top_blocking else 'none'}",
        '- note: records governance decision only; no release/rollback execution occurs here.',
    ]) + "\n")
    return {'admission_review': admission, 'go_no_go_decision_pack': go_no_go, 'rollout_gate_registry': rollout, 'waiver_exception_registry': waiver}


def build_executor_readiness_artifacts(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    manager = ArtifactManager(task_dir)
    closure_snapshot = load_release_closure_snapshot(task_dir)
    target_reviews = {
        'release': _build_target_readiness_review(task_dir, target='release', closure_snapshot=closure_snapshot),
        'rollback': _build_target_readiness_review(task_dir, target='rollback', closure_snapshot=closure_snapshot),
    }
    top_unmet_counter: Counter[str] = Counter()
    for review in target_reviews.values():
        top_unmet_counter.update(review.get('unmet_gate_ids', []))
    top_unmet_gates = [gate_id for gate_id, _count in sorted(top_unmet_counter.items(), key=lambda item: (-item[1], item[0]))[:5]]
    gate_count = sum(int(review.get('gate_count', 0) or 0) for review in target_reviews.values())
    unmet_gate_count = sum(int(review.get('unmet_gate_count', 0) or 0) for review in target_reviews.values())

    release_contract = _load_json(task_dir / 'artifacts' / TARGETS['release']['contract_artifact'])
    rollback_contract = _load_json(task_dir / 'artifacts' / TARGETS['rollback']['contract_artifact'])
    contracts_manual_only = all([
        (release_contract or {}).get('execution_mode') == 'dry_run_only',
        (rollback_contract or {}).get('execution_mode') == 'dry_run_only',
        (release_contract or {}).get('auto_execution_enabled') is False,
        (rollback_contract or {}).get('auto_execution_enabled') is False,
        (release_contract or {}).get('external_side_effects_allowed') is False,
        (rollback_contract or {}).get('external_side_effects_allowed') is False,
    ])
    handoff_boundary_ready = gate_count > 0 and unmet_gate_count == 0 and contracts_manual_only

    review_payload = {
        'task_id': task_dir.name,
        'record_type': 'executor_readiness_review',
        'review_scope': 'real_executor_pre_integration_safety_boundary',
        'generated_at': _now(),
        'shared_gate_catalog': [{k: gate[k] for k in ('gate_id', 'title', 'severity', 'description')} for gate in SHARED_GATE_DEFINITIONS],
        'targets': target_reviews,
        'executor_readiness_gate_count': gate_count,
        'executor_unmet_gate_count': unmet_gate_count,
        'top_unmet_executor_gates': top_unmet_gates,
        'readiness_gate_counts': {name: review.get('gate_count', 0) for name, review in target_reviews.items()},
        'unmet_gate_counts': {name: review.get('unmet_gate_count', 0) for name, review in target_reviews.items()},
        'handoff_boundary_ready': handoff_boundary_ready,
        'note': 'This review defines pre-integration safety gates only. It does not authorize or implement any real release/rollback execution.',
    }

    handoff_payload = {
        'task_id': task_dir.name,
        'record_type': 'real_executor_handoff_boundary',
        'generated_at': _now(),
        'handoff_boundary_ready': handoff_boundary_ready,
        'future_real_executor_connection_allowed': handoff_boundary_ready,
        'real_executor_connected': False,
        'real_execution_enabled': False,
        'manual_trigger_required': True,
        'shared_rulebook': 'release and rollback must satisfy the same readiness/safety gate set before any future real executor integration.',
        'required_conditions_met': [gate['gate_id'] for gate in SHARED_GATE_DEFINITIONS if gate['gate_id'] not in top_unmet_counter],
        'unmet_conditions': top_unmet_gates,
        'boundary_assertions': {
            'contracts_manual_only': contracts_manual_only,
            'zero_real_execution_required': True,
            'zero_real_execution_observed': all(
                gate_id != 'zero_real_execution_artifacts' or count == 0
                for gate_id, count in top_unmet_counter.items()
            ),
            'dry_run_traceability_required': True,
            'approval_before_any_future_real_executor': True,
            'paired_release_rollback_handoff': True,
        },
        'next_allowed_step': 'handoff_real_executor_integration_requirements_to_future_implementation' if handoff_boundary_ready else 'close_unmet_readiness_gates_before_any_real_executor_connection',
        'blocked_step': 'automatic_real_release_or_rollback_execution',
        'note': 'Boundary is a handoff artifact for future implementation only. Even when ready=true, the current runtime remains dry-run-only and zero-side-effect.',
    }

    markdown_lines = [
        '# executor readiness review',
        '',
        f"- task_id: {task_dir.name}",
        f"- executor_readiness_gate_count: {gate_count}",
        f"- executor_unmet_gate_count: {unmet_gate_count}",
        f"- top_unmet_executor_gates: {', '.join(top_unmet_gates) if top_unmet_gates else 'none'}",
        f"- handoff_boundary_ready: {str(handoff_boundary_ready).lower()}",
        '- note: this is a pre-integration safety threshold, not a real executor implementation.',
        '',
    ]
    for target_name, review in target_reviews.items():
        markdown_lines.extend([
            f"## {target_name}",
            '',
            f"- gate_count: {review.get('gate_count')}",
            f"- unmet_gate_count: {review.get('unmet_gate_count')}",
            f"- ready_for_real_executor_handoff: {str(bool(review.get('ready_for_real_executor_handoff'))).lower()}",
            f"- unmet_gate_ids: {', '.join(review.get('unmet_gate_ids') or []) if review.get('unmet_gate_ids') else 'none'}",
            '',
        ])

    manager.write_json('executor_readiness_review.json', review_payload)
    manager.write_text('executor_readiness_review.md', '\n'.join(markdown_lines).rstrip() + '\n')
    manager.write_json('real_executor_handoff_boundary.json', handoff_payload)
    return {'review': review_payload, 'handoff_boundary': handoff_payload}


def materialize_controlled_executor(task_dir: str | Path, *, target: str) -> dict[str, Any]:
    task_dir = Path(task_dir)
    manager = ArtifactManager(task_dir)
    cfg = TARGETS[target]
    contract = _build_contract(task_dir, target)
    manager.write_json(cfg['contract_artifact'], contract)
    manager.write_json('execution_receipt.schema.json', _load_json(PROTOCOLS / 'execution_receipt.schema.json'))
    manager.write_text(cfg['review_artifact'], (
        f"# {cfg['executor_name']} contract review\n\n"
        f"- target: {cfg['label']}\n"
        f"- execution_mode: dry_run_only\n"
        f"- auto_execution_enabled: false\n"
        f"- external_side_effects_allowed: false\n"
        f"- batch_id: {contract['batch_id']}\n"
        f"- run_id: {contract['run_id']}\n"
        f"- receipt_schema_reference: {contract['receipt_schema_reference']}\n"
        f"- required_trace_fields: {', '.join(contract['required_trace_fields'])}\n"
        f"- note: Contract is ready for dry-run validation only; real execution remains intentionally unimplemented.\n"
    ))
    build_executor_adapter_artifacts(task_dir)
    build_future_executor_scaffold_artifacts(task_dir)
    build_executor_readiness_artifacts(task_dir)
    build_rollout_gate_registry(task_dir)
    build_waiver_exception_registry(task_dir)
    build_executor_admission_artifacts(task_dir)
    build_executor_contract_artifacts(task_dir)
    return contract


def dry_run_controlled_execution(task_dir: str | Path, *, target: str, requested_by: str, proposal_ref: str, approval_ref: str) -> dict[str, Any]:
    task_dir = Path(task_dir)
    manager = ArtifactManager(task_dir)
    cfg = TARGETS[target]
    contract = _load_json(task_dir / 'artifacts' / cfg['contract_artifact']) or materialize_controlled_executor(task_dir, target=target)
    closure_snapshot = load_release_closure_snapshot(task_dir)
    run_context = get_execution_run_context(task_dir, target)
    command_preview = cfg['command_template'].format(task_id=task_dir.name, batch_id=run_context['batch_id'], run_id=run_context['run_id'])
    request_payload = {
        'task_id': task_dir.name,
        'record_type': 'controlled_execution_request',
        'execution_target': cfg['label'],
        'execution_mode': 'dry_run',
        'requested_by': requested_by,
        'requested_at': _now(),
        'proposal_ref': proposal_ref,
        'approval_ref': approval_ref,
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'command_preview': command_preview,
        'note': 'Dry-run request only. No executable command is dispatched to any external system.',
    }
    manager.write_json(cfg['request_artifact'], request_payload)

    validation_checks = {
        'contract_available': bool(contract),
        'approval_recorded': closure_snapshot.get('human_approval_state') == 'approved',
        'execution_batch_bound': bool(run_context.get('batch_id') and run_context.get('run_id')),
        'receipt_schema_available': bool(_load_json(PROTOCOLS / 'execution_receipt.schema.json')),
        'release_artifact_binding_ready': bool(closure_snapshot.get('release_artifact_binding_ready')),
        'rollback_supported': bool(closure_snapshot.get('rollback_supported')),
        'real_execution_attempted': False,
    }
    validated = all(value for key, value in validation_checks.items() if key != 'real_execution_attempted')
    command_digest = _sha256(command_preview)
    dry_run_payload = {
        'task_id': task_dir.name,
        'record_type': 'controlled_execution_dry_run',
        'execution_target': cfg['label'],
        'execution_mode': 'dry_run',
        'dry_run_validated': validated,
        'validation_checks': validation_checks,
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'contract_reference': f"artifacts/{cfg['contract_artifact']}",
        'request_reference': f"artifacts/{cfg['request_artifact']}",
        'proposal_ref': proposal_ref,
        'approval_ref': approval_ref,
        'command_preview': command_preview,
        'command_digest_sha256': command_digest,
        'command_receipt_id': f"receipt-{target}-{command_digest[:12]}",
        'side_effects_performed': [],
        'side_effect_count': 0,
        'real_execution_attempted': False,
        'note': 'Dry-run adapter validated contract and traceability fields only. No release/rollback executor was called.',
        'generated_at': _now(),
    }
    manager.write_json(cfg['dry_run_artifact'], dry_run_payload)

    receipt_payload = {
        'task_id': task_dir.name,
        'record_type': 'controlled_execution_receipt',
        'execution_target': cfg['label'],
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'receipt_state': 'recorded_dry_run_only',
        'execution_mode': 'dry_run',
        'contract_reference': f"artifacts/{cfg['contract_artifact']}",
        'request_reference': f"artifacts/{cfg['request_artifact']}",
        'dry_run_reference': f"artifacts/{cfg['dry_run_artifact']}",
        'receipt_trace': {
            'proposal_ref': proposal_ref,
            'approval_ref': approval_ref,
            'batch_id': run_context['batch_id'],
            'run_id': run_context['run_id'],
            'command_receipt_id': dry_run_payload['command_receipt_id'],
            'command_digest_sha256': command_digest,
        },
        'generated_at': _now(),
        'note': 'Mock receipt recorded for audit/traceability only. This receipt never implies real release/rollback execution happened.',
    }
    manager.write_json(cfg['receipt_artifact'], receipt_payload)
    handoff_layer = _materialize_handoff_layer(task_dir=task_dir, target=target, requested_by=requested_by, proposal_ref=proposal_ref, approval_ref=approval_ref, command_preview=command_preview)
    lifecycle = _record_request_lifecycle_event(
        task_dir=task_dir,
        target=target,
        action='requested',
        state='requested',
        acted_by=requested_by,
        note='execution request issued to operator intent/acknowledgement layer',
        operator_role='requester',
    )

    states = _states(
        closure_snapshot=closure_snapshot,
        request_recorded=True,
        dry_run_validated=validated,
        receipt_recorded=True,
        execution_target=target,
    )
    readiness_bundle = build_executor_readiness_artifacts(task_dir)
    summary = _write_execution_control_summary(task_dir)
    return {
        'task_id': task_dir.name,
        'execution_target': cfg['label'],
        'states': states,
        'dry_run_validated': validated,
        'real_execution_attempted': False,
        'command_receipt_id': dry_run_payload['command_receipt_id'],
        'command_digest_sha256': command_digest,
        'executor_readiness_gate_count': readiness_bundle['review'].get('executor_readiness_gate_count'),
        'executor_unmet_gate_count': readiness_bundle['review'].get('executor_unmet_gate_count'),
        'top_unmet_executor_gates': readiness_bundle['review'].get('top_unmet_executor_gates'),
        'handoff_boundary_ready': readiness_bundle['handoff_boundary'].get('handoff_boundary_ready'),
        'handoff_packet_available': bool(handoff_layer.get('handoff_packet')),
        'operator_execution_request_available': bool(handoff_layer.get('operator_request')),
        'receipt_correlation_ready': bool((handoff_layer.get('review') or {}).get('receipt_correlation_ready')),
        'request_state': (((lifecycle.get('requests') or {}).get(target) or {}).get('request_state')),
        'summary': summary,
    }


def _build_executor_simulation_artifacts(task_dir: Path) -> dict[str, Any]:
    manager = ArtifactManager(task_dir)
    shared_contract_checks = [
        ('request_recorded', 'request artifact present and linked'),
        ('handoff_packet_available', 'handoff packet materialized'),
        ('adapter_manifest_available', 'adapter manifest available'),
        ('contract_validation_ready', 'executor contract materialized'),
        ('dry_run_result_available', 'dry-run result recorded'),
        ('receipt_recorded', 'mock receipt recorded'),
        ('readiness_boundary_visible', 'readiness review / handoff boundary visible'),
        ('zero_real_execution', 'no real execution artifacts present'),
    ]
    target_results: list[dict[str, Any]] = []
    gap_counter: Counter[str] = Counter()
    top_gaps: list[dict[str, Any]] = []
    pass_count = 0
    fail_count = 0
    for target in ('release', 'rollback'):
        cfg = TARGETS[target]
        contract = _load_json(task_dir / 'artifacts' / cfg['contract_artifact']) or {}
        request = _load_json(task_dir / 'artifacts' / cfg['request_artifact']) or {}
        dry_run = _load_json(task_dir / 'artifacts' / cfg['dry_run_artifact']) or {}
        receipt = _load_json(task_dir / 'artifacts' / cfg['receipt_artifact']) or {}
        handoff = _load_json(task_dir / 'artifacts' / cfg['handoff_artifact']) or {}
        adapter_manifest = _load_json(task_dir / 'artifacts' / cfg['adapter_manifest_artifact']) or {}
        run_context = get_execution_run_context(task_dir, target)
        readiness_review = _load_json(task_dir / 'artifacts' / 'executor_readiness_review.json') or {}
        handoff_boundary = _load_json(task_dir / 'artifacts' / 'real_executor_handoff_boundary.json') or {}
        lifecycle = (_load_execution_request_lifecycle(task_dir).get('requests') or {}).get(target) or {}
        target_readiness = ((readiness_review.get('targets') or {}).get(target) or {})
        zero_real_execution = not (task_dir / 'artifacts' / cfg['forbidden_real_artifact']).exists()
        checks = {
            'request_recorded': bool(request),
            'handoff_packet_available': bool(handoff),
            'adapter_manifest_available': bool(adapter_manifest),
            'contract_validation_ready': bool(contract) and contract.get('execution_mode') == 'dry_run_only',
            'dry_run_result_available': bool(dry_run) and bool(dry_run.get('dry_run_validated')),
            'receipt_recorded': bool(receipt) and _trace_complete(receipt, expected_batch_id=run_context.get('batch_id'), expected_run_id=run_context.get('run_id')),
            'readiness_boundary_visible': bool(target_readiness) and bool(handoff_boundary),
            'zero_real_execution': zero_real_execution,
        }
        gaps = [key for key, value in checks.items() if not value]
        for gap in gaps:
            gap_counter[gap] += 1
        target_pass = all(checks.values())
        if target_pass:
            pass_count += 1
        else:
            fail_count += 1
        target_results.append({
            'execution_target': cfg['label'],
            'batch_id': run_context.get('batch_id'),
            'run_id': run_context.get('run_id'),
            'request_state': lifecycle.get('request_state'),
            'dry_run_validated': bool(dry_run.get('dry_run_validated')),
            'receipt_trace_complete': bool(receipt) and _trace_complete(receipt, expected_batch_id=run_context.get('batch_id'), expected_run_id=run_context.get('run_id')),
            'simulation_passed': target_pass,
            'contract_gaps': gaps,
            'checks': checks,
        })
    for gap, count in gap_counter.most_common(5):
        top_gaps.append({'gap_id': gap, 'affected_targets': count})

    simulated_run = {
        'task_id': task_dir.name,
        'record_type': 'simulated_executor_run',
        'generated_at': _now(),
        'simulation_scope': 'executor_simulation_harness',
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'real_execution_enabled': False,
        'external_side_effects_allowed': False,
        'zero_real_execution_observed': all(item['checks']['zero_real_execution'] for item in target_results),
        'available_count': len(target_results),
        'pass_count': pass_count,
        'fail_count': fail_count,
        'top_executor_contract_gaps': top_gaps,
        'targets': target_results,
        'note': 'Simulation harness rehearses request->handoff->adapter->validation->dry-run->receipt->boundary only. No real release/rollback is executed.',
    }
    manager.write_json('simulated_executor_run.json', simulated_run)

    compliance_targets = []
    for item in target_results:
        compliance_targets.append({
            'execution_target': item['execution_target'],
            'all_requirements_met': item['simulation_passed'],
            'requirements': [
                {
                    'requirement_id': requirement_id,
                    'description': description,
                    'status': 'pass' if item['checks'][requirement_id] else 'gap',
                }
                for requirement_id, description in shared_contract_checks
            ],
            'contract_gaps': item['contract_gaps'],
        })
    contract_compliance = {
        'task_id': task_dir.name,
        'record_type': 'contract_compliance_matrix',
        'generated_at': _now(),
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'contract_compliance_available': True,
        'requirement_count': len(shared_contract_checks),
        'target_count': len(compliance_targets),
        'pass_count': pass_count,
        'fail_count': fail_count,
        'top_executor_contract_gaps': top_gaps,
        'targets': compliance_targets,
        'real_execution_enabled': False,
    }
    manager.write_json('contract_compliance_matrix.json', contract_compliance)
    manager.write_text('contract_compliance_matrix.md', '\n'.join([
        '# contract compliance matrix',
        '',
        f"- contract_compliance_available: true",
        f"- pass_count: {pass_count}",
        f"- fail_count: {fail_count}",
        f"- top_executor_contract_gaps: {', '.join([g['gap_id'] for g in top_gaps]) if top_gaps else 'none'}",
        '- note: shared release/rollback simulation contract only; zero real execution.',
        '',
    ] + [
        f"## {item['execution_target']}\n" + '\n'.join([f"- {req['requirement_id']}: {req['status']}" for req in item['requirements']])
        for item in compliance_targets
    ]) + '\n')

    rehearsal = {
        'task_id': task_dir.name,
        'record_type': 'executor_integration_rehearsal',
        'generated_at': _now(),
        'integration_rehearsal_available': True,
        'shared_rule_family': 'release_rollback_controlled_executor_policy',
        'rehearsal_chain': ['request', 'ack_or_acceptance_visible', 'handoff_packet', 'adapter_manifest', 'contract_validation', 'dry_run_result', 'receipt_recording', 'readiness_handoff_boundary'],
        'available_count': len(target_results),
        'pass_count': pass_count,
        'fail_count': fail_count,
        'top_executor_contract_gaps': top_gaps,
        'targets': [
            {
                'execution_target': item['execution_target'],
                'request_state': item['request_state'],
                'rehearsal_passed': item['simulation_passed'],
                'stages': {
                    'request': item['checks']['request_recorded'],
                    'ack_or_acceptance_visible': bool(item['request_state']),
                    'handoff_packet': item['checks']['handoff_packet_available'],
                    'adapter_manifest': item['checks']['adapter_manifest_available'],
                    'contract_validation': item['checks']['contract_validation_ready'],
                    'dry_run_result': item['checks']['dry_run_result_available'],
                    'receipt_recording': item['checks']['receipt_recorded'],
                    'readiness_handoff_boundary': item['checks']['readiness_boundary_visible'],
                },
                'contract_gaps': item['contract_gaps'],
            }
            for item in target_results
        ],
        'real_execution_enabled': False,
        'external_side_effects_allowed': False,
    }
    manager.write_json('executor_integration_rehearsal.json', rehearsal)
    manager.write_text('executor_integration_rehearsal.md', '\n'.join([
        '# executor integration rehearsal',
        '',
        f"- integration_rehearsal_available: true",
        f"- available_count: {len(target_results)}",
        f"- pass_count: {pass_count}",
        f"- fail_count: {fail_count}",
        f"- top_executor_contract_gaps: {', '.join([g['gap_id'] for g in top_gaps]) if top_gaps else 'none'}",
        '- note: this is a simulation / rehearsal layer only, not a real executor.',
    ]) + '\n')
    return {
        'simulated_executor_run': simulated_run,
        'contract_compliance_matrix': contract_compliance,
        'executor_integration_rehearsal': rehearsal,
    }


def _write_execution_control_summary(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    manager = ArtifactManager(task_dir)
    build_rollout_gate_registry(task_dir)
    build_waiver_exception_registry(task_dir)
    build_executor_admission_artifacts(task_dir)
    build_executor_contract_artifacts(task_dir)
    release_contract = _load_json(task_dir / 'artifacts' / TARGETS['release']['contract_artifact'])
    rollback_contract = _load_json(task_dir / 'artifacts' / TARGETS['rollback']['contract_artifact'])
    release_dry_run = _load_json(task_dir / 'artifacts' / TARGETS['release']['dry_run_artifact'])
    rollback_dry_run = _load_json(task_dir / 'artifacts' / TARGETS['rollback']['dry_run_artifact'])
    release_handoff = _load_json(task_dir / 'artifacts' / TARGETS['release']['handoff_artifact'])
    rollback_handoff = _load_json(task_dir / 'artifacts' / TARGETS['rollback']['handoff_artifact'])
    release_operator_request = _load_json(task_dir / 'artifacts' / TARGETS['release']['operator_request_artifact'])
    rollback_operator_request = _load_json(task_dir / 'artifacts' / TARGETS['rollback']['operator_request_artifact'])
    release_receipt = _load_json(task_dir / 'artifacts' / TARGETS['release']['receipt_artifact'])
    rollback_receipt = _load_json(task_dir / 'artifacts' / TARGETS['rollback']['receipt_artifact'])
    readiness_review = _load_json(task_dir / 'artifacts' / 'executor_readiness_review.json')
    handoff_boundary = _load_json(task_dir / 'artifacts' / 'real_executor_handoff_boundary.json')
    rollout_gate_registry = _load_json(task_dir / 'artifacts' / 'rollout_gate_registry.json')
    waiver_exception_registry = _load_json(task_dir / 'artifacts' / 'waiver_exception_registry.json')
    executor_admission_review = _load_json(task_dir / 'artifacts' / 'executor_admission_review.json')
    go_no_go_decision_pack = _load_json(task_dir / 'artifacts' / 'go_no_go_decision_pack.json')
    release_adapter_manifest = _load_json(task_dir / 'artifacts' / TARGETS['release']['adapter_manifest_artifact'])
    rollback_adapter_manifest = _load_json(task_dir / 'artifacts' / TARGETS['rollback']['adapter_manifest_artifact'])
    capability_registry = _load_json(task_dir / 'artifacts' / 'executor_capability_registry.json')
    invocation_policy = _load_json(task_dir / 'artifacts' / 'invocation_policy_review.json')
    future_release_plugin_interface = _load_json(task_dir / 'artifacts' / 'release_executor_plugin_interface.json')
    future_rollback_plugin_interface = _load_json(task_dir / 'artifacts' / 'rollback_executor_plugin_interface.json')
    execution_transcript_contract = _load_json(task_dir / 'artifacts' / 'execution_transcript_contract.json')
    executor_plugin_review = _load_json(task_dir / 'artifacts' / 'executor_plugin_review.json')
    release_no_op_adapter = _load_json(task_dir / 'artifacts' / 'release_no_op_executor_adapter.json')
    rollback_no_op_adapter = _load_json(task_dir / 'artifacts' / 'rollback_no_op_executor_adapter.json')
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
    escalation_review = _load_json(task_dir / 'artifacts' / 'execution_request_escalation_review.json')
    retry_summary = _load_json(task_dir / 'artifacts' / 'execution_request_retry_summary.json')
    request_registry = _load_json(task_dir / 'artifacts' / 'execution_request_registry.json')
    dispatch_review = _load_json(task_dir / 'artifacts' / 'execution_request_dispatch_review.json')
    simulated_executor_run = _load_json(task_dir / 'artifacts' / 'simulated_executor_run.json')
    contract_compliance_matrix = _load_json(task_dir / 'artifacts' / 'contract_compliance_matrix.json')
    executor_integration_rehearsal = _load_json(task_dir / 'artifacts' / 'executor_integration_rehearsal.json')
    lifecycle = _load_execution_request_lifecycle(task_dir)
    lifecycle_summary = _request_state_summary(lifecycle=lifecycle)
    batch = ensure_execution_batch(task_dir)
    summary = {
        'task_id': task_dir.name,
        'record_type': 'execution_control_summary',
        'executor_contract_available': bool(release_contract and rollback_contract),
        'dry_run_available': bool(release_dry_run and rollback_dry_run),
        'execution_receipt_protocol_available': bool(_load_json(PROTOCOLS / 'execution_receipt.schema.json')),
        'handoff_packet_available': bool(release_handoff and rollback_handoff),
        'operator_execution_request_available': bool(release_operator_request and rollback_operator_request),
        'receipt_correlation_ready': bool((release_handoff.get('receipt_correlation_contract') or {}).get('correlation_ready')) and bool((rollback_handoff.get('receipt_correlation_contract') or {}).get('correlation_ready')),
        'release_receipt_recorded': bool(release_receipt),
        'rollback_receipt_recorded': bool(rollback_receipt),
        'executor_readiness_state': (
            'handoff_boundary_ready'
            if bool(handoff_boundary.get('handoff_boundary_ready'))
            else 'dry_run_validated'
            if bool(release_dry_run.get('dry_run_validated')) and bool(rollback_dry_run.get('dry_run_validated')) and bool(release_receipt) and bool(rollback_receipt)
            else 'contracts_ready_for_dry_run'
            if release_contract and rollback_contract
            else 'not_ready'
        ),
        'executor_readiness_review_available': bool(readiness_review),
        'executor_adapter_available_count': sum(1 for payload in (release_adapter_manifest, rollback_adapter_manifest) if payload),
        'executor_capability_registry_available': bool(capability_registry),
        'invocation_policy_available': bool(invocation_policy),
        'future_executor_scaffold_available': bool(executor_plugin_review.get('future_executor_scaffold_available')),
        'executor_plugin_interface_available': bool(future_release_plugin_interface and future_rollback_plugin_interface),
        'transcript_contract_available': bool(execution_transcript_contract.get('transcript_available')),
        'no_op_executor_available': bool(release_no_op_adapter and rollback_no_op_adapter),
        'executor_conformance_available': bool(executor_conformance_matrix.get('executor_conformance_available')),
        'executor_error_contract_available': bool(executor_error_contract.get('executor_error_contract_available')),
        'release_rollback_parity_available': bool(release_rollback_parity_matrix.get('release_rollback_parity_available')),
        'implementation_blueprint_available': bool(future_executor_implementation_blueprint.get('implementation_blueprint_available')),
        'executor_delivery_pack_available': bool(real_executor_delivery_backlog.get('executor_delivery_pack_available')),
        'executor_acceptance_pack_available': bool(executor_acceptance_test_pack.get('executor_acceptance_pack_available')),
        'ownership_split_available': bool(executor_ownership_split.get('ownership_split_available')),
        'executor_blocker_matrix_available': bool(executor_blocker_matrix.get('executor_blocker_matrix_available')),
        'executor_delivery_item_count': int(real_executor_delivery_backlog.get('delivery_item_count', 0) or 0),
        'executor_acceptance_case_count': int(executor_acceptance_test_pack.get('test_case_count', 0) or 0),
        'executor_blocker_count': int(executor_blocker_matrix.get('executor_blocker_count', 0) or 0),
        'cutover_pack_available': bool(executor_cutover_readiness_pack.get('cutover_pack_available')),
        'integration_checklist_available': bool(real_executor_integration_checklist.get('integration_checklist_available')),
        'risk_register_available': bool(executor_risk_register.get('risk_register_available')),
        'handoff_summary_available': bool(future_executor_handoff_summary.get('handoff_summary_available')),
        'credential_binding_policy_available': bool(executor_credential_binding_policy.get('credential_binding_policy_available')),
        'target_binding_registry_available': bool(executor_target_binding_registry.get('target_binding_registry_available')),
        'cutover_signoff_available': bool(cutover_signoff_workflow.get('cutover_signoff_available')),
        'blocker_drilldown_available': bool(blocker_drilldown_review.get('blocker_drilldown_available')),
        'human_action_pack_available': bool(executor_human_action_pack.get('human_action_pack_available')),
        'credential_binding_evidence_checklist_available': bool(credential_binding_evidence_checklist.get('credential_binding_evidence_checklist_available')),
        'signoff_evidence_packet_available': bool(cutover_signoff_evidence_packet.get('cutover_signoff_evidence_packet_available')),
        'unresolved_blocker_tracker_available': bool(unresolved_blocker_tracker.get('unresolved_blocker_tracker_available')),
        'pending_human_action_board_available': bool(pending_human_action_board.get('pending_human_action_board_available')),
        'credential_binding_runbook_available': bool(credential_binding_runbook.get('credential_binding_runbook_available')),
        'signoff_runbook_available': bool(cutover_signoff_runbook.get('signoff_runbook_available')),
        'blocker_resolution_playbook_available': bool(blocker_resolution_playbook.get('blocker_resolution_playbook_available')),
        'unresolved_credential_binding_count': int((executor_credential_binding_policy.get('unresolved_binding_count', 0) or 0)) + int((executor_target_binding_registry.get('unresolved_binding_count', 0) or 0)),
        'unresolved_signoff_count': int(cutover_signoff_workflow.get('unresolved_signoff_count', 0) or 0),
        'unresolved_blocker_owner_count': int(unresolved_blocker_tracker.get('unresolved_blocker_owner_count', 0) or 0),
        'pending_signoff_role_count': int(cutover_signoff_evidence_packet.get('pending_signoff_role_count', 0) or 0),
        'binding_evidence_gap_count': int(credential_binding_evidence_checklist.get('binding_evidence_gap_count', 0) or 0),
        'top_blocker_categories': list(blocker_drilldown_review.get('top_blocker_categories') or []),
        'top_human_actions': list(executor_human_action_pack.get('top_human_actions') or []),
        'top_pending_human_actions': list(pending_human_action_board.get('top_pending_human_actions') or []),
        'top_unresolved_human_blockers': list(executor_human_action_pack.get('top_unresolved_human_blockers') or blocker_resolution_playbook.get('top_unresolved_human_blockers') or []),
        'top_missing_executor_contracts': [item.get('gap_id') for item in (executor_conformance_matrix.get('top_missing_executor_contracts') or []) if item.get('gap_id')],
        'parity_gaps': list(release_rollback_parity_matrix.get('parity_gaps') or []),
        'top_executor_risks': list(executor_risk_register.get('top_executor_risks') or []),
        'top_executor_blockers': list(executor_blocker_matrix.get('top_executor_blockers') or []),
        'top_remaining_blockers': list(real_executor_integration_checklist.get('top_remaining_blockers') or executor_risk_register.get('top_remaining_blockers') or []),
        'environment_guard_ok_count': sum(1 for payload in (release_adapter_manifest, rollback_adapter_manifest) if (payload.get('environment_guard') or {}).get('guard_ok')),
        'environment_guard_unmet_count': sum(len((payload.get('environment_guard') or {}).get('unmet_guard_checks', [])) for payload in (release_adapter_manifest, rollback_adapter_manifest) if payload),
        'top_executor_adapter_types': capability_registry.get('top_executor_adapter_types', []),
        'top_executor_plugin_targets': executor_plugin_review.get('top_executor_plugin_targets', []),
        'handoff_boundary_ready': bool(handoff_boundary.get('handoff_boundary_ready')),
        'top_execution_handoff_targets': [name for name, payload in [('release', release_handoff), ('rollback', rollback_handoff)] if payload],
        'top_command_plan_steps': [step.get('title') for step in (((release_handoff.get('command_plan') or {}).get('steps') or []) + ((rollback_handoff.get('command_plan') or {}).get('steps') or []))[:5]],
        'execution_request_requested_count': lifecycle_summary.get('requested_count', 0),
        'execution_request_acknowledged_count': lifecycle_summary.get('acknowledged_count', 0),
        'execution_request_accepted_count': lifecycle_summary.get('accepted_count', 0),
        'execution_request_declined_count': lifecycle_summary.get('declined_count', 0),
        'execution_request_expired_count': lifecycle_summary.get('expired_count', 0),
        'request_open_count': lifecycle_summary.get('open_count', request_registry.get('request_open_count', 0)),
        'request_inflight_count': lifecycle_summary.get('inflight_count', request_registry.get('request_inflight_count', 0)),
        'execution_request_reassigned_count': lifecycle_summary.get('reassigned_count', escalation_review.get('execution_request_reassigned_count', 0)),
        'execution_request_escalated_count': lifecycle_summary.get('escalated_count', escalation_review.get('execution_request_escalated_count', 0)),
        'execution_request_retry_ready_count': lifecycle_summary.get('retry_ready_count', retry_summary.get('execution_request_retry_ready_count', 0)),
        'top_request_states': lifecycle_summary.get('top_request_states', []),
        'top_pending_requests': lifecycle_summary.get('top_pending_requests', request_registry.get('top_pending_requests', dispatch_review.get('top_pending_requests', []))),
        'recent_request_actions': lifecycle_summary.get('recent_request_actions', []),
        'recent_request_transitions': lifecycle_summary.get('recent_request_transitions', dispatch_review.get('recent_request_transitions', [])),
        'recent_request_escalations': lifecycle_summary.get('recent_request_escalations', escalation_review.get('recent_request_escalations', [])),
        'top_request_owners': lifecycle_summary.get('top_request_owners', escalation_review.get('top_request_owners', [])),
        'execution_request_traceability_ready_count': lifecycle_summary.get('traceability_ready_count', 0),
        'executor_readiness_gate_count': readiness_review.get('executor_readiness_gate_count'),
        'executor_unmet_gate_count': readiness_review.get('executor_unmet_gate_count'),
        'top_unmet_executor_gates': readiness_review.get('top_unmet_executor_gates', []),
        'readiness_gate_counts': readiness_review.get('readiness_gate_counts', {}),
        'unmet_gate_counts': readiness_review.get('unmet_gate_counts', {}),
        'executor_admission_available': bool(executor_admission_review),
        'go_no_go_available': bool(go_no_go_decision_pack),
        'rollout_gate_count': rollout_gate_registry.get('rollout_gate_count', 0),
        'rollout_unmet_count': rollout_gate_registry.get('unmet_count', 0),
        'waiver_exception_count': waiver_exception_registry.get('waiver_exception_count', 0),
        'overall_admission_state': executor_admission_review.get('overall_admission_state') or ('ready_for_future_executor' if go_no_go_decision_pack.get('overall_decision') == 'go' else None),
        'top_blocking_gates': executor_admission_review.get('top_blocking_gates', rollout_gate_registry.get('top_blocking_gates', [])),
        'executor_simulation_available_count': int(simulated_executor_run.get('available_count', 0) or 0),
        'executor_simulation_pass_count': int(simulated_executor_run.get('pass_count', 0) or 0),
        'executor_simulation_fail_count': int(simulated_executor_run.get('fail_count', 0) or 0),
        'contract_compliance_available': bool(contract_compliance_matrix.get('contract_compliance_available')),
        'integration_rehearsal_available': bool(executor_integration_rehearsal.get('integration_rehearsal_available')),
        'top_executor_contract_gaps': [item.get('gap_id') for item in (simulated_executor_run.get('top_executor_contract_gaps') or contract_compliance_matrix.get('top_executor_contract_gaps') or []) if item.get('gap_id')],
        'execution_batch_id': batch.get('batch_id'),
        'release_run_id': batch.get('release_run_id'),
        'rollback_run_id': batch.get('rollback_run_id'),
        'generated_at': _now(),
    }
    if release_contract and rollback_contract and release_dry_run and rollback_dry_run and release_receipt and rollback_receipt:
        simulation_bundle = _build_executor_simulation_artifacts(task_dir)
        simulated_executor_run = simulation_bundle['simulated_executor_run']
        contract_compliance_matrix = simulation_bundle['contract_compliance_matrix']
        executor_integration_rehearsal = simulation_bundle['executor_integration_rehearsal']
        summary['executor_simulation_available_count'] = int(simulated_executor_run.get('available_count', 0) or 0)
        summary['executor_simulation_pass_count'] = int(simulated_executor_run.get('pass_count', 0) or 0)
        summary['executor_simulation_fail_count'] = int(simulated_executor_run.get('fail_count', 0) or 0)
        summary['contract_compliance_available'] = bool(contract_compliance_matrix.get('contract_compliance_available'))
        summary['integration_rehearsal_available'] = bool(executor_integration_rehearsal.get('integration_rehearsal_available'))
        summary['top_executor_contract_gaps'] = [item.get('gap_id') for item in (simulated_executor_run.get('top_executor_contract_gaps') or []) if item.get('gap_id')]
        contract_bundle = build_executor_contract_artifacts(task_dir)
        summary['executor_conformance_available'] = bool(contract_bundle['executor_conformance_matrix'].get('executor_conformance_available'))
        summary['executor_error_contract_available'] = bool(contract_bundle['executor_error_contract'].get('executor_error_contract_available'))
        summary['release_rollback_parity_available'] = bool(contract_bundle['release_rollback_parity_matrix'].get('release_rollback_parity_available'))
        summary['implementation_blueprint_available'] = bool(contract_bundle['future_executor_implementation_blueprint'].get('implementation_blueprint_available'))
        summary['executor_delivery_pack_available'] = bool(contract_bundle['real_executor_delivery_backlog'].get('executor_delivery_pack_available'))
        summary['executor_acceptance_pack_available'] = bool(contract_bundle['executor_acceptance_test_pack'].get('executor_acceptance_pack_available'))
        summary['ownership_split_available'] = bool(contract_bundle['executor_ownership_split'].get('ownership_split_available'))
        summary['executor_blocker_matrix_available'] = bool(contract_bundle['executor_blocker_matrix'].get('executor_blocker_matrix_available'))
        summary['executor_delivery_item_count'] = int(contract_bundle['real_executor_delivery_backlog'].get('delivery_item_count', 0) or 0)
        summary['executor_acceptance_case_count'] = int(contract_bundle['executor_acceptance_test_pack'].get('test_case_count', 0) or 0)
        summary['executor_blocker_count'] = int(contract_bundle['executor_blocker_matrix'].get('executor_blocker_count', 0) or 0)
        summary['cutover_pack_available'] = bool(contract_bundle['executor_cutover_readiness_pack'].get('cutover_pack_available'))
        summary['integration_checklist_available'] = bool(contract_bundle['real_executor_integration_checklist'].get('integration_checklist_available'))
        summary['risk_register_available'] = bool(contract_bundle['executor_risk_register'].get('risk_register_available'))
        summary['handoff_summary_available'] = bool(contract_bundle['future_executor_handoff_summary'].get('handoff_summary_available'))
        summary['credential_binding_policy_available'] = bool(contract_bundle.get('executor_credential_binding_policy', {}).get('credential_binding_policy_available'))
        summary['target_binding_registry_available'] = bool(contract_bundle.get('executor_target_binding_registry', {}).get('target_binding_registry_available'))
        summary['cutover_signoff_available'] = bool(contract_bundle.get('cutover_signoff_workflow', {}).get('cutover_signoff_available'))
        summary['blocker_drilldown_available'] = bool(contract_bundle.get('blocker_drilldown_review', {}).get('blocker_drilldown_available'))
        summary['human_action_pack_available'] = bool(contract_bundle.get('executor_human_action_pack', {}).get('human_action_pack_available'))
        summary['credential_binding_evidence_checklist_available'] = bool(contract_bundle.get('credential_binding_evidence_checklist', {}).get('credential_binding_evidence_checklist_available'))
        summary['signoff_evidence_packet_available'] = bool(contract_bundle.get('cutover_signoff_evidence_packet', {}).get('cutover_signoff_evidence_packet_available'))
        summary['unresolved_blocker_tracker_available'] = bool(contract_bundle.get('unresolved_blocker_tracker', {}).get('unresolved_blocker_tracker_available'))
        summary['pending_human_action_board_available'] = bool(contract_bundle.get('pending_human_action_board', {}).get('pending_human_action_board_available'))
        summary['credential_binding_runbook_available'] = bool(contract_bundle.get('credential_binding_runbook', {}).get('credential_binding_runbook_available'))
        summary['signoff_runbook_available'] = bool(contract_bundle.get('cutover_signoff_runbook', {}).get('signoff_runbook_available'))
        summary['blocker_resolution_playbook_available'] = bool(contract_bundle.get('blocker_resolution_playbook', {}).get('blocker_resolution_playbook_available'))
        summary['unresolved_credential_binding_count'] = int((contract_bundle.get('executor_credential_binding_policy', {}).get('unresolved_binding_count', 0) or 0)) + int((contract_bundle.get('executor_target_binding_registry', {}).get('unresolved_binding_count', 0) or 0))
        summary['unresolved_signoff_count'] = int(contract_bundle.get('cutover_signoff_workflow', {}).get('unresolved_signoff_count', 0) or 0)
        summary['unresolved_blocker_owner_count'] = int(contract_bundle.get('unresolved_blocker_tracker', {}).get('unresolved_blocker_owner_count', 0) or 0)
        summary['pending_signoff_role_count'] = int(contract_bundle.get('cutover_signoff_evidence_packet', {}).get('pending_signoff_role_count', 0) or 0)
        summary['binding_evidence_gap_count'] = int(contract_bundle.get('credential_binding_evidence_checklist', {}).get('binding_evidence_gap_count', 0) or 0)
        summary['top_blocker_categories'] = list(contract_bundle.get('blocker_drilldown_review', {}).get('top_blocker_categories') or [])
        summary['top_human_actions'] = list(contract_bundle.get('executor_human_action_pack', {}).get('top_human_actions') or [])
        summary['top_pending_human_actions'] = list(contract_bundle.get('pending_human_action_board', {}).get('top_pending_human_actions') or [])
        summary['top_unresolved_human_blockers'] = list(contract_bundle.get('executor_human_action_pack', {}).get('top_unresolved_human_blockers') or contract_bundle.get('blocker_resolution_playbook', {}).get('top_unresolved_human_blockers') or [])
        summary['top_missing_executor_contracts'] = [item.get('gap_id') for item in (contract_bundle['executor_conformance_matrix'].get('top_missing_executor_contracts') or []) if item.get('gap_id')]
        summary['parity_gaps'] = list(contract_bundle['release_rollback_parity_matrix'].get('parity_gaps') or [])
        summary['top_executor_risks'] = list(contract_bundle['executor_risk_register'].get('top_executor_risks') or [])
        summary['top_executor_blockers'] = list(contract_bundle['executor_blocker_matrix'].get('top_executor_blockers') or [])
        summary['top_remaining_blockers'] = list(contract_bundle['real_executor_integration_checklist'].get('top_remaining_blockers') or contract_bundle['executor_risk_register'].get('top_remaining_blockers') or [])
    manager.write_json('execution_control_summary.json', summary)
    manager.write_text('execution_receipt_review.md', (
        '# execution receipt review\n\n'
        f"- executor_contract_available: {str(summary['executor_contract_available']).lower()}\n"
        f"- dry_run_available: {str(summary['dry_run_available']).lower()}\n"
        f"- execution_receipt_protocol_available: {str(summary['execution_receipt_protocol_available']).lower()}\n"
        f"- handoff_packet_available: {str(summary['handoff_packet_available']).lower()}\n"
        f"- operator_execution_request_available: {str(summary['operator_execution_request_available']).lower()}\n"
        f"- receipt_correlation_ready: {str(summary['receipt_correlation_ready']).lower()}\n"
        f"- executor_readiness_review_available: {str(summary['executor_readiness_review_available']).lower()}\n"
        f"- executor_adapter_available_count: {summary['executor_adapter_available_count']}\n"
        f"- executor_capability_registry_available: {str(summary['executor_capability_registry_available']).lower()}\n"
        f"- invocation_policy_available: {str(summary['invocation_policy_available']).lower()}\n"
        f"- future_executor_scaffold_available: {str(summary['future_executor_scaffold_available']).lower()}\n"
        f"- executor_plugin_interface_available: {str(summary['executor_plugin_interface_available']).lower()}\n"
        f"- transcript_contract_available: {str(summary['transcript_contract_available']).lower()}\n"
        f"- no_op_executor_available: {str(summary['no_op_executor_available']).lower()}\n"
        f"- environment_guard_ok_count: {summary['environment_guard_ok_count']}\n"
        f"- environment_guard_unmet_count: {summary['environment_guard_unmet_count']}\n"
        f"- top_executor_adapter_types: {', '.join(summary['top_executor_adapter_types']) if summary['top_executor_adapter_types'] else 'none'}\n"
        f"- top_executor_plugin_targets: {', '.join(summary['top_executor_plugin_targets']) if summary['top_executor_plugin_targets'] else 'none'}\n"
        f"- executor_readiness_state: {summary['executor_readiness_state']}\n"
        f"- executor_readiness_gate_count: {summary['executor_readiness_gate_count']}\n"
        f"- executor_unmet_gate_count: {summary['executor_unmet_gate_count']}\n"
        f"- top_unmet_executor_gates: {', '.join(summary['top_unmet_executor_gates']) if summary['top_unmet_executor_gates'] else 'none'}\n"
        f"- execution_request_requested_count: {summary['execution_request_requested_count']}\n"
        f"- execution_request_acknowledged_count: {summary['execution_request_acknowledged_count']}\n"
        f"- execution_request_accepted_count: {summary['execution_request_accepted_count']}\n"
        f"- execution_request_declined_count: {summary['execution_request_declined_count']}\n"
        f"- execution_request_expired_count: {summary['execution_request_expired_count']}\n"
        f"- execution_request_reassigned_count: {summary['execution_request_reassigned_count']}\n"
        f"- execution_request_escalated_count: {summary['execution_request_escalated_count']}\n"
        f"- execution_request_retry_ready_count: {summary['execution_request_retry_ready_count']}\n"
        f"- top_request_states: {', '.join(summary['top_request_states']) if summary['top_request_states'] else 'none'}\n"
        f"- handoff_boundary_ready: {str(summary['handoff_boundary_ready']).lower()}\n"
        f"- execution_batch_id: {summary['execution_batch_id']}\n"
        f"- release_run_id: {summary['release_run_id']}\n"
        f"- rollback_run_id: {summary['rollback_run_id']}\n"
        '- note: All receipts are dry-run-only mock receipts with command digest traceability.\n'
    ))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)

    mat = sub.add_parser('materialize')
    mat.add_argument('--task-dir', default='')
    mat.add_argument('--task-id', default='')
    mat.add_argument('--jobs-root', default=str(JOBS_ROOT))
    mat.add_argument('--target', choices=['release', 'rollback', 'all'], default='all')

    dry = sub.add_parser('dry-run')
    dry.add_argument('--task-dir', default='')
    dry.add_argument('--task-id', default='')
    dry.add_argument('--jobs-root', default=str(JOBS_ROOT))
    dry.add_argument('--target', choices=['release', 'rollback'], required=True)
    dry.add_argument('--requested-by', required=True)
    dry.add_argument('--proposal-ref', required=True)
    dry.add_argument('--approval-ref', required=True)

    ack = sub.add_parser('ack-request')
    ack.add_argument('--task-dir', default='')
    ack.add_argument('--task-id', default='')
    ack.add_argument('--jobs-root', default=str(JOBS_ROOT))
    ack.add_argument('--target', choices=['release', 'rollback'], required=True)
    ack.add_argument('--request-action', dest='request_action', choices=['acknowledge', 'accept', 'decline', 'expire'], required=True)
    ack.add_argument('--acted-by', required=True)
    ack.add_argument('--note', default='')
    ack.add_argument('--reason', default='')
    ack.add_argument('--operator-role', default='human_operator')

    gov = sub.add_parser('govern-request')
    gov.add_argument('--task-dir', default='')
    gov.add_argument('--task-id', default='')
    gov.add_argument('--jobs-root', default=str(JOBS_ROOT))
    gov.add_argument('--target', choices=['release', 'rollback'], required=True)
    gov.add_argument('--governance-action', choices=['set-expiry-policy', 'reassign', 'escalate', 'mark-retry-ready'], required=True)
    gov.add_argument('--acted-by', required=True)
    gov.add_argument('--timeout-minutes', type=int, default=None)
    gov.add_argument('--new-owner', default='')
    gov.add_argument('--escalation-level', default='')
    gov.add_argument('--escalation-reason', default='')
    gov.add_argument('--retry-reason', default='')
    gov.add_argument('--reroute-target', default='')
    gov.add_argument('--note', default='')
    gov.add_argument('--operator-role', default='request_governor')

    args = parser.parse_args()
    task_dir = _resolve_task_dir(task_dir=args.task_dir or None, task_id=args.task_id or None, jobs_root=args.jobs_root)
    if args.action == 'materialize':
        if args.target == 'all':
            result = {
                'release': materialize_controlled_executor(task_dir, target='release'),
                'rollback': materialize_controlled_executor(task_dir, target='rollback'),
                'readiness': build_executor_readiness_artifacts(task_dir),
                'summary': _write_execution_control_summary(task_dir),
            }
        else:
            result = materialize_controlled_executor(task_dir, target=args.target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.action == 'dry-run':
        result = dry_run_controlled_execution(
            task_dir,
            target=args.target,
            requested_by=args.requested_by,
            proposal_ref=args.proposal_ref,
            approval_ref=args.approval_ref,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.action == 'ack-request':
        result = acknowledge_execution_request(
            task_dir,
            target=args.target,
            action=args.request_action,
            acted_by=args.acted_by,
            note=args.note,
            reason=args.reason,
            operator_role=args.operator_role,
        )
        _write_execution_control_summary(task_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.action == 'govern-request':
        result = govern_execution_request(
            task_dir,
            target=args.target,
            action=args.governance_action,
            acted_by=args.acted_by,
            timeout_minutes=args.timeout_minutes,
            new_owner=args.new_owner,
            escalation_level=args.escalation_level,
            escalation_reason=args.escalation_reason,
            retry_reason=args.retry_reason,
            reroute_target=args.reroute_target,
            note=args.note,
            operator_role=args.operator_role,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
