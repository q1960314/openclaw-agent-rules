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
from release_closure_runtime import load_release_closure_snapshot
from validate_execution_binding_observation import _reset_task
from worker_runtime_scheduler import run_cycle

ROOT = Path('/home/admin/.openclaw/workspace/master')
JOBS_ROOT = ROOT / 'traces' / 'jobs'
PREFIX = 'validation_followup_ownership_'


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


def _prepare_release_timeout(task_suffix: str) -> Path:
    task_dir = _reset_task(f'{PREFIX}{task_suffix}')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-followup-a', reason='follow-up ownership timeout release')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='validator-followup-a', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='validator-followup-a', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-followup-timeout', executed_by='validator-followup-a', summary='timeout ownership validation')
    _force_timeout(task_dir)
    return task_dir


def _prepare_rollback_failed(task_suffix: str) -> Path:
    task_dir = _reset_task(f'{PREFIX}{task_suffix}')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-followup-b', reason='follow-up ownership failed rollback')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='validator-followup-b', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='validator-followup-b', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-followup-before-rollback', executed_by='validator-followup-b', summary='prepare rollback validation')
    confirm_execution(task_dir=task_dir, target='rollback', action='start', confirmed_by='validator-followup-b', note='rollback start')
    confirm_execution(task_dir=task_dir, target='rollback', action='complete', confirmed_by='validator-followup-b', note='rollback complete')
    record_manual_rollback(task_dir=task_dir, rollback_version='rb-followup-failed', executed_by='validator-followup-b', reason='failed rollback validation')
    fail_observation_window(task_dir=task_dir, target='rollback', failed_by='validator-followup-b', note='rollback failed for follow-up ownership validation', anomaly_findings=['anomaly_rb'], signal_count=0)
    return task_dir


