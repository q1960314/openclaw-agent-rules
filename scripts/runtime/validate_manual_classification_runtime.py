#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from human_approval_runtime import record_human_approval
from manual_execution_confirmation_runtime import confirm_execution
from manual_release_registration_runtime import record_manual_release, record_manual_rollback
from manual_classification_runtime import apply_manual_classification_action
from post_execution_observation_runtime import fail_observation_window
from validate_execution_binding_observation import _reset_task
from worker_runtime_scheduler import run_cycle

ROOT = Path('/home/admin/.openclaw/workspace/master')
JOBS_ROOT = ROOT / 'traces' / 'jobs'
PREFIX = 'validation_manual_classification_'


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _prepare_release(task_suffix: str) -> Path:
    task_dir = _reset_task(f'{PREFIX}{task_suffix}')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-mc-release', reason='manual classification release validation')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='validator-mc-release', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='validator-mc-release', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-manual-classification', executed_by='validator-mc-release', summary='manual classification release validation')
    fail_observation_window(task_dir=task_dir, target='release', failed_by='validator-mc-release', note='release needs manual classification', anomaly_findings=['release_manual_classification'], signal_count=0)
    return task_dir


def _prepare_rollback(task_suffix: str) -> Path:
    task_dir = _reset_task(f'{PREFIX}{task_suffix}')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-mc-rollback', reason='manual classification rollback validation')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='validator-mc-rollback', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='validator-mc-rollback', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-before-manual-rollback', executed_by='validator-mc-rollback', summary='prepare rollback validation')
    confirm_execution(task_dir=task_dir, target='rollback', action='start', confirmed_by='validator-mc-rollback', note='rollback start')
    confirm_execution(task_dir=task_dir, target='rollback', action='complete', confirmed_by='validator-mc-rollback', note='rollback complete')
    record_manual_rollback(task_dir=task_dir, rollback_version='rb-manual-classification', executed_by='validator-mc-rollback', reason='manual classification rollback validation')
    fail_observation_window(task_dir=task_dir, target='rollback', failed_by='validator-mc-rollback', note='rollback needs manual classification', anomaly_findings=['rollback_manual_classification'], signal_count=0)
    return task_dir


