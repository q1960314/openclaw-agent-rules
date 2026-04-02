#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backfill runtime for historical tasks.

Goal:
- populate missing quality/formalization artifacts for older tasks
- let new dashboards show real distributions instead of empty counters
- keep behavior deterministic and conservative (only derives missing artifacts)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from artifact_manager import ArtifactManager
from approval_recompute_runtime import build_approval_recompute_snapshot
from artifact_binding_runtime import build_release_artifact_binding
from closure_consistency_runtime import build_release_closure_consistency
from human_approval_input_runtime import build_human_approval_input_slot
from evaluation_runtime import evaluate_quality, load_quality_score
from formalization_runtime import build_formalization_gate, load_formalization_snapshot
from official_release_registry import build_official_release_stub, build_release_readiness, build_rollback_stub
from official_release_rehearsal_runtime import build_official_release_rehearsal
from release_closure_runtime import build_approval_checklist, build_approval_decision_placeholder, build_approval_outcome_stub, build_approval_record, build_approval_transition_stub, build_human_approval_result_stub, build_official_release_pipeline_summary, build_official_release_state_placeholder, build_post_approval_guardrail_transition, build_pre_release_gate, build_release_action_stub, build_release_execution_guardrail, build_release_preflight_stub, build_rollback_registry_entry
from task_queue import TaskQueue

