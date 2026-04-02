#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from artifact_manager import ArtifactManager
from audit_manager import AuditManager
from execution_binding_runtime import ensure_execution_batch, extract_run_context_from_plan
from release_closure_runtime import _load_json

TARGET_CONFIG = {
    'release': {
        'label': 'official_release',
        'protocol_artifact': 'official_release_execution_protocol.json',
        'timeline_artifact': 'official_release_execution_timeline.json',
        'status_artifact': 'official_release_execution_status.json',
        'confirmation_artifact': 'official_release_execution_confirmation_record.json',
        'registration_artifact': 'official_release_record.json',
        'precheck_artifact': 'official_release_execution_precheck.json',
        'plan_artifact': 'official_release_execution_plan.json',
    },
    'rollback': {
        'label': 'rollback',
        'protocol_artifact': 'rollback_execution_protocol.json',
        'timeline_artifact': 'rollback_execution_timeline.json',
        'status_artifact': 'rollback_execution_status.json',
        'confirmation_artifact': 'rollback_execution_confirmation_record.json',
        'registration_artifact': 'rollback_registration_record.json',
        'precheck_artifact': 'rollback_execution_precheck.json',
        'plan_artifact': 'official_release_execution_plan.json',
    },
}


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _event(ts: str | None, stage: str, actor: str | None, state: str | None, detail: str, refs: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        'at': ts,
        'stage': stage,
        'actor': actor,
        'state': state,
        'detail': detail,
        'refs': refs or {},
    }


def _approval_event(human_approval_record: dict[str, Any], human_approval_result: dict[str, Any], run_context: dict[str, Any]) -> dict[str, Any] | None:
    ts = human_approval_record.get('decided_at') or human_approval_result.get('decided_at')
    if not ts:
        return None
    approved = human_approval_result.get('approved')
    return _event(
        ts,
        'approved_for_execution' if approved is True else 'rejected_before_execution',
        human_approval_record.get('decided_by') or human_approval_result.get('decided_by'),
        'approved' if approved is True else 'rejected',
        human_approval_record.get('decision_reason') or human_approval_result.get('decision_reason') or '',
        {
            'decision': human_approval_record.get('decision') or ('approve' if approved is True else 'reject' if approved is False else None),
            'decision_source': human_approval_result.get('decision_source'),
            'batch_id': run_context.get('batch_id'),
            'run_id': run_context.get('run_id'),
        },
    )


