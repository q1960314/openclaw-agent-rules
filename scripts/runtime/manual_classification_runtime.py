#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from artifact_manager import ArtifactManager
from execution_protocol_runtime import sync_all_execution_protocols
from post_execution_observation_runtime import (
    JOBS_ROOT,
    TARGET_CONFIG,
    RESOLUTION_TAXONOMY,
    _build_closure_audit_payload,
    _build_followup_resolution_review,
    _load_json,
    _normalize_resolution_category,
    _now,
    _resolution_taxonomy_payload,
    _resolve_task_dir,
    _sync_followup_backfill,
)

WORKFLOW_OPEN_STATES = {'pending', 'claimed', 'classified', 'confirmed'}
ACTION_TO_STATE = {
    'claim': 'claimed',
    'assign': '__preserve__',
    'classify': 'classified',
    'confirm': 'confirmed',
    'close': 'closed',
}
ALLOWED = {
    'claim': {'pending', 'claimed'},
    'assign': {'pending', 'claimed', 'classified', 'confirmed'},
    'classify': {'pending', 'claimed', 'classified'},
    'confirm': {'classified', 'confirmed'},
    'close': {'classified', 'confirmed'},
}


def _artifact_name(target: str) -> str:
    return TARGET_CONFIG[target]['manual_classification_artifact']


