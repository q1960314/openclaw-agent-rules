#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from human_approval_runtime import record_human_approval
from manual_execution_confirmation_runtime import confirm_execution
from manual_release_registration_runtime import record_manual_release, record_manual_rollback
from post_execution_observation_runtime import apply_followup_action, complete_observation_window, fail_observation_window
from release_closure_runtime import load_release_closure_snapshot
from validate_execution_binding_observation import _reset_task
from worker_runtime_scheduler import run_cycle

ROOT = Path('/home/admin/.openclaw/workspace/master')
JOBS_ROOT = ROOT / 'traces' / 'jobs'
PREFIX = 'validation_observation_runtime_'


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _force_observation_deadlines(task_dir: Path, *, deadline_delta_minutes: int, overdue_grace_minutes: int, timeout_grace_minutes: int) -> None:
    observation_path = task_dir / 'artifacts' / 'post_execution_observation.json'
    observation = json.loads(observation_path.read_text(encoding='utf-8'))
    opened_at = datetime.fromisoformat(observation['opened_at'])
    deadline_at = opened_at + timedelta(minutes=deadline_delta_minutes)
    overdue_at = deadline_at + timedelta(minutes=overdue_grace_minutes)
    timeout_at = deadline_at + timedelta(minutes=timeout_grace_minutes)
    observation.update({
        'deadline_at': deadline_at.isoformat(),
        'overdue_at': overdue_at.isoformat(),
        'timeout_at': timeout_at.isoformat(),
        'sla_seconds': int((deadline_at - opened_at).total_seconds()),
        'overdue_grace_seconds': overdue_grace_minutes * 60,
        'timeout_grace_seconds': timeout_grace_minutes * 60,
    })
    observation_path.write_text(json.dumps(observation, ensure_ascii=False, indent=2), encoding='utf-8')


def scenario_release_timeout_via_scheduler() -> dict:
    task_dir = _reset_task(f'{PREFIX}release_timeout')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-runtime-a', reason='release timeout via scheduler')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='operator-runtime-a', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='operator-runtime-a', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-runtime-timeout', executed_by='operator-runtime-a', summary='release timeout validation')
    _force_observation_deadlines(task_dir, deadline_delta_minutes=-30, overdue_grace_minutes=5, timeout_grace_minutes=10)
    return {'task_id': task_dir.name}


def scenario_completed_not_timed_out() -> dict:
    task_dir = _reset_task(f'{PREFIX}completed_safe')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-runtime-b', reason='completed observation safe')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='operator-runtime-b', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='operator-runtime-b', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-runtime-complete', executed_by='operator-runtime-b', summary='release completed validation')
    complete_observation_window(task_dir=task_dir, target='release', completed_by='observer-runtime-b', note='completed before scheduler refresh', signal_count=2)
    _force_observation_deadlines(task_dir, deadline_delta_minutes=-30, overdue_grace_minutes=5, timeout_grace_minutes=10)
    return {'task_id': task_dir.name}


def scenario_rollback_timeout_via_scheduler() -> dict:
    task_dir = _reset_task(f'{PREFIX}rollback_timeout')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-runtime-c', reason='rollback timeout via scheduler')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='operator-runtime-c', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='operator-runtime-c', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-runtime-before-rollback', executed_by='operator-runtime-c', summary='prepare rollback validation')
    confirm_execution(task_dir=task_dir, target='rollback', action='start', confirmed_by='operator-runtime-c2', note='rollback start')
    confirm_execution(task_dir=task_dir, target='rollback', action='complete', confirmed_by='operator-runtime-c2', note='rollback complete')
    record_manual_rollback(task_dir=task_dir, rollback_version='rb-runtime-timeout', executed_by='operator-runtime-c2', reason='rollback timeout validation')
    _force_observation_deadlines(task_dir, deadline_delta_minutes=-30, overdue_grace_minutes=5, timeout_grace_minutes=10)
    return {'task_id': task_dir.name}


