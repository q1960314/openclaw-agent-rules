#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from human_approval_runtime import record_human_approval
from manual_execution_confirmation_runtime import confirm_execution
from manual_release_registration_runtime import record_manual_release, record_manual_rollback
from post_execution_observation_runtime import apply_followup_action, fail_observation_window
from validate_execution_binding_observation import _reset_task
from worker_runtime_scheduler import run_cycle

ROOT = Path('/home/admin/.openclaw/workspace/master')
JOBS_ROOT = ROOT / 'traces' / 'jobs'
PREFIX = 'validation_resolution_knowledge_linkage_'


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _force_timeout(task_dir: Path) -> None:
    path = task_dir / 'artifacts' / 'post_execution_observation.json'
    payload = _load_json(path)
    opened_at = datetime.fromisoformat(payload['opened_at'])
    deadline_at = opened_at - timedelta(minutes=20)
    overdue_at = deadline_at + timedelta(minutes=5)
    timeout_at = deadline_at + timedelta(minutes=10)
    payload.update({
        'deadline_at': deadline_at.isoformat(),
        'overdue_at': overdue_at.isoformat(),
        'timeout_at': timeout_at.isoformat(),
        'sla_seconds': -1200,
        'overdue_grace_seconds': 300,
        'timeout_grace_seconds': 600,
    })
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def _prepare_release_manual(task_suffix: str) -> Path:
    task_dir = _reset_task(f'{PREFIX}{task_suffix}')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-linkage-a', reason='manual classification linkage release')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='validator-linkage-a', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='validator-linkage-a', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-linkage-manual', executed_by='validator-linkage-a', summary='manual classification linkage validation')
    _force_timeout(task_dir)
    return task_dir


def _prepare_release_resolved(task_suffix: str) -> Path:
    return _prepare_release_manual(task_suffix)


def _prepare_rollback_resolved(task_suffix: str) -> Path:
    task_dir = _reset_task(f'{PREFIX}{task_suffix}')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-linkage-b', reason='manual classification linkage rollback')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='validator-linkage-b', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='validator-linkage-b', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-linkage-before-rollback', executed_by='validator-linkage-b', summary='prepare rollback linkage validation')
    confirm_execution(task_dir=task_dir, target='rollback', action='start', confirmed_by='validator-linkage-b', note='rollback start')
    confirm_execution(task_dir=task_dir, target='rollback', action='complete', confirmed_by='validator-linkage-b', note='rollback complete')
    record_manual_rollback(task_dir=task_dir, rollback_version='rb-linkage-effective', executed_by='validator-linkage-b', reason='rollback linkage validation')
    fail_observation_window(task_dir=task_dir, target='rollback', failed_by='validator-linkage-b', note='rollback linkage validation failed and needs confirmation', anomaly_findings=['rollback_linkage_anomaly'], signal_count=0)
    return task_dir