def _base_workflow(*, task_dir: Path, target: str, followup: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    backfill = dict(followup.get('followup_backfill') or {})
    manual_required_reason = []
    if backfill.get('manual_classification_required'):
        manual_required_reason.append('backfill_manual_classification_required')
    if not _normalize_resolution_category(followup.get('followup_resolution_category')):
        manual_required_reason.append('resolution_category_missing')
    workflow = {
        'task_id': task_dir.name,
        'execution_target': TARGET_CONFIG[target]['label'],
        'batch_id': observation.get('batch_id'),
        'run_id': observation.get('run_id'),
        'state': 'closed' if not manual_required_reason else 'pending',
        'open': bool(manual_required_reason),
        'assignee': followup.get('followup_assignee'),
        'claimed_by': None,
        'claimed_at': None,
        'classified_by': None,
        'classified_at': None,
        'confirmed_by': None,
        'confirmed_at': None,
        'closed_by': None,
        'closed_at': None,
        'pending_reason': manual_required_reason,
        'original_resolution_category': followup.get('followup_resolution_category'),
        'original_resolution_taxonomy': (followup.get('followup_resolution_taxonomy') or {}).get('taxonomy'),
        'selected_resolution_category': followup.get('followup_resolution_category'),
        'selected_resolution_taxonomy': (followup.get('followup_resolution_taxonomy') or {}).get('taxonomy'),
        'selected_resolution_summary': followup.get('followup_resolution_summary') or '',
        'classification_note': '',
        'audit_trail': [],
        'generated_at': _now(),
    }
    return workflow


def _ensure_workflow(task_dir: Path, target: str, followup: dict[str, Any], observation: dict[str, Any], manager: ArtifactManager) -> tuple[dict[str, Any], Path]:
    path = task_dir / 'artifacts' / _artifact_name(target)
    workflow = _load_json(path)
    if not workflow:
        workflow = _base_workflow(task_dir=task_dir, target=target, followup=followup, observation=observation)
        manager.write_json(path.name, workflow)
    return workflow, path


def _append_audit(workflow: dict[str, Any], *, action: str, actor: str, note: str = '', extra: dict[str, Any] | None = None) -> None:
    audit = list(workflow.get('audit_trail', []) or [])
    entry = {
        'action': action,
        'actor': actor,
        'at': _now(),
        'state': workflow.get('state'),
        'note': note,
    }
    if extra:
        entry.update(extra)
    audit.append(entry)
    workflow['audit_trail'] = audit


def apply_manual_classification_action(*, task_dir: str | Path | None = None, task_id: str | None = None, target: str, action: str, acted_by: str = 'human', assignee: str = '', resolution_category: str = '', resolution_summary: str = '', note: str = '', jobs_root: str | Path = JOBS_ROOT) -> dict[str, Any]:
    resolved_task_dir = _resolve_task_dir(task_dir=task_dir, task_id=task_id, jobs_root=jobs_root)
    manager = ArtifactManager(resolved_task_dir)
    observation = _load_json(resolved_task_dir / 'artifacts' / 'post_execution_observation.json')
    if not observation:
        raise FileNotFoundError('missing required artifact: post_execution_observation.json')
    followup_path = resolved_task_dir / 'artifacts' / f'{target}_observation_followup_protocol.json'
    followup = _load_json(followup_path)
    if not followup:
        raise FileNotFoundError(f'missing required artifact: {followup_path.name}')

    workflow, workflow_path = _ensure_workflow(resolved_task_dir, target, followup, observation, manager)
    current_state = str(workflow.get('state') or 'pending').strip().lower()
    if action not in ACTION_TO_STATE:
        raise ValueError(f'unsupported manual classification action: {action}')
    if current_state not in ALLOWED[action]:
        raise ValueError(f'manual classification action {action} not allowed from state {current_state}')
    next_state = current_state if ACTION_TO_STATE[action] == '__preserve__' else ACTION_TO_STATE[action]

    normalized_category = _normalize_resolution_category(resolution_category) or _normalize_resolution_category(workflow.get('selected_resolution_category')) or _normalize_resolution_category(followup.get('followup_resolution_category'))
    normalized_summary = str(resolution_summary or workflow.get('selected_resolution_summary') or followup.get('followup_resolution_summary') or '').strip()
    if action in {'classify', 'confirm', 'close'} and not normalized_category:
        raise ValueError(f'{action} requires resolution_category')

    if action == 'claim':
        workflow['claimed_by'] = acted_by
        workflow['claimed_at'] = _now()
        if not workflow.get('assignee'):
            workflow['assignee'] = acted_by
    elif action == 'assign':
        if not str(assignee).strip():
            raise ValueError('assign requires assignee')
        workflow['assignee'] = str(assignee).strip()
    elif action == 'classify':
        workflow['classified_by'] = acted_by
        workflow['classified_at'] = _now()
        workflow['selected_resolution_category'] = normalized_category
        workflow['selected_resolution_taxonomy'] = RESOLUTION_TAXONOMY.get(normalized_category)
        workflow['selected_resolution_summary'] = normalized_summary or note
        workflow['classification_note'] = note
        followup['followup_resolution_category'] = normalized_category
        followup['followup_resolution_taxonomy'] = _resolution_taxonomy_payload(normalized_category)
        followup['followup_resolution_summary'] = normalized_summary or note
        backfill = dict(followup.get('followup_backfill') or {})
        backfill['manual_classification_candidate'] = {
            'category': normalized_category,
            'taxonomy': RESOLUTION_TAXONOMY.get(normalized_category),
            'summary': normalized_summary or note,
            'classified_by': acted_by,
            'classified_at': workflow['classified_at'],
            'pending_close': True,
        }
        followup['followup_backfill'] = backfill
    elif action == 'confirm':
        workflow['confirmed_by'] = acted_by
        workflow['confirmed_at'] = _now()
    elif action == 'close':
        workflow['closed_by'] = acted_by
        workflow['closed_at'] = _now()
        workflow['open'] = False
        workflow['selected_resolution_category'] = normalized_category
        workflow['selected_resolution_taxonomy'] = RESOLUTION_TAXONOMY.get(normalized_category)
        workflow['selected_resolution_summary'] = normalized_summary or note
        backfill = dict(followup.get('followup_backfill') or {})
        backfill.update({
            'checked_at': _now(),
            'checked_by': acted_by,
            'followup_state': followup.get('followup_item_state'),
            'manual_classification_required': False,
            'manual_classification_completed_at': workflow['closed_at'],
            'manual_classification_completed_by': acted_by,
            'manual_classification_reason': workflow.get('pending_reason') or [],
            'manual_classification_category': normalized_category,
            'manual_classification_taxonomy': RESOLUTION_TAXONOMY.get(normalized_category),
        })
        followup['followup_backfill'] = backfill
        followup['followup_resolution_category'] = normalized_category
        followup['followup_resolution_taxonomy'] = _resolution_taxonomy_payload(normalized_category)
        followup['followup_resolution_summary'] = normalized_summary or note or followup.get('followup_resolution_summary') or ''
        followup['manual_classification_completed_at'] = workflow['closed_at']
        followup['manual_classification_completed_by'] = acted_by
        if followup.get('followup_item_state') == 'closed':
            closure_audit = dict(followup.get('followup_closure_audit') or {})
            closure_audit.update(_build_closure_audit_payload(
                followup=followup,
                observation=observation,
                category=normalized_category,
                closed_at=followup.get('followup_closed_at') or workflow['closed_at'],
                closed_by=closure_audit.get('closed_by') or followup.get('followup_last_actor') or acted_by,
            ) or {})
            closure_audit['manual_classification'] = {
                'completed_by': acted_by,
                'completed_at': workflow['closed_at'],
                'pending_reason': workflow.get('pending_reason') or [],
                'selected_category': normalized_category,
                'selected_taxonomy': RESOLUTION_TAXONOMY.get(normalized_category),
                'confirmed_by': workflow.get('confirmed_by'),
                'confirmed_at': workflow.get('confirmed_at'),
            }
            followup['followup_closure_audit'] = closure_audit

    workflow['state'] = next_state
    if next_state != 'closed':
        workflow['open'] = True
    _append_audit(workflow, action=action, actor=acted_by, note=note, extra={
        'assignee': workflow.get('assignee'),
        'selected_resolution_category': workflow.get('selected_resolution_category'),
        'selected_resolution_taxonomy': workflow.get('selected_resolution_taxonomy'),
        'pending_reason': workflow.get('pending_reason') or [],
    })

    followup['manual_classification_workflow'] = {
        'artifact': workflow_path.name,
        'state': workflow.get('state'),
        'open': workflow.get('open'),
        'assignee': workflow.get('assignee'),
        'claimed_by': workflow.get('claimed_by'),
        'claimed_at': workflow.get('claimed_at'),
        'classified_by': workflow.get('classified_by'),
        'classified_at': workflow.get('classified_at'),
        'confirmed_by': workflow.get('confirmed_by'),
        'confirmed_at': workflow.get('confirmed_at'),
        'closed_by': workflow.get('closed_by'),
        'closed_at': workflow.get('closed_at'),
        'pending_reason': workflow.get('pending_reason') or [],
        'selected_resolution_category': workflow.get('selected_resolution_category'),
        'selected_resolution_taxonomy': workflow.get('selected_resolution_taxonomy'),
        'selected_resolution_summary': workflow.get('selected_resolution_summary') or '',
        'last_actor': acted_by,
        'last_action': action,
        'last_action_at': _now(),
        'audit_count': len(workflow.get('audit_trail') or []),
    }

    _sync_followup_backfill(task_dir=resolved_task_dir, observation=observation, followup=followup, manager=manager)
    manager.write_json(followup_path.name, followup)
    manager.write_json(workflow_path.name, workflow)
    manager.append_log('manual_classification_runtime.log', json.dumps({
        'time': _now(),
        'task_id': resolved_task_dir.name,
        'target': target,
        'action': action,
        'state': workflow.get('state'),
        'actor': acted_by,
        'assignee': workflow.get('assignee'),
        'selected_resolution_category': workflow.get('selected_resolution_category'),
    }, ensure_ascii=False))
    sync_all_execution_protocols(resolved_task_dir)
    review_payload = _build_followup_resolution_review(task_dir=resolved_task_dir, target=target, observation=observation, followup=followup)
    manager.write_json(TARGET_CONFIG[target]['resolution_review_artifact'], review_payload)
    return {'workflow': workflow, 'followup': followup, 'review': review_payload}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('apply')
    p.add_argument('--target', required=True, choices=sorted(TARGET_CONFIG.keys()))
    p.add_argument('--task-dir', default='')
    p.add_argument('--task-id', default='')
    p.add_argument('--jobs-root', default=str(JOBS_ROOT))
    p.add_argument('--action-name', required=True, choices=sorted(ACTION_TO_STATE.keys()))
    p.add_argument('--acted-by', default='human')
    p.add_argument('--assignee', default='')
    p.add_argument('--resolution-category', default='')
    p.add_argument('--resolution-summary', default='')
    p.add_argument('--note', default='')
    args = parser.parse_args()
    result = apply_manual_classification_action(task_dir=args.task_dir or None, task_id=args.task_id or None, target=args.target, action=args.action_name, acted_by=args.acted_by, assignee=args.assignee, resolution_category=args.resolution_category, resolution_summary=args.resolution_summary, note=args.note, jobs_root=args.jobs_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