def _confirmation_events(target: str, status: dict[str, Any], confirmation_record: dict[str, Any], run_context: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    label = TARGET_CONFIG[target]['label']
    refs = {'action': 'start', 'batch_id': run_context.get('batch_id'), 'run_id': run_context.get('run_id')}
    if status.get('start_confirmed_at'):
        events.append(_event(
            status.get('start_confirmed_at'),
            'execution_started',
            status.get('start_confirmed_by'),
            'in_progress',
            f'{label} execution manually confirmed as started',
            refs,
        ))
    if confirmation_record.get('action') == 'complete':
        events.append(_event(
            status.get('completion_confirmed_at') or confirmation_record.get('confirmed_at'),
            'execution_completed',
            status.get('completion_confirmed_by') or confirmation_record.get('confirmed_by'),
            'completed',
            confirmation_record.get('note', ''),
            {'action': 'complete', 'batch_id': run_context.get('batch_id'), 'run_id': run_context.get('run_id')},
        ))
    elif confirmation_record.get('action') == 'fail':
        events.append(_event(
            status.get('failure_confirmed_at') or confirmation_record.get('confirmed_at'),
            'execution_failed',
            status.get('failure_confirmed_by') or confirmation_record.get('confirmed_by'),
            'failed',
            confirmation_record.get('note', ''),
            {'action': 'fail', 'batch_id': run_context.get('batch_id'), 'run_id': run_context.get('run_id')},
        ))
    elif confirmation_record.get('action') == 'abort':
        events.append(_event(
            status.get('abort_confirmed_at') or confirmation_record.get('confirmed_at'),
            'execution_aborted',
            status.get('abort_confirmed_by') or confirmation_record.get('confirmed_by'),
            'aborted',
            confirmation_record.get('note', ''),
            {'action': 'abort', 'batch_id': run_context.get('batch_id'), 'run_id': run_context.get('run_id')},
        ))
    return events


def _registration_event(target: str, registration_record: dict[str, Any], run_context: dict[str, Any]) -> dict[str, Any] | None:
    if not registration_record:
        return None
    stage = 'execution_registered' if target == 'release' else 'rollback_registered'
    detail = registration_record.get('summary') or registration_record.get('reason') or ''
    version_ref = registration_record.get('release_version') or registration_record.get('rollback_version')
    return _event(
        registration_record.get('executed_at'),
        stage,
        registration_record.get('executed_by'),
        registration_record.get('record_state'),
        detail,
        {
            'release_version': registration_record.get('release_version'),
            'rollback_version': registration_record.get('rollback_version'),
            'rolled_back_release_version': registration_record.get('rolled_back_release_version'),
            'version_ref': version_ref,
            'batch_id': run_context.get('batch_id'),
            'run_id': run_context.get('run_id'),
        },
    )


def _observation_event(target: str, observation: dict[str, Any], run_context: dict[str, Any]) -> dict[str, Any] | None:
    if not observation or observation.get('execution_target') != TARGET_CONFIG[target]['label']:
        return None
    state = observation.get('observation_state')
    if state == 'observing':
        at = observation.get('opened_at') or observation.get('generated_at')
        stage = 'post_execution_observation_opened'
        actor = observation.get('opened_by')
        detail = observation.get('note') or ''
    elif state == 'observation_failed':
        at = observation.get('closed_at') or observation.get('generated_at')
        stage = 'post_execution_observation_failed'
        actor = observation.get('closed_by')
        detail = observation.get('failure_reason') or observation.get('note') or ''
    else:
        at = observation.get('closed_at') or observation.get('generated_at')
        stage = 'post_execution_observation_completed'
        actor = observation.get('closed_by') or observation.get('opened_by')
        detail = observation.get('completion_note') or observation.get('note') or ''
    return _event(
        at,
        stage,
        actor,
        state,
        detail,
        {
            'batch_id': run_context.get('batch_id'),
            'run_id': run_context.get('run_id'),
            'observation_window_active': observation.get('observation_window_active'),
            'observation_completed': observation.get('observation_completed'),
            'observation_failed': observation.get('observation_failed'),
            'observation_summary_visible': observation.get('observation_summary_visible'),
            'observation_anomaly_count': observation.get('observation_anomaly_count'),
        },
    )


def _sort_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted([e for e in events if e.get('at')], key=lambda x: (x.get('at') or '', x.get('stage') or ''))


def _run_context_for_target(batch: dict[str, Any], plan: dict[str, Any], target: str) -> dict[str, Any]:
    from_plan = extract_run_context_from_plan(plan, target)
    return {
        'batch_id': from_plan.get('batch_id') or batch.get('batch_id'),
        'run_id': from_plan.get('run_id') or (batch.get('release_run_id') if target == 'release' else batch.get('rollback_run_id')),
        'release_run_id': from_plan.get('release_run_id') or batch.get('release_run_id'),
        'rollback_run_id': from_plan.get('rollback_run_id') or batch.get('rollback_run_id'),
    }


def _mismatch(expected: dict[str, Any], payload: dict[str, Any], label: str) -> str | None:
    if not payload:
        return None
    batch_id = payload.get('batch_id')
    run_id = payload.get('run_id')
    if batch_id and expected.get('batch_id') and batch_id != expected['batch_id']:
        return f'{label}.batch_id_mismatch'
    if run_id and expected.get('run_id') and run_id != expected['run_id']:
        return f'{label}.run_id_mismatch'
    return None


def sync_execution_protocol(task_dir: str | Path, *, target: str) -> dict[str, Any]:
    task_dir = Path(task_dir)
    artifacts_dir = task_dir / 'artifacts'
    cfg = TARGET_CONFIG[target]

    batch = ensure_execution_batch(task_dir)
    human_approval_record = _load_json(artifacts_dir / 'human_approval_record.json')
    human_approval_result = _load_json(artifacts_dir / 'human_approval_result_stub.json')
    precheck = _load_json(artifacts_dir / cfg['precheck_artifact'])
    plan = _load_json(artifacts_dir / cfg['plan_artifact'])
    status = _load_json(artifacts_dir / cfg['status_artifact'])
    confirmation_record = _load_json(artifacts_dir / cfg['confirmation_artifact'])
    registration_record = _load_json(artifacts_dir / cfg['registration_artifact'])
    observation = _load_json(artifacts_dir / 'post_execution_observation.json')
    release_record = _load_json(artifacts_dir / 'official_release_record.json')
    rollback_registry = _load_json(artifacts_dir / 'rollback_registry_entry.json')
    run_context = _run_context_for_target(batch, plan, target)

    events: list[dict[str, Any]] = []
    approval_evt = _approval_event(human_approval_record, human_approval_result, run_context)
    if approval_evt:
        events.append(approval_evt)
    events.extend(_confirmation_events(target, status, confirmation_record, run_context))
    reg_evt = _registration_event(target, registration_record, run_context)
    if reg_evt:
        events.append(reg_evt)
    obs_evt = _observation_event(target, observation, run_context)
    if obs_evt:
        events.append(obs_evt)
    timeline = _sort_events(events)

    latest_stage = timeline[-1]['stage'] if timeline else 'not_started'
    protocol_state = observation.get('observation_state') if obs_evt else (registration_record.get('record_state') or status.get('confirmation_state') or (approval_evt and approval_evt.get('state')) or 'not_started')
    registration_expected = status.get('confirmation_state') == 'completed' and not registration_record
    observation_expected = bool(registration_record) and not obs_evt

    consistency_errors = [
        err for err in [
            _mismatch(run_context, precheck, 'precheck'),
            _mismatch(run_context, status, 'status'),
            _mismatch(run_context, confirmation_record, 'confirmation'),
            _mismatch(run_context, registration_record, 'registration'),
            _mismatch(run_context, observation, 'observation') if observation.get('execution_target') == cfg['label'] else None,
        ] if err
    ]

    if target == 'release':
        version_ref = registration_record.get('release_version') or release_record.get('release_version') or rollback_registry.get('release_version')
        rollback_target_ref = rollback_registry.get('rollback_version') or rollback_registry.get('rollback_artifacts')
    else:
        version_ref = registration_record.get('rollback_version')
        rollback_target_ref = registration_record.get('rolled_back_release_version') or release_record.get('release_version')

    payload = {
        'task_id': task_dir.name,
        'record_type': 'execution_protocol',
        'execution_target': cfg['label'],
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'protocol_state': protocol_state,
        'latest_stage': latest_stage,
        'timeline_event_count': len(timeline),
        'timeline': timeline,
        'approved_for_execution_by': approval_evt.get('actor') if approval_evt else None,
        'approved_for_execution_at': approval_evt.get('at') if approval_evt else None,
        'execution_started_by': status.get('start_confirmed_by'),
        'execution_started_at': status.get('start_confirmed_at'),
        'execution_completed_by': status.get('completion_confirmed_by'),
        'execution_completed_at': status.get('completion_confirmed_at'),
        'execution_failed_by': status.get('failure_confirmed_by'),
        'execution_failed_at': status.get('failure_confirmed_at'),
        'execution_aborted_by': status.get('abort_confirmed_by'),
        'execution_aborted_at': status.get('abort_confirmed_at'),
        'execution_registered_by': registration_record.get('executed_by'),
        'execution_registered_at': registration_record.get('executed_at'),
        'observation_state': observation.get('observation_state') if observation.get('execution_target') == cfg['label'] else None,
        'observation_window_active': observation.get('observation_window_active') if observation.get('execution_target') == cfg['label'] else False,
        'observation_completed': observation.get('observation_completed') if observation.get('execution_target') == cfg['label'] else False,
        'observation_failed': observation.get('observation_failed') if observation.get('execution_target') == cfg['label'] else False,
        'observation_summary_visible': observation.get('observation_summary_visible') if observation.get('execution_target') == cfg['label'] else False,
        'observation_signal_count': observation.get('observation_signal_count') if observation.get('execution_target') == cfg['label'] else 0,
        'observation_drift_count': observation.get('observation_drift_count') if observation.get('execution_target') == cfg['label'] else 0,
        'observation_mismatch_count': observation.get('observation_mismatch_count') if observation.get('execution_target') == cfg['label'] else 0,
        'observation_anomaly_count': observation.get('observation_anomaly_count') if observation.get('execution_target') == cfg['label'] else 0,
        'observation_opened_at': observation.get('opened_at') if observation.get('execution_target') == cfg['label'] else None,
        'observation_closed_at': observation.get('closed_at') if observation.get('execution_target') == cfg['label'] else None,
        'plan_reference': cfg['plan_artifact'] if plan else None,
        'precheck_reference': cfg['precheck_artifact'] if precheck else None,
        'confirmation_reference': cfg['confirmation_artifact'] if confirmation_record else None,
        'registration_reference': cfg['registration_artifact'] if registration_record else None,
        'observation_reference': 'post_execution_observation.json' if observation.get('execution_target') == cfg['label'] else None,
        'observation_summary_reference': observation.get('summary_artifact') if observation.get('execution_target') == cfg['label'] and observation.get('observation_summary_visible') else None,
        'observation_audit_reference': observation.get('audit_artifact') if observation.get('execution_target') == cfg['label'] and observation.get('observation_summary_visible') else None,
        'plan_state': plan.get('plan_state'),
        'precheck_state': precheck.get('precheck_state'),
        'precheck_ready': precheck.get('precheck_ready'),
        'confirmation_state': status.get('confirmation_state'),
        'registration_state': registration_record.get('record_state'),
        'version_ref': version_ref,
        'rollback_target_ref': rollback_target_ref,
        'registration_expected': registration_expected,
        'observation_expected': observation_expected,
        'binding_consistent': len(consistency_errors) == 0,
        'binding_errors': consistency_errors,
        'auto_execution_enabled': False,
        'note': 'Execution protocol/audit chain only. This records approval, confirmation, registration, binding, and observation relationships without executing release or rollback automatically.',
        'generated_at': _now(),
    }
    timeline_payload = {
        'task_id': task_dir.name,
        'execution_target': cfg['label'],
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'event_count': len(timeline),
        'events': timeline,
        'generated_at': payload['generated_at'],
    }

    manager = ArtifactManager(task_dir)
    manager.write_json(cfg['protocol_artifact'], payload)
    manager.write_json(cfg['timeline_artifact'], timeline_payload)

    audit = AuditManager(task_dir)
    audit.append(
        'execution_protocol_synced',
        'system',
        execution_target=cfg['label'],
        batch_id=run_context['batch_id'],
        run_id=run_context['run_id'],
        protocol_state=protocol_state,
        latest_stage=latest_stage,
        timeline_event_count=len(timeline),
        registration_expected=registration_expected,
        observation_expected=observation_expected,
        binding_consistent=payload['binding_consistent'],
    )
    return payload


def sync_all_execution_protocols(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    release_payload = sync_execution_protocol(task_dir, target='release')
    rollback_payload = sync_execution_protocol(task_dir, target='rollback')
    summary = {
        'task_id': task_dir.name,
        'record_type': 'execution_audit_summary',
        'batch_id': release_payload.get('batch_id') or rollback_payload.get('batch_id'),
        'release_run_id': release_payload.get('run_id'),
        'rollback_run_id': rollback_payload.get('run_id'),
        'release_protocol_state': release_payload.get('protocol_state'),
        'rollback_protocol_state': rollback_payload.get('protocol_state'),
        'release_timeline_event_count': release_payload.get('timeline_event_count'),
        'rollback_timeline_event_count': rollback_payload.get('timeline_event_count'),
        'release_registration_expected': release_payload.get('registration_expected'),
        'rollback_registration_expected': rollback_payload.get('registration_expected'),
        'release_observation_expected': release_payload.get('observation_expected'),
        'rollback_observation_expected': rollback_payload.get('observation_expected'),
        'release_observation_state': release_payload.get('observation_state'),
        'rollback_observation_state': rollback_payload.get('observation_state'),
        'release_observation_completed': release_payload.get('observation_completed'),
        'rollback_observation_completed': rollback_payload.get('observation_completed'),
        'release_observation_failed': release_payload.get('observation_failed'),
        'rollback_observation_failed': rollback_payload.get('observation_failed'),
        'release_observation_summary_visible': release_payload.get('observation_summary_visible'),
        'rollback_observation_summary_visible': rollback_payload.get('observation_summary_visible'),
        'release_observation_anomaly_count': release_payload.get('observation_anomaly_count'),
        'rollback_observation_anomaly_count': rollback_payload.get('observation_anomaly_count'),
        'binding_consistent': bool(release_payload.get('binding_consistent')) and bool(rollback_payload.get('binding_consistent')),
        'generated_at': _now(),
        'note': 'Aggregated execution audit summary for closure/runtime visibility only.',
    }
    ArtifactManager(task_dir).write_json('execution_audit_summary.json', summary)
    return summary
