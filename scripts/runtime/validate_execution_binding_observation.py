#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from artifact_manager import ArtifactManager
from backfill_runtime import backfill_task
from execution_binding_runtime import collect_run_refs
from human_approval_runtime import record_human_approval
from manual_execution_confirmation_runtime import confirm_execution
from manual_release_registration_runtime import record_manual_release, record_manual_rollback
from post_execution_observation_runtime import complete_observation_window, fail_observation_window, refresh_observation_window
from release_closure_runtime import load_release_closure_snapshot
from task_queue import TaskQueue

ROOT = Path('/home/admin/.openclaw/workspace/master')
JOBS_ROOT = ROOT / 'traces' / 'jobs'
PREFIX = '_validation_execution_binding_'


def _reset_task(task_id: str) -> Path:
    task_dir = JOBS_ROOT / task_id
    if task_dir.exists():
        shutil.rmtree(task_dir)
    queue = TaskQueue(JOBS_ROOT)
    queue.create_task({
        'task_id': task_id,
        'role': 'doc-manager',
        'objective': f'validation task {task_id}',
        'constraints': ['manual approval required before execution', 'no automatic release', 'no automatic rollback'],
        'acceptance_criteria': ['formalization gate available', 'release closure artifacts available'],
        'downstream': 'knowledge-steward',
        'metadata': {'manual_review_required': False},
    })
    (task_dir / 'review.json').write_text(json.dumps({
        'decision': 'passed',
        'issues': [],
        'evidence': ['validation fixture'],
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    backfill_task(task_dir)
    manager = ArtifactManager(task_dir)
    rollback_stub = {
        'task_id': task_id,
        'rollback_supported': True,
        'rollback_artifacts': ['artifacts/official_release_record.json', 'artifacts/rollback_registration_record.json'],
        'official_release': False,
        'candidate_only': True,
        'note': 'validation fixture rollback stub',
    }
    manager.write_json('rollback_stub.json', rollback_stub)
    manager.write_json('rollback_registry_entry.json', {
        'task_id': task_id,
        'entry_type': 'candidate_stub',
        'official_release': False,
        'rollback_supported': True,
        'rollback_artifacts': rollback_stub['rollback_artifacts'],
        'formalization_state': 'release_ready_candidate',
        'note': 'validation fixture rollback registry',
    })
    manager.write_json('approval_checklist.json', {
        'task_id': task_id,
        'checklist_ready': True,
        'checks': [
            {'name': 'technical_validation_passed', 'passed': True},
            {'name': 'quality_gate_passed', 'passed': True},
            {'name': 'release_ready_candidate', 'passed': True},
            {'name': 'rollback_stub_present', 'passed': True},
            {'name': 'human_approval_pending', 'passed': True},
        ],
        'summary': 'validation fixture approval checklist ready',
    })
    manager.write_json('approval_outcome_stub.json', {
        'task_id': task_id,
        'approval_status': 'pending_human_approval',
        'approved': False,
        'requires_human_approval': True,
        'next_step': 'record_human_approval_decision',
        'note': 'validation fixture approval outcome ready',
    })
    manager.write_json('release_preflight_stub.json', {
        'task_id': task_id,
        'preflight_ready': True,
        'required_artifacts': [],
        'missing_artifacts': [],
        'next_step': 'request_human_approval',
        'note': 'validation fixture release preflight ready',
    })
    manager.write_json('pre_release_gate.json', {
        'task_id': task_id,
        'gate_state': 'ready_for_human_release_review',
        'pre_release_ready': True,
        'requires_human_approval': True,
        'approval_status': 'pending_human_approval',
        'formalization_state': 'release_ready_candidate',
        'rollback_supported': True,
        'release_preflight_ready': True,
        'summary': 'validation fixture pre-release gate ready',
    })
    manager.write_json('release_artifact_binding.json', {
        'task_id': task_id,
        'binding_ready': True,
        'release_artifacts': ['artifacts/formalization_gate.json', 'artifacts/release_readiness.json'],
        'rollback_artifacts': rollback_stub['rollback_artifacts'],
        'missing_release_artifacts': [],
        'missing_rollback_artifacts': [],
        'summary': 'validation fixture artifact binding ready',
    })
    return task_dir


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _validate_run_consistency(task_dir: Path, target: str) -> dict:
    refs = collect_run_refs(task_dir=task_dir, target=target)
    expected = refs['plan']
    for label in ('confirmation', 'status', 'registration', 'protocol'):
        if refs[label].get('run_id'):
            _assert(refs[label]['run_id'] == expected['run_id'], f'{target} {label} run_id mismatch')
            _assert(refs[label]['batch_id'] == expected['batch_id'], f'{target} {label} batch_id mismatch')
    if refs['observation'].get('run_id'):
        _assert(refs['observation']['run_id'] == expected['run_id'], f'{target} observation run_id mismatch')
        _assert(refs['observation']['batch_id'] == expected['batch_id'], f'{target} observation batch_id mismatch')
    return refs


def scenario_release_success() -> dict:
    task_dir = _reset_task(f'{PREFIX}release_success')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-a', reason='ready for manual release validation')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='operator-a', note='manual release started')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='operator-a', note='manual release completed')
    record_manual_release(task_dir=task_dir, release_version='v-validation-1', executed_by='operator-a', summary='manual release validation complete')
    complete_observation_window(task_dir=task_dir, target='release', completed_by='observer-a', note='release observation completed normally', signal_count=2)
    refresh_observation_window(task_dir=task_dir, target='release', refreshed_by='validator-a')
    snapshot = load_release_closure_snapshot(task_dir)
    refs = _validate_run_consistency(task_dir, 'release')
    _assert(snapshot.get('official_release_registered') is True, 'release should be registered')
    _assert(snapshot.get('post_execution_observation_state') == 'observation_completed', 'release observation should be completed')
    _assert(snapshot.get('post_execution_observation_completed') is True, 'release observation completed flag should be true')
    _assert(snapshot.get('post_execution_observation_failed') is False, 'release observation failed flag should stay false')
    _assert(snapshot.get('post_execution_observation_is_timed_out') is False, 'completed release observation must not be marked timed out')
    _assert(snapshot.get('post_execution_observation_sla_state') in {'completed_on_time', 'completed_late'}, 'completed release observation should expose completion SLA state')
    _assert(snapshot.get('post_execution_observation_summary_visible') is True, 'release observation summary should be visible')
    _assert(snapshot.get('release_observation_summary_visible') is True, 'release summary artifact should be visible')
    _assert(snapshot.get('current_run_id') == refs['plan']['run_id'], 'snapshot current_run_id should match release run_id')
    return {
        'task_id': task_dir.name,
        'batch_id': refs['plan']['batch_id'],
        'run_id': refs['plan']['run_id'],
        'observation_state': snapshot.get('post_execution_observation_state'),
        'sla_state': snapshot.get('post_execution_observation_sla_state'),
        'observation_completed': snapshot.get('post_execution_observation_completed'),
        'observation_summary_visible': snapshot.get('post_execution_observation_summary_visible'),
        'timed_out': snapshot.get('post_execution_observation_is_timed_out'),
        'anomaly_count': snapshot.get('post_execution_observation_anomaly_count'),
        'protocol_state': snapshot.get('release_execution_protocol_state'),
    }


def scenario_rollback_success() -> dict:
    task_dir = _reset_task(f'{PREFIX}rollback_success')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-b', reason='ready for release+rollback validation')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='operator-b', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='operator-b', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-validation-2', executed_by='operator-b', summary='release for rollback validation')
    confirm_execution(task_dir=task_dir, target='rollback', action='start', confirmed_by='operator-c', note='rollback start')
    confirm_execution(task_dir=task_dir, target='rollback', action='complete', confirmed_by='operator-c', note='rollback complete')
    record_manual_rollback(task_dir=task_dir, rollback_version='rb-validation-1', executed_by='operator-c', reason='rollback validation complete')
    complete_observation_window(task_dir=task_dir, target='rollback', completed_by='observer-b', note='rollback observation completed normally', signal_count=1)
    snapshot = load_release_closure_snapshot(task_dir)
    refs = _validate_run_consistency(task_dir, 'rollback')
    _assert(snapshot.get('rollback_registered') is True, 'rollback should be registered')
    _assert(snapshot.get('post_execution_observation_target') == 'rollback', 'observation target should switch to rollback')
    _assert(snapshot.get('post_execution_observation_state') == 'observation_completed', 'rollback observation should be completed')
    _assert(snapshot.get('post_execution_observation_completed') is True, 'rollback observation completed flag should be true')
    _assert(snapshot.get('post_execution_observation_summary_visible') is True, 'rollback observation summary should be visible')
    _assert(snapshot.get('rollback_observation_summary_visible') is True, 'rollback summary artifact should be visible')
    _assert(snapshot.get('post_execution_observation_history_count') == 2, 'rollback flow should expose aggregated observation history across release and rollback')
    _assert(snapshot.get('current_run_id') == refs['plan']['run_id'], 'snapshot current_run_id should match rollback run_id')
    return {
        'task_id': task_dir.name,
        'batch_id': refs['plan']['batch_id'],
        'run_id': refs['plan']['run_id'],
        'observation_state': snapshot.get('post_execution_observation_state'),
        'observation_completed': snapshot.get('post_execution_observation_completed'),
        'observation_summary_visible': snapshot.get('post_execution_observation_summary_visible'),
        'history_count': snapshot.get('post_execution_observation_history_count'),
        'latest_result': snapshot.get('post_execution_observation_latest_result'),
        'anomaly_count': snapshot.get('post_execution_observation_anomaly_count'),
        'protocol_state': snapshot.get('rollback_execution_protocol_state'),
    }



def scenario_release_timeout_history() -> dict:
    task_dir = _reset_task(f'{PREFIX}release_timeout_history')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-timeout', reason='ready for timeout validation')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='operator-timeout', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='operator-timeout', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-timeout-1', executed_by='operator-timeout', summary='release for timeout validation')

    observation_path = task_dir / 'artifacts' / 'post_execution_observation.json'
    observation = json.loads(observation_path.read_text(encoding='utf-8'))
    opened_at = datetime.fromisoformat(observation['opened_at'])
    deadline_at = opened_at - timedelta(minutes=30)
    overdue_at = deadline_at + timedelta(minutes=5)
    timeout_at = deadline_at + timedelta(minutes=10)
    observation.update({
        'deadline_at': deadline_at.isoformat(),
        'overdue_at': overdue_at.isoformat(),
        'timeout_at': timeout_at.isoformat(),
        'sla_seconds': -1800,
        'overdue_grace_seconds': 300,
        'timeout_grace_seconds': 600,
    })
    observation_path.write_text(json.dumps(observation, ensure_ascii=False, indent=2), encoding='utf-8')

    refresh_observation_window(task_dir=task_dir, target='release', refreshed_by='validator-timeout', note='force timeout for validation')
    snapshot = load_release_closure_snapshot(task_dir)
    history = json.loads((task_dir / 'artifacts' / 'observation_history_aggregate.json').read_text(encoding='utf-8'))
    followup = json.loads((task_dir / 'artifacts' / 'release_observation_followup_protocol.json').read_text(encoding='utf-8'))
    _assert(snapshot.get('post_execution_observation_state') == 'observation_timed_out', 'timeout scenario should finalize as observation_timed_out')
    _assert(snapshot.get('post_execution_observation_is_timed_out') is True, 'timeout scenario should expose timed out flag')
    _assert(snapshot.get('post_execution_observation_requires_manual_followup') is True, 'timeout scenario should require manual follow-up')
    _assert('observation_timed_out' in (snapshot.get('post_execution_observation_manual_followup_reason') or []), 'timeout scenario should expose standardized follow-up reason')
    _assert(history.get('history_count', 0) >= 1, 'history aggregate should be visible for timeout scenario')
    _assert(followup.get('action_count', 0) >= 2, 'timeout scenario should produce standardized follow-up actions')
    return {
        'task_id': task_dir.name,
        'observation_state': snapshot.get('post_execution_observation_state'),
        'sla_state': snapshot.get('post_execution_observation_sla_state'),
        'timed_out': snapshot.get('post_execution_observation_is_timed_out'),
        'requires_manual_followup': snapshot.get('post_execution_observation_requires_manual_followup'),
        'manual_followup_reason': snapshot.get('post_execution_observation_manual_followup_reason'),
        'history_count': history.get('history_count'),
        'latest_result': history.get('latest_observation_state'),
        'followup_action_count': followup.get('action_count'),
    }

def scenario_observation_failure() -> dict:
    task_dir = _reset_task(f'{PREFIX}observation_failure')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-c', reason='ready for observation failure validation')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='operator-d', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='complete', confirmed_by='operator-d', note='release complete')
    record_manual_release(task_dir=task_dir, release_version='v-validation-3', executed_by='operator-d', summary='release for observation failure validation')
    fail_observation_window(
        task_dir=task_dir,
        target='release',
        failed_by='observer-c',
        note='detected structural anomalies during observation',
        drift_findings=['metric_drift_placeholder'],
        mismatch_findings=['summary_vs_registration_version_mismatch_placeholder'],
        anomaly_findings=['health_signal_missing_placeholder', 'post_release_check_timeout_placeholder'],
        signal_count=5,
    )
    snapshot = load_release_closure_snapshot(task_dir)
    refs = _validate_run_consistency(task_dir, 'release')
    _assert(snapshot.get('official_release_registered') is True, 'registered release should remain registered')
    _assert(snapshot.get('post_execution_observation_state') == 'observation_failed', 'observation should be marked failed')
    _assert(snapshot.get('post_execution_observation_completed') is False, 'failed observation must not be marked completed')
    _assert(snapshot.get('post_execution_observation_failed') is True, 'failed observation flag should be true')
    _assert(snapshot.get('post_execution_observation_summary_visible') is True, 'failed observation should still produce summary')
    _assert(snapshot.get('post_execution_observation_anomaly_count') == 2, 'failed observation anomaly count should aggregate findings')
    _assert(snapshot.get('current_run_id') == refs['plan']['run_id'], 'snapshot current_run_id should match failed release run_id')
    return {
        'task_id': task_dir.name,
        'batch_id': refs['plan']['batch_id'],
        'run_id': refs['plan']['run_id'],
        'observation_state': snapshot.get('post_execution_observation_state'),
        'observation_completed': snapshot.get('post_execution_observation_completed'),
        'observation_failed': snapshot.get('post_execution_observation_failed'),
        'observation_summary_visible': snapshot.get('post_execution_observation_summary_visible'),
        'requires_manual_followup': snapshot.get('post_execution_observation_requires_manual_followup'),
        'manual_followup_reason': snapshot.get('post_execution_observation_manual_followup_reason'),
        'drift_count': snapshot.get('post_execution_observation_drift_count'),
        'mismatch_count': snapshot.get('post_execution_observation_mismatch_count'),
        'anomaly_count': snapshot.get('post_execution_observation_anomaly_count'),
        'protocol_state': snapshot.get('release_execution_protocol_state'),
    }


def scenario_unregistered_completion_guard() -> dict:
    task_dir = _reset_task(f'{PREFIX}unregistered_completion_guard')
    record_human_approval(task_dir=task_dir, decision='approve', approver='validator-d', reason='ready for unregistered completion guard validation')
    confirm_execution(task_dir=task_dir, target='release', action='start', confirmed_by='operator-e', note='release start')
    confirm_execution(task_dir=task_dir, target='release', action='abort', confirmed_by='operator-e', note='release aborted intentionally')
    error = ''
    try:
        complete_observation_window(task_dir=task_dir, target='release', completed_by='observer-d', note='should not be allowed before registration')
    except Exception as exc:
        error = str(exc)
    snapshot = load_release_closure_snapshot(task_dir)
    refs = collect_run_refs(task_dir=task_dir, target='release')
    _assert(error, 'completing observation before registration should fail')
    _assert(snapshot.get('official_release_registered') is False, 'aborted release must not be registered')
    _assert(snapshot.get('post_execution_observation_visible') is False, 'aborted release must not open observation')
    _assert(refs['registration'].get('run_id') is None, 'aborted release must not have registration run_id')
    return {
        'task_id': task_dir.name,
        'confirmation_state': snapshot.get('release_execution_confirmation_state'),
        'protocol_state': snapshot.get('release_execution_protocol_state'),
        'registered': snapshot.get('official_release_registered'),
        'observation_visible': snapshot.get('post_execution_observation_visible'),
        'completion_guard_error': error,
    }


def main() -> int:
    results = {
        'release_success': scenario_release_success(),
        'release_timeout_history': scenario_release_timeout_history(),
        'rollback_success': scenario_rollback_success(),
        'observation_failure': scenario_observation_failure(),
        'unregistered_completion_guard': scenario_unregistered_completion_guard(),
    }
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