def main() -> int:
    release_manual = _prepare_release_manual('release_manual_required')
    release_resolved = _prepare_release_resolved('release_resolved')
    rollback_resolved = _prepare_rollback_resolved('rollback_resolved')

    run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-resolution-knowledge-linkage-bootstrap', backfill_missing=True)

    apply_followup_action(task_dir=release_resolved, target='release', action='assign', acted_by='lead-linkage', assignee='ops-monitor', note='assign release linkage')
    apply_followup_action(task_dir=release_resolved, target='release', action='handoff', acted_by='lead-linkage', assignee='coder', note='handoff release linkage to coder')
    apply_followup_action(task_dir=release_resolved, target='release', action='accept', acted_by='coder', note='coder accepts release linkage')
    apply_followup_action(task_dir=release_resolved, target='release', action='resolve', acted_by='coder', resolution_category='code_fix_required', resolution_summary='Patched release linkage issue and verified evidence chain', note='resolved release linkage issue')
    apply_followup_action(task_dir=release_resolved, target='release', action='close', acted_by='coder', note='close release linkage after verification')

    apply_followup_action(task_dir=rollback_resolved, target='rollback', action='assign', acted_by='lead-linkage-rb', assignee='ops-monitor', note='assign rollback linkage')
    apply_followup_action(task_dir=rollback_resolved, target='rollback', action='handoff', acted_by='lead-linkage-rb', assignee='test-expert', note='handoff rollback linkage to test-expert')
    apply_followup_action(task_dir=rollback_resolved, target='rollback', action='accept', acted_by='test-expert', note='test-expert accepts rollback linkage')
    apply_followup_action(task_dir=rollback_resolved, target='rollback', action='resolve', acted_by='test-expert', resolution_category='rollback_effective', resolution_summary='Rollback linkage validation confirmed safe fallback state', note='rollback linkage resolved')
    apply_followup_action(task_dir=rollback_resolved, target='rollback', action='close', acted_by='test-expert', note='close rollback linkage after validation')

    cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-resolution-knowledge-linkage', backfill_missing=True)

    latest_cycle = _load_json(ROOT / 'reports' / 'worker-runtime' / 'state' / 'latest_cycle.json')
    latest_stage_card = _load_json(ROOT / 'reports' / 'worker-runtime' / 'state' / 'latest_stage_card.json')
    latest_review = _load_json(ROOT / 'reports' / 'worker-runtime' / 'state' / 'latest_followup_resolution_review.json')

    stage_signals = latest_stage_card.get('signals') or {}
    backlog = latest_review.get('manual_classification_backlog') or {}
    backlog_items = backlog.get('items') or []
    recent_insights = latest_review.get('recent_closure_insights') or []
    knowledge_candidates = latest_review.get('knowledge_candidate_items') or []

    _assert(backlog.get('count', 0) >= 1, 'manual classification backlog should be generated')
    _assert(any(item.get('task_id') == release_manual.name for item in backlog_items), 'release manual fixture should enter unified backlog')
    _assert(latest_cycle.get('manual_classification_backlog_count', 0) >= 1, 'latest_cycle should expose manual classification backlog count')
    _assert('manual_classification_unresolved_items' in latest_cycle, 'latest_cycle should expose unresolved classification items field')
    _assert(stage_signals.get('manual_classification_backlog_count', 0) >= 1, 'stage card should expose manual classification backlog count')
    _assert('followup_resolution_digest_available' in stage_signals and stage_signals.get('followup_resolution_digest_available') is True, 'stage card should expose resolution digest signal')
    _assert((latest_review.get('resolution_taxonomy_theme_counts') or {}).get('code', 0) >= 1, 'review digest should expose release taxonomy theme')
    _assert((latest_review.get('resolution_taxonomy_theme_counts') or {}).get('rollback_validation', 0) >= 1, 'review digest should expose rollback taxonomy theme')
    _assert(any(item.get('task_id') == release_resolved.name for item in recent_insights), 'digest should include resolved release closure insight')
    _assert(any(item.get('task_id') == rollback_resolved.name for item in recent_insights), 'digest should include resolved rollback closure insight')
    _assert(any(item.get('task_id') == release_manual.name and (item.get('knowledge_linkage') or {}).get('cycle_level_candidate') for item in knowledge_candidates), 'manual classification item should become knowledge linkage candidate')
    _assert((latest_cycle.get('followup_target_resolution_category_counts') or {}).get('release', {}).get('needs_manual_classification', 0) >= 1, 'release side should expose needs_manual_classification')
    _assert((latest_cycle.get('followup_target_resolution_category_counts') or {}).get('rollback', {}).get('rollback_effective', 0) >= 1, 'rollback side should expose rollback_effective')

    result = {
        'cycle_id': cycle.get('cycle_id'),
        'manual_backlog': backlog,
        'latest_cycle_signals': {
            'manual_classification_backlog_count': latest_cycle.get('manual_classification_backlog_count'),
            'manual_classification_unresolved_count': latest_cycle.get('manual_classification_unresolved_count'),
            'followup_resolution_digest_available': latest_cycle.get('followup_resolution_digest_available'),
            'recent_closure_knowledge_themes': latest_cycle.get('recent_closure_knowledge_themes'),
            'followup_resolution_taxonomy_theme_counts': latest_cycle.get('followup_resolution_taxonomy_theme_counts'),
            'followup_target_resolution_category_counts': latest_cycle.get('followup_target_resolution_category_counts'),
        },
        'stage_card_signals': {
            'manual_classification_backlog_count': stage_signals.get('manual_classification_backlog_count'),
            'manual_classification_unresolved_count': stage_signals.get('manual_classification_unresolved_count'),
            'followup_resolution_digest_available': stage_signals.get('followup_resolution_digest_available'),
            'recent_closure_knowledge_themes': stage_signals.get('recent_closure_knowledge_themes'),
            'followup_resolution_taxonomy_theme_counts': stage_signals.get('followup_resolution_taxonomy_theme_counts'),
        },
        'recent_closure_insights': recent_insights,
        'knowledge_candidate_items': knowledge_candidates,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