def scenario_failed_followup_visible() -> dict:
    task_dir = _reset_task(f'{PREFIX}failed_followup')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-runtime-d', reason='failed observation follow-up')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='operator-runtime-d', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='operator-runtime-d', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-runtime-failed', executed_by='operator-runtime-d', summary='release failure validation')
    fail_observation_window(
        task_dir=task_dir,
        target='release',
        failed_by='observer-runtime-d',
        note='failure should enter pending follow-up aggregate',
        drift_findings=['drift_x'],
        mismatch_findings=['mismatch_y'],
        anomaly_findings=['anomaly_z'],
        signal_count=0,
    )
    return {'task_id': task_dir.name}


def scenario_release_followup_state_machine() -> dict:
    task_dir = _reset_task(f'{PREFIX}release_followup_state_machine')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-runtime-e', reason='release follow-up state machine')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='operator-runtime-e', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='operator-runtime-e', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-runtime-followup-release', executed_by='operator-runtime-e', summary='release follow-up state machine validation')
    fail_observation_window(task_dir=task_dir, target='release', failed_by='observer-runtime-e', note='release follow-up should become actionable', anomaly_findings=['anomaly_release'], signal_count=0)
    apply_followup_action(task_dir=task_dir, target='release', action='ack', acted_by='triage-release', note='ack release follow-up')
    apply_followup_action(task_dir=task_dir, target='release', action='start', acted_by='triage-release', note='start release follow-up')
    apply_followup_action(task_dir=task_dir, target='release', action='resolve', acted_by='triage-release', resolution_category='manual_intervention', resolution_summary='manual mitigation completed for release follow-up validation', note='resolve release follow-up')
    apply_followup_action(task_dir=task_dir, target='release', action='close', acted_by='triage-release', note='close release follow-up')
    return {'task_id': task_dir.name}


def scenario_rollback_followup_state_machine() -> dict:
    task_dir = _reset_task(f'{PREFIX}rollback_followup_state_machine')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-runtime-f', reason='rollback follow-up state machine')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='operator-runtime-f', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='operator-runtime-f', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-runtime-pre-rollback', executed_by='operator-runtime-f', summary='prepare rollback follow-up validation')
    confirm_execution(task_dir=task_dir, target='rollback', action='start', confirmed_by='operator-runtime-f2', note='rollback start')
    confirm_execution(task_dir=task_dir, target='rollback', action='complete', confirmed_by='operator-runtime-f2', note='rollback complete')
    record_manual_rollback(task_dir=task_dir, rollback_version='rb-runtime-followup', executed_by='operator-runtime-f2', reason='rollback follow-up validation')
    fail_observation_window(task_dir=task_dir, target='rollback', failed_by='observer-runtime-f', note='rollback follow-up should become actionable', anomaly_findings=['anomaly_rollback'], signal_count=0)
    apply_followup_action(task_dir=task_dir, target='rollback', action='ack', acted_by='triage-rollback', note='ack rollback follow-up')
    apply_followup_action(task_dir=task_dir, target='rollback', action='start', acted_by='triage-rollback', note='start rollback follow-up')
    return {'task_id': task_dir.name}