def main() -> int:
    timed_out_release = _prepare_release_timeout('release_timeout_assign_handoff')
    failed_rollback = _prepare_rollback_failed('rollback_failed_assign_handoff')

    first_cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-followup-ownership-initial', backfill_missing=True)

    apply_followup_action(task_dir=timed_out_release, target='release', action='assign', acted_by='lead-ops', assignee='ops-monitor', note='assign timed_out release follow-up to ops')
    apply_followup_action(task_dir=timed_out_release, target='release', action='handoff', acted_by='lead-ops', assignee='coder', note='handoff timed_out release follow-up to coder')
    apply_followup_action(task_dir=timed_out_release, target='release', action='accept', acted_by='coder', note='coder accepts ownership')
    apply_followup_action(task_dir=timed_out_release, target='release', action='resolve', acted_by='coder', resolution_category='code_fix_required', resolution_summary='Patched release-side observation issue and validated evidence chain', note='resolved with code-side remediation')
    apply_followup_action(task_dir=timed_out_release, target='release', action='close', acted_by='coder', note='close timed_out release follow-up after audit-ready verification')

    apply_followup_action(task_dir=failed_rollback, target='rollback', action='assign', acted_by='lead-rollback', assignee='ops-monitor', note='assign failed rollback follow-up to ops')
    apply_followup_action(task_dir=failed_rollback, target='rollback', action='handoff', acted_by='lead-rollback', assignee='test-expert', note='handoff failed rollback follow-up to validator')
    apply_followup_action(task_dir=failed_rollback, target='rollback', action='accept', acted_by='test-expert', note='test-expert accepts rollback ownership')
    apply_followup_action(task_dir=failed_rollback, target='rollback', action='resolve', acted_by='test-expert', resolution_category='rollback_effective', resolution_summary='Confirmed rollback cleared the risky state after manual evidence review', note='rollback issue resolved')
    apply_followup_action(task_dir=failed_rollback, target='rollback', action='close', acted_by='test-expert', note='close failed rollback follow-up with closure audit')

    second_cycle = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-followup-ownership-final', backfill_missing=True)

    timed_out_snapshot = load_release_closure_snapshot(timed_out_release)
    failed_snapshot = load_release_closure_snapshot(failed_rollback)
    timed_out_followup = _load_json(timed_out_release / 'artifacts' / 'release_observation_followup_protocol.json')
    failed_followup = _load_json(failed_rollback / 'artifacts' / 'rollback_observation_followup_protocol.json')
    timed_out_history = _load_json(timed_out_release / 'artifacts' / 'observation_history_aggregate.json')
    failed_history = _load_json(failed_rollback / 'artifacts' / 'observation_history_aggregate.json')
    latest_cycle = _load_json(ROOT / 'reports' / 'worker-runtime' / 'state' / 'latest_cycle.json')
    latest_stage_card = _load_json(ROOT / 'reports' / 'worker-runtime' / 'state' / 'latest_stage_card.json')
    stage_signals = (latest_stage_card.get('signals') or {})

    _assert(timed_out_snapshot.get('post_execution_observation_state') == 'observation_timed_out', 'timed_out release fixture should remain timed_out')
    _assert(failed_snapshot.get('post_execution_observation_state') == 'observation_failed', 'failed rollback fixture should remain failed')
    _assert(timed_out_snapshot.get('post_execution_observation_followup_item_state') == 'closed', 'timed_out release follow-up should reach closed')
    _assert(failed_snapshot.get('post_execution_observation_followup_item_state') == 'closed', 'failed rollback follow-up should reach closed')
    _assert(timed_out_followup.get('followup_assignee') == 'coder', 'timed_out release should retain final assignee after handoff')
    _assert(failed_followup.get('followup_assignee') == 'test-expert', 'failed rollback should retain final assignee after handoff')
    _assert(int(timed_out_followup.get('followup_handoff_count') or 0) >= 1, 'timed_out release should record handoff history')
    _assert(int(failed_followup.get('followup_handoff_count') or 0) >= 1, 'failed rollback should record handoff history')
    _assert(timed_out_followup.get('followup_resolution_category') == 'code_fix_required', 'timed_out release should store resolution category')
    _assert(failed_followup.get('followup_resolution_category') == 'rollback_effective', 'failed rollback should store resolution category')
    _assert((timed_out_followup.get('followup_closure_audit') or {}).get('resolution_category') == 'code_fix_required', 'timed_out release closure audit should capture resolution category')
    _assert((failed_followup.get('followup_closure_audit') or {}).get('resolution_category') == 'rollback_effective', 'failed rollback closure audit should capture resolution category')
    _assert(any((entry.get('action') == 'handoff' and entry.get('assignee') == 'coder') for entry in (timed_out_followup.get('followup_history') or [])), 'timed_out release history should retain handoff trace')
    _assert(any((entry.get('action') == 'handoff' and entry.get('assignee') == 'test-expert') for entry in (failed_followup.get('followup_history') or [])), 'failed rollback history should retain handoff trace')
    _assert(any((item.get('followup_closure_audit') or {}).get('resolution_category') == 'code_fix_required' for item in (timed_out_history.get('recent_results') or [])), 'history aggregate should preserve timed_out release closure audit trail')
    _assert(any((item.get('followup_closure_audit') or {}).get('resolution_category') == 'rollback_effective' for item in (failed_history.get('recent_results') or [])), 'history aggregate should preserve failed rollback closure audit trail')
    _assert(latest_cycle.get('followup_assigned_count', 0) >= 2, 'latest_cycle should expose assigned follow-up count')
    _assert(latest_cycle.get('followup_handoff_count', 0) >= 2, 'latest_cycle should expose handoff count')
    _assert((latest_cycle.get('followup_resolution_category_counts') or {}).get('code_fix_required', 0) >= 1, 'latest_cycle should expose code_fix_required resolution category')
    _assert((latest_cycle.get('followup_resolution_category_counts') or {}).get('rollback_effective', 0) >= 1, 'latest_cycle should expose rollback_effective resolution category')
    _assert(any(item.get('task_id') == timed_out_release.name for item in (latest_cycle.get('recently_closed_followup_items') or [])), 'latest_cycle should expose recently closed timed_out release item')
    _assert(any(item.get('task_id') == failed_rollback.name for item in (latest_cycle.get('recently_closed_followup_items') or [])), 'latest_cycle should expose recently closed failed rollback item')
    _assert(stage_signals.get('followup_assigned_count', 0) >= 2, 'stage card should expose assigned follow-up count')
    _assert(stage_signals.get('followup_unassigned_count', 0) >= 0, 'stage card should expose unassigned follow-up count')
    _assert(stage_signals.get('followup_handoff_count', 0) >= 2, 'stage card should expose handoff count')
    _assert((stage_signals.get('followup_resolution_category_counts') or {}).get('code_fix_required', 0) >= 1, 'stage card should expose code_fix_required resolution category')
    _assert((stage_signals.get('followup_resolution_category_counts') or {}).get('rollback_effective', 0) >= 1, 'stage card should expose rollback_effective resolution category')
    _assert(any(item.get('task_id') == timed_out_release.name for item in (stage_signals.get('recently_closed_followup_items') or [])), 'stage card should expose recently closed release follow-up')
    _assert(any(item.get('task_id') == failed_rollback.name for item in (stage_signals.get('recently_closed_followup_items') or [])), 'stage card should expose recently closed rollback follow-up')

    result = {
        'initial_cycle_id': first_cycle.get('cycle_id'),
        'final_cycle_id': second_cycle.get('cycle_id'),
        'timed_out_release': {
            'task_id': timed_out_release.name,
            'state': timed_out_snapshot.get('post_execution_observation_state'),
            'followup_state': timed_out_snapshot.get('post_execution_observation_followup_item_state'),
            'assignee': timed_out_snapshot.get('post_execution_observation_followup_assignee'),
            'handoff_count': timed_out_snapshot.get('post_execution_observation_followup_handoff_count'),
            'resolution_category': timed_out_snapshot.get('post_execution_observation_followup_resolution_category'),
            'closure_audit': timed_out_snapshot.get('post_execution_observation_followup_closure_audit'),
        },
        'failed_rollback': {
            'task_id': failed_rollback.name,
            'state': failed_snapshot.get('post_execution_observation_state'),
            'followup_state': failed_snapshot.get('post_execution_observation_followup_item_state'),
            'assignee': failed_snapshot.get('post_execution_observation_followup_assignee'),
            'handoff_count': failed_snapshot.get('post_execution_observation_followup_handoff_count'),
            'resolution_category': failed_snapshot.get('post_execution_observation_followup_resolution_category'),
            'closure_audit': failed_snapshot.get('post_execution_observation_followup_closure_audit'),
        },
        'latest_cycle_followup_metrics': {
            'assigned_count': latest_cycle.get('followup_assigned_count'),
            'unassigned_count': latest_cycle.get('followup_unassigned_count'),
            'handoff_count': latest_cycle.get('followup_handoff_count'),
            'resolution_category_counts': latest_cycle.get('followup_resolution_category_counts'),
            'recently_closed_followup_items': latest_cycle.get('recently_closed_followup_items'),
        },
        'stage_card_followup_metrics': {
            'assigned_count': stage_signals.get('followup_assigned_count'),
            'unassigned_count': stage_signals.get('followup_unassigned_count'),
            'handoff_count': stage_signals.get('followup_handoff_count'),
            'resolution_category_counts': stage_signals.get('followup_resolution_category_counts'),
            'recently_closed_followup_items': stage_signals.get('recently_closed_followup_items'),
        },
        'history_trace_check': {
            'timed_out_release_recent_results': timed_out_history.get('recent_results'),
            'failed_rollback_recent_results': failed_history.get('recent_results'),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
