#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from approval_recompute_runtime import build_approval_recompute_snapshot
from artifact_manager import ArtifactManager
from execution_protocol_runtime import sync_all_execution_protocols
from human_approval_input_runtime import build_human_approval_input_slot
from official_release_execution_runtime import prepare_execution_path
from official_release_rehearsal_runtime import build_official_release_rehearsal
from release_closure_runtime import (
    build_approval_transition_stub,
    build_human_approval_result_stub,
    build_official_release_pipeline_summary,
    build_official_release_state_placeholder,
    build_post_approval_guardrail_transition,
    build_release_execution_guardrail,
    load_release_closure_snapshot,
)

ROOT = Path('/home/admin/.openclaw/workspace/master')
JOBS_ROOT = ROOT / 'traces' / 'jobs'


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


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


def _build_real_approval_outcome(*, task_id: str, decision: str, approval_checklist: dict[str, Any], approver: str, reason: str) -> dict[str, Any]:
    approved = decision == 'approve'
    if not approval_checklist.get('checklist_ready'):
        status = 'not_ready_for_approval'
        next_step = 'fix_checklist_gaps_before_requesting_approval'
    elif approved:
        status = 'approved_by_human'
        next_step = 'recompute_release_execution_guardrail_after_real_approval'
    else:
        status = 'rejected_by_human'
        next_step = 'keep_candidate_blocked_and_rework'
    return {
        'task_id': task_id,
        'approval_status': status,
        'approved': approved,
        'requires_human_approval': True,
        'decision_recorded': True,
        'decision_source': 'real_human_decision_recorded',
        'decided_by': approver,
        'decision_reason': reason,
        'decided_at': _now(),
        'next_step': next_step,
        'note': 'Approval outcome updated from a real recorded human decision. Official release execution is still gated separately.',
    }


def _build_real_approval_decision(*, task_id: str, decision: str, approver: str, reason: str) -> dict[str, Any]:
    approved = decision == 'approve'
    return {
        'task_id': task_id,
        'decision_recorded': True,
        'decision_state': 'approved_placeholder' if approved else 'rejected_placeholder',
        'approved': approved,
        'decision_source': 'real_human_decision_recorded',
        'decided_by': approver,
        'decision_reason': reason,
        'decided_at': _now(),
        'next_step': 'prepare_official_release_state_placeholder' if approved else 'candidate_rejected_no_release_possible_until_rework',
        'note': 'Approval decision placeholder has been upgraded with a real recorded human decision.',
    }


def _build_real_human_result(*, task_id: str, approval_transition: dict[str, Any], decision: str, approver: str, reason: str) -> dict[str, Any]:
    payload = build_human_approval_result_stub(task_id, approval_transition=approval_transition)
    approved = decision == 'approve'
    payload.update({
        'ingestion_state': 'approved_ingested_real_decision' if approved else 'rejected_ingested_real_decision',
        'decision_recorded': True,
        'approved': approved,
        'decision_source': 'real_human_decision_recorded',
        'decided_by': approver,
        'decision_reason': reason,
        'decided_at': _now(),
        'note': 'Human approval result has been updated from a real recorded human decision. This still does not execute any official release action.',
    })
    return payload