ROOT = Path('/home/admin/.openclaw/workspace/master')
JOBS_ROOT = ROOT / 'traces' / 'jobs'


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def derive_boundary(task: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    metadata = task.get('metadata', {}) if isinstance(task.get('metadata', {}), dict) else {}
    manual_review_required = bool(metadata.get('manual_review_required', False)) or review.get('decision') == 'manual_review_required'
    approval_state = 'manual_review_required' if manual_review_required else 'technically_validated_candidate'
    return {
        'result_tier': 'candidate',
        'approval_state': approval_state,
        'formalization_required': True,
        'manual_review_required': manual_review_required,
        'review_decision': review.get('decision'),
    }


def _normalized_review_decision(decision: str | None) -> str:
    if decision in {'passed', 'manual_review_required', 'rejected'}:
        return str(decision)
    if decision == 'needs_changes':
        return 'rejected'
    return 'rejected'


def backfill_task(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    queue = TaskQueue(task_dir.parent)
    task = queue.load_task(task_dir.name) or {}
    review = _load_json(task_dir / 'review.json')
    manager = ArtifactManager(task_dir)

    result = {
        'task_id': task_dir.name,
        'role': task.get('role'),
        'quality_backfilled': False,
        'formalization_backfilled': False,
        'closure_backfilled': False,
        'skipped': False,
        'reason': '',
    }

    if not review.get('decision'):
        result['skipped'] = True
        result['reason'] = 'missing_review_decision'
        return result

    role = task.get('role') or task.get('owner_role') or 'unknown'
    normalized_decision = _normalized_review_decision(review.get('decision'))
    metadata = task.get('metadata', {}) if isinstance(task.get('metadata', {}), dict) else {}

    if not load_quality_score(task_dir):
        quality = evaluate_quality(
            task_id=task_dir.name,
            role=role,
            review_decision=normalized_decision,
            issues=review.get('issues', []),
            evidence=review.get('evidence', []),
            manual_review_required=bool(metadata.get('manual_review_required', False)),
        )
        manager.write_json('quality_score.json', quality)
        quality_lines = [
            '# Quality Score (Backfilled)',
            '',
            quality['summary'],
            '',
            f"- score: {quality['score']}",
            f"- grade: {quality['grade']}",
            f"- artifact_completeness: {quality['dimensions']['artifact_completeness']}",
            f"- structural_quality: {quality['dimensions']['structural_quality']}",
            f"- validation_outcome: {quality['dimensions']['validation_outcome']}",
            f"- release_readiness: {quality['dimensions']['release_readiness']}",
            f"- blocking_flags: {quality['blocking_flags']}",
        ]
        manager.write_text('quality_score.md', '\n'.join(quality_lines) + '\n')
        result['quality_backfilled'] = True

    boundary = derive_boundary(task, review)
    snapshot = load_formalization_snapshot(task_dir)
    if not snapshot.get('formalization_state'):
        gate = build_formalization_gate(task_dir, boundary=boundary, review=review)
        manager.write_json('formalization_gate.json', gate)
        result['formalization_backfilled'] = True
    else:
        gate = _load_json(task_dir / 'artifacts' / 'formalization_gate.json')

    release_readiness_path = task_dir / 'artifacts' / 'release_readiness.json'
    rollback_stub_path = task_dir / 'artifacts' / 'rollback_stub.json'
    approval_record_path = task_dir / 'artifacts' / 'approval_record.json'
    approval_checklist_path = task_dir / 'artifacts' / 'approval_checklist.json'
    approval_outcome_stub_path = task_dir / 'artifacts' / 'approval_outcome_stub.json'
    approval_decision_placeholder_path = task_dir / 'artifacts' / 'approval_decision_placeholder.json'
    approval_transition_stub_path = task_dir / 'artifacts' / 'approval_transition_stub.json'
    human_approval_result_stub_path = task_dir / 'artifacts' / 'human_approval_result_stub.json'
    human_approval_input_slot_path = task_dir / 'artifacts' / 'human_approval_input_slot.json'
    release_action_stub_path = task_dir / 'artifacts' / 'release_action_stub.json'
    release_preflight_stub_path = task_dir / 'artifacts' / 'release_preflight_stub.json'
    official_release_stub_path = task_dir / 'artifacts' / 'official_release_stub.json'
    rollback_registry_entry_path = task_dir / 'artifacts' / 'rollback_registry_entry.json'
    pre_release_gate_path = task_dir / 'artifacts' / 'pre_release_gate.json'
    release_closure_consistency_path = task_dir / 'artifacts' / 'release_closure_consistency.json'
    official_release_rehearsal_path = task_dir / 'artifacts' / 'official_release_rehearsal.json'
    release_execution_guardrail_path = task_dir / 'artifacts' / 'release_execution_guardrail.json'
    post_approval_guardrail_transition_path = task_dir / 'artifacts' / 'post_approval_guardrail_transition.json'
    official_release_state_placeholder_path = task_dir / 'artifacts' / 'official_release_state_placeholder.json'
    approval_recompute_snapshot_path = task_dir / 'artifacts' / 'approval_recompute_snapshot.json'
    release_artifact_binding_path = task_dir / 'artifacts' / 'release_artifact_binding.json'
    official_release_pipeline_summary_path = task_dir / 'artifacts' / 'official_release_pipeline_summary.json'
    official_release_rehearsal_path = task_dir / 'artifacts' / 'official_release_rehearsal.json'

    closure_changed = False
    rollback_stub = _load_json(rollback_stub_path)
    if not release_readiness_path.exists():
        manager.write_json('release_readiness.json', build_release_readiness(task_dir, boundary=boundary, review=review))
        closure_changed = True
    if not rollback_stub_path.exists():
        rollback_stub = build_rollback_stub(task_dir)
        manager.write_json('rollback_stub.json', rollback_stub)
        closure_changed = True
    if not rollback_stub:
        rollback_stub = _load_json(rollback_stub_path)
    approval_record_payload = _load_json(approval_record_path)
    if not approval_record_path.exists():
        approval_record_payload = build_approval_record(task_dir.name, review=review, boundary=boundary, formalization_gate=gate)
        manager.write_json('approval_record.json', approval_record_payload)
        closure_changed = True
    if not approval_record_payload:
        approval_record_payload = _load_json(approval_record_path)
    approval_checklist_payload = _load_json(approval_checklist_path)
    if not approval_checklist_path.exists():
        approval_checklist_payload = build_approval_checklist(task_dir.name, formalization_gate=gate, release_readiness=_load_json(release_readiness_path) or build_release_readiness(task_dir, boundary=boundary, review=review), rollback_stub=rollback_stub)
        manager.write_json('approval_checklist.json', approval_checklist_payload)
        closure_changed = True
    if not approval_checklist_payload:
        approval_checklist_payload = _load_json(approval_checklist_path)
    approval_outcome_payload = _load_json(approval_outcome_stub_path)
    if not approval_outcome_stub_path.exists():
        approval_outcome_payload = build_approval_outcome_stub(task_dir.name, approval_checklist=approval_checklist_payload)
        manager.write_json('approval_outcome_stub.json', approval_outcome_payload)
        closure_changed = True
    if not approval_outcome_payload:
        approval_outcome_payload = _load_json(approval_outcome_stub_path)
    approval_decision_payload = _load_json(approval_decision_placeholder_path)
    if not approval_decision_placeholder_path.exists():
        approval_decision_payload = build_approval_decision_placeholder(task_dir.name, approval_outcome=approval_outcome_payload)
        manager.write_json('approval_decision_placeholder.json', approval_decision_payload)
        closure_changed = True
    if not approval_decision_payload:
        approval_decision_payload = _load_json(approval_decision_placeholder_path)
    approval_transition_payload = _load_json(approval_transition_stub_path)
    if not approval_transition_stub_path.exists():
        approval_transition_payload = build_approval_transition_stub(task_dir.name, approval_decision=approval_decision_payload)
        manager.write_json('approval_transition_stub.json', approval_transition_payload)
        closure_changed = True
    if not approval_transition_payload:
        approval_transition_payload = _load_json(approval_transition_stub_path)
    if not human_approval_result_stub_path.exists():
        manager.write_json('human_approval_result_stub.json', build_human_approval_result_stub(task_dir.name, approval_transition=approval_transition_payload))
        closure_changed = True
    if not release_action_stub_path.exists():
        manager.write_json('release_action_stub.json', build_release_action_stub(task_dir.name, formalization_gate=gate))
        closure_changed = True
    release_preflight_payload = _load_json(release_preflight_stub_path)
    if not release_preflight_stub_path.exists():
        release_preflight_payload = build_release_preflight_stub(task_dir.name, task_dir)
        manager.write_json('release_preflight_stub.json', release_preflight_payload)
        closure_changed = True
    if not release_preflight_payload:
        release_preflight_payload = _load_json(release_preflight_stub_path)
    if not official_release_stub_path.exists():
        manager.write_json('official_release_stub.json', build_official_release_stub(task_dir, boundary=boundary, review=review))
        closure_changed = True
    rollback_registry_payload = _load_json(rollback_registry_entry_path)
    if not rollback_registry_entry_path.exists():
        rollback_registry_payload = build_rollback_registry_entry(task_dir.name, rollback_stub=rollback_stub, formalization_gate=gate, official_release=False)
        manager.write_json('rollback_registry_entry.json', rollback_registry_payload)
        closure_changed = True
    if not rollback_registry_payload:
        rollback_registry_payload = _load_json(rollback_registry_entry_path)
    if not pre_release_gate_path.exists():
        manager.write_json('pre_release_gate.json', build_pre_release_gate(task_dir.name, formalization_gate=gate, approval_outcome=approval_outcome_payload, release_preflight=release_preflight_payload, rollback_registry=rollback_registry_payload))
        closure_changed = True
    pre_release_gate_payload = _load_json(pre_release_gate_path)
    if not human_approval_input_slot_path.exists():
        manager.write_json('human_approval_input_slot.json', build_human_approval_input_slot(task_dir.name, pre_release_gate=pre_release_gate_payload, human_approval_result=_load_json(human_approval_result_stub_path)))
        closure_changed = True
    closure_consistency_payload = _load_json(release_closure_consistency_path)
    if not release_closure_consistency_path.exists():
        closure_consistency_payload = build_release_closure_consistency(task_dir.name, approval_record=_load_json(approval_record_path), approval_checklist=approval_checklist_payload, approval_outcome=approval_outcome_payload, release_action=_load_json(release_action_stub_path), release_preflight=release_preflight_payload, pre_release_gate=pre_release_gate_payload, rollback_registry=rollback_registry_payload)
        manager.write_json('release_closure_consistency.json', closure_consistency_payload)
        closure_changed = True
    if not closure_consistency_payload:
        closure_consistency_payload = _load_json(release_closure_consistency_path)
    if not official_release_rehearsal_path.exists():
        manager.write_json('official_release_rehearsal.json', build_official_release_rehearsal(task_dir.name, pre_release_gate=pre_release_gate_payload, closure_consistency=closure_consistency_payload, approval_outcome=approval_outcome_payload, release_action=_load_json(release_action_stub_path)))
        closure_changed = True
    if not release_execution_guardrail_path.exists():
        manager.write_json('release_execution_guardrail.json', build_release_execution_guardrail(task_dir.name, approval_decision=approval_decision_payload, pre_release_gate=pre_release_gate_payload, human_approval_result=_load_json(human_approval_result_stub_path)))
        closure_changed = True
    if not post_approval_guardrail_transition_path.exists():
        manager.write_json('post_approval_guardrail_transition.json', build_post_approval_guardrail_transition(task_dir.name, human_approval_result=_load_json(human_approval_result_stub_path), release_execution_guardrail=_load_json(release_execution_guardrail_path)))
        closure_changed = True
    if not official_release_state_placeholder_path.exists():
        manager.write_json('official_release_state_placeholder.json', build_official_release_state_placeholder(task_dir.name, approval_transition=approval_transition_payload, release_execution_guardrail=_load_json(release_execution_guardrail_path), human_approval_result=_load_json(human_approval_result_stub_path)))
        closure_changed = True
    if not approval_recompute_snapshot_path.exists():
        manager.write_json('approval_recompute_snapshot.json', build_approval_recompute_snapshot(task_dir.name, human_approval_result=_load_json(human_approval_result_stub_path), pre_release_gate=pre_release_gate_payload, official_release_rehearsal=_load_json(official_release_rehearsal_path), release_execution_guardrail=_load_json(release_execution_guardrail_path), official_release_state=_load_json(official_release_state_placeholder_path)))
        closure_changed = True
    if not release_artifact_binding_path.exists():
        manager.write_json('release_artifact_binding.json', build_release_artifact_binding(task_dir.name, task_dir, rollback_stub=rollback_stub))
        closure_changed = True
    if not official_release_pipeline_summary_path.exists():
        manager.write_json(
            'official_release_pipeline_summary.json',
            build_official_release_pipeline_summary(
                task_dir.name,
                pre_release_gate=pre_release_gate_payload,
                official_release_rehearsal=_load_json(official_release_rehearsal_path),
                release_execution_guardrail=_load_json(release_execution_guardrail_path),
                official_release_state=_load_json(official_release_state_placeholder_path),
                release_artifact_binding=_load_json(release_artifact_binding_path),
                rollback_registry=rollback_registry_payload,
                human_approval_result=_load_json(human_approval_result_stub_path),
                approval_recompute_snapshot=_load_json(approval_recompute_snapshot_path),
            ),
        )
        closure_changed = True
    result['closure_backfilled'] = closure_changed

    if not result['quality_backfilled'] and not result['formalization_backfilled'] and not result['closure_backfilled']:
        result['skipped'] = True
        result['reason'] = 'artifacts_already_present'
    return result


def backfill_jobs(jobs_root: str | Path = JOBS_ROOT, limit: int = 0) -> dict[str, Any]:
    jobs_root = Path(jobs_root)
    items: list[dict[str, Any]] = []
    processed = 0
    quality_count = 0
    formalization_count = 0
    closure_count = 0

    for task_dir in sorted(jobs_root.iterdir()):
        if not task_dir.is_dir() or task_dir.name.startswith('_'):
            continue
        item = backfill_task(task_dir)
        items.append(item)
        processed += 1
        if item.get('quality_backfilled'):
            quality_count += 1
        if item.get('formalization_backfilled'):
            formalization_count += 1
        if item.get('closure_backfilled'):
            closure_count += 1
        if limit and processed >= limit:
            break

    return {
        'jobs_scanned': processed,
        'quality_backfilled_count': quality_count,
        'formalization_backfilled_count': formalization_count,
        'closure_backfilled_count': closure_count,
        'items': items,
    }