def main() -> int:
    fixtures = {
        'release_timeout': scenario_release_timeout_via_scheduler(),
        'completed_safe': scenario_completed_not_timed_out(),
        'rollback_timeout': scenario_rollback_timeout_via_scheduler(),
        'failed_followup': scenario_failed_followup_visible(),
        'release_followup_state_machine': scenario_release_followup_state_machine(),
        'rollback_followup_state_machine': scenario_rollback_followup_state_machine(),
    }
    summary = run_cycle(jobs_root=JOBS_ROOT, max_age_minutes=30, auto_retry=False, retry_requested_by='validate-observation-refresh-runtime', backfill_missing=True)

    release_timeout_snapshot = load_release_closure_snapshot(JOBS_ROOT / fixtures['release_timeout']['task_id'])
    completed_snapshot = load_release_closure_snapshot(JOBS_ROOT / fixtures['completed_safe']['task_id'])
    rollback_timeout_snapshot = load_release_closure_snapshot(JOBS_ROOT / fixtures['rollback_timeout']['task_id'])
    failed_snapshot = load_release_closure_snapshot(JOBS_ROOT / fixtures['failed_followup']['task_id'])
    release_followup_snapshot = load_release_closure_snapshot(JOBS_ROOT / fixtures['release_followup_state_machine']['task_id'])
    rollback_followup_snapshot = load_release_closure_snapshot(JOBS_ROOT / fixtures['rollback_followup_state_machine']['task_id'])
    latest_cycle = json.loads((ROOT / 'reports' / 'worker-runtime' / 'state' / 'latest_cycle.json').read_text(encoding='utf-8'))
    latest_stage_card = json.loads((ROOT / 'reports' / 'worker-runtime' / 'state' / 'latest_stage_card.json').read_text(encoding='utf-8'))
    followup_queue = ((latest_cycle.get('observation_runtime') or {}).get('followup_queue') or {})

    _assert(release_timeout_snapshot.get('post_execution_observation_state') == 'observation_timed_out', 'active release observation should auto-timeout during scheduler cycle refresh')
    _assert(rollback_timeout_snapshot.get('post_execution_observation_state') == 'observation_timed_out', 'active rollback observation should auto-timeout during scheduler cycle refresh')
    _assert(completed_snapshot.get('post_execution_observation_state') == 'observation_completed', 'completed observation must remain completed after scheduler refresh')
    _assert(completed_snapshot.get('post_execution_observation_is_timed_out') is False, 'completed observation must not be marked timed out by scheduler refresh')
    _assert(failed_snapshot.get('post_execution_observation_requires_manual_followup') is True, 'failed observation should require manual follow-up')
    _assert(failed_snapshot.get('post_execution_observation_escalation_level') == 'high', 'failed observation should be routed with high escalation')
    _assert(failed_snapshot.get('post_execution_observation_recommended_routing_target') in {'ops_monitor', 'coder', 'test-expert', 'human_operator'}, 'failed observation should expose a routing target')
    _assert(release_followup_snapshot.get('post_execution_observation_followup_item_state') == 'closed', 'release follow-up should reach closed state after ack/start/resolve/close')
    _assert(release_followup_snapshot.get('post_execution_observation_followup_terminal') is True, 'closed release follow-up should be terminal')
    _assert(rollback_followup_snapshot.get('post_execution_observation_followup_item_state') == 'in_progress', 'rollback follow-up should support ack/start transitions into in_progress')
    _assert(rollback_followup_snapshot.get('post_execution_observation_followup_item_open') is True, 'in_progress rollback follow-up should remain open')
    _assert(completed_snapshot.get('post_execution_observation_followup_item_state') in {None, 'not_required'}, 'completed_on_time observation must not create actionable follow-up item')
    _assert(latest_cycle.get('observation_pending_followup_count', 0) >= 3, 'latest_cycle should expose aggregated pending follow-up count')
    _assert(latest_cycle.get('followup_queue_count', 0) >= 3, 'latest_cycle should expose follow-up queue count')
    _assert((latest_cycle.get('followup_queue_escalation_counts') or {}).get('critical', 0) >= 2, 'latest_cycle should expose escalation counts for timeout observations')
    _assert((latest_cycle.get('top_pending_followup_items') or []), 'latest_cycle should expose top pending follow-up items')
    _assert(not any(item.get('task_id') == fixtures['release_followup_state_machine']['task_id'] for item in (latest_cycle.get('top_pending_followup_items') or [])), 'resolved/closed follow-up should not remain in top pending items')
    _assert(followup_queue.get('routing_target_counts', {}), 'latest_cycle observation runtime should expose routing target counts')
    _assert(latest_cycle.get('observation_timed_out_count', 0) >= 2, 'latest_cycle should expose aggregated timed_out count')
    _assert('latest_attention_observations' in latest_cycle and latest_cycle.get('latest_attention_observations'), 'latest_cycle should expose latest overdue/timed_out observations')
    stage_signals = (latest_stage_card.get('signals') or {})
    _assert(stage_signals.get('observation_pending_followup_count', 0) >= 3, 'stage card should expose observation pending follow-up count')
    _assert(stage_signals.get('observation_timed_out_count', 0) >= 2, 'stage card should expose observation timed_out count')
    _assert(stage_signals.get('followup_queue_count', 0) >= 3, 'stage card should expose follow-up queue count')
    _assert(stage_signals.get('followup_open_count', 0) >= 1, 'stage card should expose open follow-up count')
    _assert(stage_signals.get('followup_in_progress_count', 0) >= 1, 'stage card should expose in-progress follow-up count')
    _assert(stage_signals.get('followup_resolved_count', 0) >= 0, 'stage card should expose resolved follow-up count')
    _assert(stage_signals.get('followup_closed_count', 0) >= 1, 'stage card should expose closed follow-up count')
    _assert(stage_signals.get('followup_escalation_counts', {}), 'stage card should expose escalation counts')
    _assert(stage_signals.get('followup_routing_target_counts', {}), 'stage card should expose recommended routing targets')
    _assert(stage_signals.get('top_pending_followup_items', []), 'stage card should expose top pending follow-up items')
    _assert('latest_attention_observations' in stage_signals and stage_signals.get('latest_attention_observations'), 'stage card should expose latest attention observations')

    result = {
        'fixtures': fixtures,
        'release_timeout': {
            'state': release_timeout_snapshot.get('post_execution_observation_state'),
            'sla_state': release_timeout_snapshot.get('post_execution_observation_sla_state'),
            'requires_manual_followup': release_timeout_snapshot.get('post_execution_observation_requires_manual_followup'),
        },
        'completed_safe': {
            'state': completed_snapshot.get('post_execution_observation_state'),
            'sla_state': completed_snapshot.get('post_execution_observation_sla_state'),
            'timed_out': completed_snapshot.get('post_execution_observation_is_timed_out'),
        },
        'rollback_timeout': {
            'state': rollback_timeout_snapshot.get('post_execution_observation_state'),
            'sla_state': rollback_timeout_snapshot.get('post_execution_observation_sla_state'),
            'requires_manual_followup': rollback_timeout_snapshot.get('post_execution_observation_requires_manual_followup'),
        },
        'failed_followup': {
            'state': failed_snapshot.get('post_execution_observation_state'),
            'requires_manual_followup': failed_snapshot.get('post_execution_observation_requires_manual_followup'),
            'manual_followup_reason': failed_snapshot.get('post_execution_observation_manual_followup_reason'),
            'escalation_level': failed_snapshot.get('post_execution_observation_escalation_level'),
            'recommended_owner': failed_snapshot.get('post_execution_observation_recommended_owner'),
            'recommended_routing_target': failed_snapshot.get('post_execution_observation_recommended_routing_target'),
            'routing_targets': failed_snapshot.get('post_execution_observation_routing_targets'),
        },
        'release_followup_state_machine': {
            'state': release_followup_snapshot.get('post_execution_observation_followup_item_state'),
            'terminal': release_followup_snapshot.get('post_execution_observation_followup_terminal'),
            'last_action': release_followup_snapshot.get('post_execution_observation_followup_last_action'),
        },
        'rollback_followup_state_machine': {
            'state': rollback_followup_snapshot.get('post_execution_observation_followup_item_state'),
            'open': rollback_followup_snapshot.get('post_execution_observation_followup_item_open'),
            'last_action': rollback_followup_snapshot.get('post_execution_observation_followup_last_action'),
        },
        'latest_cycle_observation_runtime': latest_cycle.get('observation_runtime'),
        'latest_cycle_followup_queue': latest_cycle.get('observation_runtime', {}).get('followup_queue'),
        'latest_cycle_attention': latest_cycle.get('latest_attention_observations'),
        'stage_card_observation_signals': {
            'observation_active_count': stage_signals.get('observation_active_count'),
            'observation_pending_followup_count': stage_signals.get('observation_pending_followup_count'),
            'observation_timed_out_count': stage_signals.get('observation_timed_out_count'),
            'observation_overdue_count': stage_signals.get('observation_overdue_count'),
            'followup_open_count': stage_signals.get('followup_open_count'),
            'followup_in_progress_count': stage_signals.get('followup_in_progress_count'),
            'followup_resolved_count': stage_signals.get('followup_resolved_count'),
            'followup_closed_count': stage_signals.get('followup_closed_count'),
            'top_pending_followup_items': stage_signals.get('top_pending_followup_items'),
            'latest_attention_observations': stage_signals.get('latest_attention_observations'),
        },
        'cycle_id': summary.get('cycle_id'),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