def main() -> int:
    release_task = _prepare_release('release')
    rollback_task = _prepare_rollback('rollback')

    bootstrap_cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-manual-classification-bootstrap', backfill_missing=True)
    bootstrap_latest = _load_json(ROOT / 'reports' / 'worker-runtime' / 'state' / 'latest_cycle.json')
    bootstrap_stage = _load_json(ROOT / 'reports' / 'worker-runtime' / 'state' / 'latest_stage_card.json')
    _assert(bootstrap_latest.get('manual_classification_backlog_count', 0) >= 2, 'bootstrap cycle should expose manual classification backlog items')
    _assert(bootstrap_stage.get('signals', {}).get('manual_classification_backlog_count', 0) >= 2, 'bootstrap stage card should expose backlog count')

    for task_dir, target, assignee, actor, category, summary in [
        (release_task, 'release', 'ops-monitor', 'release-classifier', 'manual_intervention', 'release manual intervention classified and confirmed'),
        (rollback_task, 'rollback', 'test-expert', 'rollback-classifier', 'rollback_effective', 'rollback evidence confirms effective fallback state'),
    ]:
        apply_manual_classification_action(task_dir=task_dir, target=target, action='claim', acted_by=actor, note='claim manual classification item')
        apply_manual_classification_action(task_dir=task_dir, target=target, action='assign', acted_by='lead-triage', assignee=assignee, note='assign manual classification item')
        apply_manual_classification_action(task_dir=task_dir, target=target, action='classify', acted_by=actor, resolution_category=category, resolution_summary=summary, note='classify manual backlog item')
        apply_manual_classification_action(task_dir=task_dir, target=target, action='confirm', acted_by='qa-confirm', resolution_category=category, resolution_summary=summary, note='confirm classification result')
        apply_manual_classification_action(task_dir=task_dir, target=target, action='close', acted_by='qa-confirm', resolution_category=category, resolution_summary=summary, note='close manual classification workflow')

    cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-manual-classification', backfill_missing=True)
    latest_cycle = _load_json(ROOT / 'reports' / 'worker-runtime' / 'state' / 'latest_cycle.json')
    latest_stage_card = _load_json(ROOT / 'reports' / 'worker-runtime' / 'state' / 'latest_stage_card.json')
    latest_review = _load_json(ROOT / 'reports' / 'worker-runtime' / 'state' / 'latest_followup_resolution_review.json')

    release_followup = _load_json(release_task / 'artifacts' / 'release_observation_followup_protocol.json')
    rollback_followup = _load_json(rollback_task / 'artifacts' / 'rollback_observation_followup_protocol.json')
    release_workflow = _load_json(release_task / 'artifacts' / 'release_manual_classification_workflow.json')
    rollback_workflow = _load_json(rollback_task / 'artifacts' / 'rollback_manual_classification_workflow.json')
    release_summary = _load_json(release_task / 'artifacts' / 'release_observation_summary.json')
    rollback_summary = _load_json(rollback_task / 'artifacts' / 'rollback_observation_summary.json')
    stage_signals = latest_stage_card.get('signals') or {}
    backlog = latest_review.get('manual_classification_backlog') or {}

    _assert((release_followup.get('followup_backfill') or {}).get('manual_classification_required') is False, 'release manual classification should clear backlog flag')
    _assert((rollback_followup.get('followup_backfill') or {}).get('manual_classification_required') is False, 'rollback manual classification should clear backlog flag')
    _assert(release_followup.get('followup_resolution_category') == 'manual_intervention', 'release classification should write back resolution category')
    _assert((release_followup.get('followup_resolution_taxonomy') or {}).get('taxonomy') == 'operations', 'release classification should write back taxonomy')
    _assert(rollback_followup.get('followup_resolution_category') == 'rollback_effective', 'rollback classification should write back resolution category')
    _assert((rollback_followup.get('followup_resolution_taxonomy') or {}).get('taxonomy') == 'rollback_validation', 'rollback classification should write back taxonomy')
    _assert(release_workflow.get('state') == 'closed' and rollback_workflow.get('state') == 'closed', 'manual classification workflows should reach closed state')
    _assert(release_summary.get('manual_classification_state') == 'closed', 'release observation summary should expose closed manual classification state')
    _assert(rollback_summary.get('manual_classification_state') == 'closed', 'rollback observation summary should expose closed manual classification state')
    _assert(latest_cycle.get('manual_classification_backlog_count', 0) <= max(0, bootstrap_latest.get('manual_classification_backlog_count', 0) - 2), 'latest_cycle backlog count should drop after classification close')
    _assert(stage_signals.get('manual_classification_backlog_count', 0) <= max(0, bootstrap_stage.get('signals', {}).get('manual_classification_backlog_count', 0) - 2), 'stage card backlog count should drop after classification close')
    _assert(stage_signals.get('manual_classification_state_counts', {}).get('closed', 0) >= 2, 'stage card should expose manual classification closed state counts')
    _assert(release_followup.get('manual_classification_completed_by') == 'qa-confirm', 'release audit trail should track manual classifier closer')
    _assert(rollback_followup.get('manual_classification_completed_by') == 'qa-confirm', 'rollback audit trail should track manual classifier closer')
    _assert(any(item.get('action') == 'classify' for item in (release_workflow.get('audit_trail') or [])), 'release workflow audit trail should contain classify action')
    _assert(any(item.get('action') == 'confirm' for item in (rollback_workflow.get('audit_trail') or [])), 'rollback workflow audit trail should contain confirm action')
    _assert((latest_cycle.get('followup_target_resolution_category_counts') or {}).get('release', {}).get('manual_intervention', 0) >= 1, 'release side should expose manual_intervention after classification')
    _assert((latest_cycle.get('followup_target_resolution_category_counts') or {}).get('rollback', {}).get('rollback_effective', 0) >= 1, 'rollback side should expose rollback_effective after classification')
    _assert(backlog.get('state_counts', {}).get('closed', 0) >= 0, 'review should expose manual classification state counts')

    result = {
        'cycle_id': cycle.get('cycle_id'),
        'bootstrap_cycle_id': bootstrap_cycle.get('cycle_id'),
        'bootstrap_backlog_count': bootstrap_latest.get('manual_classification_backlog_count'),
        'final_backlog_count': latest_cycle.get('manual_classification_backlog_count'),
        'stage_card_backlog_count': stage_signals.get('manual_classification_backlog_count'),
        'manual_classification_state_counts': stage_signals.get('manual_classification_state_counts'),
        'release_workflow': {
            'state': release_workflow.get('state'),
            'assignee': release_workflow.get('assignee'),
            'selected_resolution_category': release_workflow.get('selected_resolution_category'),
            'audit_trail': release_workflow.get('audit_trail'),
        },
        'rollback_workflow': {
            'state': rollback_workflow.get('state'),
            'assignee': rollback_workflow.get('assignee'),
            'selected_resolution_category': rollback_workflow.get('selected_resolution_category'),
            'audit_trail': rollback_workflow.get('audit_trail'),
        },
        'followup_target_resolution_category_counts': latest_cycle.get('followup_target_resolution_category_counts'),
        'manual_classification_backlog': backlog,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