def record_human_approval(*, task_dir: str | Path | None = None, task_id: str | None = None, decision: str, approver: str = 'human', reason: str = '', jobs_root: str | Path = JOBS_ROOT) -> dict[str, Any]:
    if decision not in {'approve', 'reject'}:
        raise ValueError('decision must be approve or reject')

    resolved_task_dir = _resolve_task_dir(task_dir=task_dir, task_id=task_id, jobs_root=jobs_root)
    artifacts_dir = resolved_task_dir / 'artifacts'
    if not artifacts_dir.exists():
        raise FileNotFoundError(f'artifacts directory missing: {artifacts_dir}')

    manager = ArtifactManager(resolved_task_dir)
    task_name = resolved_task_dir.name

    approval_record = _load_json(artifacts_dir / 'approval_record.json')
    approval_checklist = _load_json(artifacts_dir / 'approval_checklist.json')
    pre_release_gate = _load_json(artifacts_dir / 'pre_release_gate.json')
    release_action = _load_json(artifacts_dir / 'release_action_stub.json')
    release_preflight = _load_json(artifacts_dir / 'release_preflight_stub.json')
    rollback_registry = _load_json(artifacts_dir / 'rollback_registry_entry.json')
    official_release_rehearsal = _load_json(artifacts_dir / 'official_release_rehearsal.json')
    release_artifact_binding = _load_json(artifacts_dir / 'release_artifact_binding.json')
    closure_consistency = _load_json(artifacts_dir / 'release_closure_consistency.json')

    missing_required = []
    for name, payload in {
        'approval_record.json': approval_record,
        'approval_checklist.json': approval_checklist,
        'pre_release_gate.json': pre_release_gate,
        'release_action_stub.json': release_action,
        'release_preflight_stub.json': release_preflight,
        'rollback_registry_entry.json': rollback_registry,
        'official_release_rehearsal.json': official_release_rehearsal,
        'release_artifact_binding.json': release_artifact_binding,
        'release_closure_consistency.json': closure_consistency,
    }.items():
        if not payload:
            missing_required.append(name)
    if missing_required:
        raise FileNotFoundError(f'missing required release closure artifacts: {missing_required}')

    approval_outcome = _build_real_approval_outcome(
        task_id=task_name,
        decision=decision,
        approval_checklist=approval_checklist,
        approver=approver,
        reason=reason,
    )
    approval_decision = _build_real_approval_decision(
        task_id=task_name,
        decision=decision,
        approver=approver,
        reason=reason,
    )
    approval_transition = build_approval_transition_stub(task_name, approval_decision=approval_decision)
    human_approval_result = _build_real_human_result(
        task_id=task_name,
        approval_transition=approval_transition,
        decision=decision,
        approver=approver,
        reason=reason,
    )
    human_approval_input_slot = build_human_approval_input_slot(
        task_name,
        pre_release_gate=pre_release_gate,
        human_approval_result=human_approval_result,
    )
    release_execution_guardrail = build_release_execution_guardrail(
        task_name,
        approval_decision=approval_decision,
        pre_release_gate=pre_release_gate,
        human_approval_result=human_approval_result,
    )
    post_approval_guardrail_transition = build_post_approval_guardrail_transition(
        task_name,
        human_approval_result=human_approval_result,
        release_execution_guardrail=release_execution_guardrail,
    )
    official_release_state = build_official_release_state_placeholder(
        task_name,
        approval_transition=approval_transition,
        release_execution_guardrail=release_execution_guardrail,
        human_approval_result=human_approval_result,
    )
    refreshed_official_release_rehearsal = build_official_release_rehearsal(
        task_name,
        pre_release_gate=pre_release_gate,
        closure_consistency=closure_consistency,
        approval_outcome=approval_outcome,
        release_action=release_action,
    )
    approval_recompute_snapshot = build_approval_recompute_snapshot(
        task_name,
        human_approval_result=human_approval_result,
        pre_release_gate=pre_release_gate,
        official_release_rehearsal=refreshed_official_release_rehearsal,
        release_execution_guardrail=release_execution_guardrail,
        official_release_state=official_release_state,
    )
    official_release_pipeline_summary = build_official_release_pipeline_summary(
        task_name,
        pre_release_gate=pre_release_gate,
        official_release_rehearsal=refreshed_official_release_rehearsal,
        release_execution_guardrail=release_execution_guardrail,
        official_release_state=official_release_state,
        release_artifact_binding=release_artifact_binding,
        rollback_registry=rollback_registry,
        human_approval_result=human_approval_result,
        approval_recompute_snapshot=approval_recompute_snapshot,
    )

    approval_record_updated = {
        **approval_record,
        'approved': decision == 'approve',
        'approval_state': 'human_approved_candidate' if decision == 'approve' else 'human_rejected_candidate',
        'decision_recorded': True,
        'decision_source': 'real_human_decision_recorded',
        'decided_by': approver,
        'decision_reason': reason,
        'decided_at': _now(),
    }

    manager.write_json('approval_record.json', approval_record_updated)
    manager.write_json('approval_outcome_stub.json', approval_outcome)
    manager.write_json('approval_decision_placeholder.json', approval_decision)
    manager.write_json('approval_transition_stub.json', approval_transition)
    manager.write_json('human_approval_result_stub.json', human_approval_result)
    manager.write_json('human_approval_input_slot.json', human_approval_input_slot)
    manager.write_json('release_execution_guardrail.json', release_execution_guardrail)
    manager.write_json('post_approval_guardrail_transition.json', post_approval_guardrail_transition)
    manager.write_json('official_release_state_placeholder.json', official_release_state)
    manager.write_json('approval_recompute_snapshot.json', approval_recompute_snapshot)
    manager.write_json('official_release_rehearsal.json', refreshed_official_release_rehearsal)
    manager.write_json('official_release_pipeline_summary.json', official_release_pipeline_summary)
    manager.write_json(
        'human_approval_record.json',
        {
            'task_id': task_name,
            'decision': decision,
            'approved': decision == 'approve',
            'decided_by': approver,
            'decision_reason': reason,
            'decided_at': _now(),
            'note': 'Real human approval decision record. This records approval only and does not execute any official release action.',
        },
    )
    manager.append_log(
        'human_approval_runtime.log',
        json.dumps(
            {
                'time': _now(),
                'task_id': task_name,
                'decision': decision,
                'approved': decision == 'approve',
                'decided_by': approver,
                'reason': reason,
            },
            ensure_ascii=False,
        ),
    )

    execution_path_result = None
    if decision == 'approve':
        execution_path_result = prepare_execution_path(task_dir=resolved_task_dir)
    sync_all_execution_protocols(resolved_task_dir)
    snapshot = load_release_closure_snapshot(resolved_task_dir)
    return {
        'task_id': task_name,
        'decision': decision,
        'approved': decision == 'approve',
        'decided_by': approver,
        'decision_reason': reason,
        'human_approval_state': snapshot.get('human_approval_state'),
        'approval_decision_recorded': snapshot.get('approval_decision_recorded'),
        'human_approval_result_recorded': snapshot.get('human_approval_result_recorded'),
        'approval_recompute_state': snapshot.get('approval_recompute_state'),
        'release_execution_state': snapshot.get('release_execution_state'),
        'official_release_state': snapshot.get('official_release_state'),
        'official_release_pipeline_state': snapshot.get('official_release_pipeline_state'),
        'official_release_pipeline_blockers': snapshot.get('official_release_pipeline_blockers'),
        'post_approval_execution_unblocked': snapshot.get('post_approval_execution_unblocked'),
        'official_release_pipeline_executable': snapshot.get('official_release_pipeline_executable'),
        'execution_path_result': execution_path_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)

    record_p = sub.add_parser('record-decision')
    record_p.add_argument('--task-dir', default='')
    record_p.add_argument('--task-id', default='')
    record_p.add_argument('--jobs-root', default=str(JOBS_ROOT))
    record_p.add_argument('--decision', choices=['approve', 'reject'], required=True)
    record_p.add_argument('--approver', default='human')
    record_p.add_argument('--reason', default='')

    args = parser.parse_args()
    if args.action == 'record-decision':
        result = record_human_approval(
            task_dir=args.task_dir or None,
            task_id=args.task_id or None,
            jobs_root=args.jobs_root,
            decision=args.decision,
            approver=args.approver,
            reason=args.reason,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
