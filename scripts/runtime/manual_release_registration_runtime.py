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

from artifact_manager import ArtifactManager
from execution_binding_runtime import extract_run_context_from_plan, validate_run_context
from execution_protocol_runtime import sync_all_execution_protocols
from post_execution_observation_runtime import open_observation_window
from release_closure_runtime import _load_json, load_release_closure_snapshot

ROOT = Path('/home/admin/.openclaw/workspace/master')
JOBS_ROOT = ROOT / 'traces' / 'jobs'


def _now() -> str:
    return datetime.now().astimezone().isoformat()


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


def _load_required_artifacts(task_dir: Path) -> dict[str, dict[str, Any]]:
    artifacts_dir = task_dir / 'artifacts'
    required = {
        'release_artifact_binding': artifacts_dir / 'release_artifact_binding.json',
        'rollback_registry': artifacts_dir / 'rollback_registry_entry.json',
        'execution_precheck': artifacts_dir / 'official_release_execution_precheck.json',
        'rollback_precheck': artifacts_dir / 'rollback_execution_precheck.json',
        'execution_plan': artifacts_dir / 'official_release_execution_plan.json',
        'official_release_state': artifacts_dir / 'official_release_state_placeholder.json',
        'official_release_pipeline_summary': artifacts_dir / 'official_release_pipeline_summary.json',
    }
    payloads: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for key, path in required.items():
        payload = _load_json(path)
        if not payload:
            missing.append(path.name)
        payloads[key] = payload
    if missing:
        raise FileNotFoundError(f'missing required artifacts: {missing}')
    return payloads


def _build_official_release_record(*, task_id: str, version: str, executed_by: str, summary: str, closure_snapshot: dict[str, Any], release_artifact_binding: dict[str, Any], rollback_registry: dict[str, Any], run_context: dict[str, Any]) -> dict[str, Any]:
    return {
        'task_id': task_id,
        'record_type': 'official_release_registration',
        'record_state': 'official_release_registered',
        'official_release': True,
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'release_version': version,
        'executed_by': executed_by,
        'executed_at': _now(),
        'execution_source': 'manual_execution_recorded_only',
        'summary': summary,
        'gate_snapshot': {
            'human_approval_state': closure_snapshot.get('human_approval_state'),
            'pre_release_ready': closure_snapshot.get('pre_release_ready'),
            'closure_consistency_ready': closure_snapshot.get('closure_consistency_ready'),
            'official_release_rehearsal_ready': closure_snapshot.get('official_release_rehearsal_ready'),
            'release_preflight_ready': closure_snapshot.get('release_preflight_ready'),
            'release_execution_state': closure_snapshot.get('release_execution_state'),
        },
        'release_artifacts': list(release_artifact_binding.get('release_artifacts', []) or []),
        'rollback_artifacts': list(rollback_registry.get('rollback_artifacts', []) or []),
        'note': 'This artifact only registers that a human has already executed the official release outside the automation path. It does not perform release execution.',
    }


def _build_official_release_state_registered(*, task_id: str, release_record: dict[str, Any]) -> dict[str, Any]:
    return {
        'task_id': task_id,
        'official_release_state': 'official_release_registered',
        'official_release': True,
        'current_execution_batch_id': release_record.get('batch_id'),
        'current_execution_run_id': release_record.get('run_id'),
        'release_version': release_record.get('release_version'),
        'executed_by': release_record.get('executed_by'),
        'executed_at': release_record.get('executed_at'),
        'next_step': 'wait_for_post_release_observation_or_manual_rollback_registration',
        'note': 'Official release has been manually registered as already executed by a human. The system still does not perform release execution automatically.',
    }


def _build_pipeline_summary_registered(*, task_id: str, closure_snapshot: dict[str, Any], release_record: dict[str, Any]) -> dict[str, Any]:
    return {
        'task_id': task_id,
        'pipeline_state': 'official_release_registered',
        'batch_id': release_record.get('batch_id'),
        'run_id': release_record.get('run_id'),
        'official_release_executable': False,
        'ready_signals': {
            'pre_release_ready': bool(closure_snapshot.get('pre_release_ready')),
            'rehearsal_ready': bool(closure_snapshot.get('official_release_rehearsal_ready')),
            'artifact_binding_ready': bool(closure_snapshot.get('release_artifact_binding_ready')),
            'rollback_supported': bool(closure_snapshot.get('rollback_supported')),
            'human_decision_recorded': bool(closure_snapshot.get('human_approval_result_recorded')),
            'human_approved': closure_snapshot.get('human_approval_state') == 'approved',
            'manual_release_registered': True,
            'manual_rollback_registered': False,
        },
        'blockers': [],
        'blocker_count': 0,
        'official_release_state': 'official_release_registered',
        'next_step': 'wait_for_post_release_observation_or_manual_rollback_registration',
        'note': f"Manual release registration recorded for version {release_record.get('release_version')}. This updates closure visibility only and does not execute release.",
    }


def _build_rollback_registry_for_release(*, rollback_registry: dict[str, Any], release_record: dict[str, Any]) -> dict[str, Any]:
    updated = dict(rollback_registry)
    updated.update({
        'entry_type': 'official_release_stub',
        'official_release': True,
        'batch_id': release_record.get('batch_id'),
        'run_id': release_record.get('run_id'),
        'release_version': release_record.get('release_version'),
        'release_registered': True,
        'release_registered_at': release_record.get('executed_at'),
        'release_registered_by': release_record.get('executed_by'),
        'note': 'Rollback registry has been upgraded from candidate stub to registered official release rollback entry. This still records state only and does not execute rollback.',
    })
    return updated


def record_manual_release(*, task_dir: str | Path | None = None, task_id: str | None = None, release_version: str, executed_by: str = 'human', summary: str = '', jobs_root: str | Path = JOBS_ROOT) -> dict[str, Any]:
    resolved_task_dir = _resolve_task_dir(task_dir=task_dir, task_id=task_id, jobs_root=jobs_root)
    task_name = resolved_task_dir.name
    manager = ArtifactManager(resolved_task_dir)
    closure_snapshot = load_release_closure_snapshot(resolved_task_dir)

    if closure_snapshot.get('human_approval_state') != 'approved':
        raise ValueError('manual release registration requires an approved human decision')

    payloads = _load_required_artifacts(resolved_task_dir)
    run_context = extract_run_context_from_plan(payloads['execution_plan'], 'release')
    validate_run_context(expected=run_context, candidate={'batch_id': payloads['execution_precheck'].get('batch_id'), 'run_id': payloads['execution_precheck'].get('run_id')}, label='release precheck')
    validate_run_context(expected=run_context, candidate={'batch_id': _load_json(resolved_task_dir / 'artifacts' / 'official_release_execution_status.json').get('batch_id'), 'run_id': _load_json(resolved_task_dir / 'artifacts' / 'official_release_execution_status.json').get('run_id')}, label='release execution status')
    if not payloads['execution_precheck'].get('precheck_ready'):
        raise ValueError('manual release registration requires official_release_execution_precheck.json to be ready')
    if closure_snapshot.get('release_execution_confirmation_state') != 'completed':
        raise ValueError('manual release registration requires completed official release execution confirmation')
    if closure_snapshot.get('official_release_registered'):
        raise ValueError('official release already registered for this task')
    if closure_snapshot.get('rollback_registered'):
        raise ValueError('rollback already registered; cannot register release afterwards on the same task')

    release_record = _build_official_release_record(task_id=task_name, version=release_version, executed_by=executed_by, summary=summary, closure_snapshot=closure_snapshot, release_artifact_binding=payloads['release_artifact_binding'], rollback_registry=payloads['rollback_registry'], run_context=run_context)
    official_release_state = _build_official_release_state_registered(task_id=task_name, release_record=release_record)
    official_release_pipeline_summary = _build_pipeline_summary_registered(task_id=task_name, closure_snapshot=closure_snapshot, release_record=release_record)
    rollback_registry = _build_rollback_registry_for_release(rollback_registry=payloads['rollback_registry'], release_record=release_record)
    post_execution_status = {
        'task_id': task_name,
        'status_type': 'post_release_registration',
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'release_registered': True,
        'rollback_registered': False,
        'official_release_state': official_release_state.get('official_release_state'),
        'official_release_pipeline_state': official_release_pipeline_summary.get('pipeline_state'),
        'release_version': release_record.get('release_version'),
        'next_step': 'wait_for_post_release_observation_or_manual_rollback_registration',
        'generated_at': _now(),
    }

    manager.write_json('official_release_record.json', release_record)
    manager.write_json('official_release_state_placeholder.json', official_release_state)
    manager.write_json('official_release_pipeline_summary.json', official_release_pipeline_summary)
    manager.write_json('rollback_registry_entry.json', rollback_registry)
    manager.write_json('post_release_registration_status.json', post_execution_status)
    manager.append_log('manual_release_registration_runtime.log', json.dumps({'time': _now(), 'task_id': task_name, 'batch_id': run_context['batch_id'], 'run_id': run_context['run_id'], 'release_version': release_version, 'executed_by': executed_by, 'summary': summary}, ensure_ascii=False))
    observation = open_observation_window(task_dir=resolved_task_dir, target='release', observed_by=executed_by, note='Release registration completed; post-execution observation window opened.')
    sync_all_execution_protocols(resolved_task_dir)

    refreshed = load_release_closure_snapshot(resolved_task_dir)
    return {
        'task_id': task_name,
        'record_state': release_record.get('record_state'),
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'release_version': release_record.get('release_version'),
        'official_release_state': refreshed.get('official_release_state'),
        'official_release_pipeline_state': refreshed.get('official_release_pipeline_state'),
        'official_release_registered': refreshed.get('official_release_registered'),
        'rollback_registered': refreshed.get('rollback_registered'),
        'observation_state': observation.get('observation_state'),
        'next_step': post_execution_status.get('next_step'),
    }


def _build_rollback_record(*, task_id: str, release_record: dict[str, Any], rollback_version: str, executed_by: str, reason: str, closure_snapshot: dict[str, Any], run_context: dict[str, Any]) -> dict[str, Any]:
    return {
        'task_id': task_id,
        'record_type': 'manual_rollback_registration',
        'record_state': 'rollback_registered',
        'official_release': False,
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'rollback_version': rollback_version,
        'rolled_back_release_version': release_record.get('release_version'),
        'executed_by': executed_by,
        'executed_at': _now(),
        'execution_source': 'manual_rollback_recorded_only',
        'reason': reason,
        'gate_snapshot': {
            'human_approval_state': closure_snapshot.get('human_approval_state'),
            'rollback_supported': closure_snapshot.get('rollback_supported'),
            'release_execution_state': closure_snapshot.get('release_execution_state'),
        },
        'note': 'This artifact only registers that a human has already executed rollback outside the automation path. It does not perform rollback execution.',
    }


def _build_official_release_state_rolled_back(*, task_id: str, release_record: dict[str, Any], rollback_record: dict[str, Any]) -> dict[str, Any]:
    return {
        'task_id': task_id,
        'official_release_state': 'rollback_registered',
        'official_release': False,
        'current_execution_batch_id': rollback_record.get('batch_id'),
        'current_execution_run_id': rollback_record.get('run_id'),
        'release_version': release_record.get('release_version'),
        'rollback_version': rollback_record.get('rollback_version'),
        'executed_by': rollback_record.get('executed_by'),
        'executed_at': rollback_record.get('executed_at'),
        'next_step': 'official_release_closed_with_registered_rollback_and_observation',
        'note': 'Rollback has been manually registered as already executed by a human. The system still does not perform rollback automatically.',
    }


def _build_pipeline_summary_rolled_back(*, task_id: str, closure_snapshot: dict[str, Any], release_record: dict[str, Any], rollback_record: dict[str, Any]) -> dict[str, Any]:
    return {
        'task_id': task_id,
        'pipeline_state': 'rollback_registered',
        'batch_id': rollback_record.get('batch_id'),
        'run_id': rollback_record.get('run_id'),
        'official_release_executable': False,
        'ready_signals': {
            'pre_release_ready': bool(closure_snapshot.get('pre_release_ready')),
            'rehearsal_ready': bool(closure_snapshot.get('official_release_rehearsal_ready')),
            'artifact_binding_ready': bool(closure_snapshot.get('release_artifact_binding_ready')),
            'rollback_supported': bool(closure_snapshot.get('rollback_supported')),
            'human_decision_recorded': bool(closure_snapshot.get('human_approval_result_recorded')),
            'human_approved': closure_snapshot.get('human_approval_state') == 'approved',
            'manual_release_registered': True,
            'manual_rollback_registered': True,
        },
        'blockers': [],
        'blocker_count': 0,
        'official_release_state': 'rollback_registered',
        'next_step': 'official_release_closed_with_registered_rollback_and_observation',
        'note': f"Manual rollback registration recorded for release {release_record.get('release_version')} -> rollback {rollback_record.get('rollback_version')}. This updates closure visibility only and does not execute rollback.",
    }


def _build_rollback_registry_after_rollback(*, rollback_registry: dict[str, Any], release_record: dict[str, Any], rollback_record: dict[str, Any]) -> dict[str, Any]:
    updated = dict(rollback_registry)
    updated.update({
        'entry_type': 'official_release_stub',
        'official_release': False,
        'batch_id': rollback_record.get('batch_id'),
        'run_id': rollback_record.get('run_id'),
        'release_version': release_record.get('release_version'),
        'release_registered': True,
        'rollback_registered': True,
        'rollback_registered_at': rollback_record.get('executed_at'),
        'rollback_registered_by': rollback_record.get('executed_by'),
        'rollback_version': rollback_record.get('rollback_version'),
        'note': 'Rollback registry now records both the registered official release and the subsequent registered manual rollback. This remains state registration only.',
    })
    return updated


def record_manual_rollback(*, task_dir: str | Path | None = None, task_id: str | None = None, rollback_version: str, executed_by: str = 'human', reason: str = '', jobs_root: str | Path = JOBS_ROOT) -> dict[str, Any]:
    resolved_task_dir = _resolve_task_dir(task_dir=task_dir, task_id=task_id, jobs_root=jobs_root)
    task_name = resolved_task_dir.name
    manager = ArtifactManager(resolved_task_dir)
    closure_snapshot = load_release_closure_snapshot(resolved_task_dir)
    release_record = _load_json(resolved_task_dir / 'artifacts' / 'official_release_record.json')

    if closure_snapshot.get('human_approval_state') != 'approved':
        raise ValueError('manual rollback registration requires an approved human decision')

    payloads = _load_required_artifacts(resolved_task_dir)
    run_context = extract_run_context_from_plan(payloads['execution_plan'], 'rollback')
    validate_run_context(expected=run_context, candidate={'batch_id': payloads['rollback_precheck'].get('batch_id'), 'run_id': payloads['rollback_precheck'].get('run_id')}, label='rollback precheck')
    validate_run_context(expected=run_context, candidate={'batch_id': _load_json(resolved_task_dir / 'artifacts' / 'rollback_execution_status.json').get('batch_id'), 'run_id': _load_json(resolved_task_dir / 'artifacts' / 'rollback_execution_status.json').get('run_id')}, label='rollback execution status')
    if not payloads['rollback_precheck'].get('precheck_ready'):
        raise ValueError('manual rollback registration requires rollback_execution_precheck.json to be ready')
    if closure_snapshot.get('rollback_execution_confirmation_state') != 'completed':
        raise ValueError('manual rollback registration requires completed rollback execution confirmation')
    if not release_record:
        raise ValueError('manual rollback registration requires a prior official_release_record.json')
    if closure_snapshot.get('rollback_registered'):
        raise ValueError('rollback already registered for this task')

    rollback_record = _build_rollback_record(task_id=task_name, release_record=release_record, rollback_version=rollback_version, executed_by=executed_by, reason=reason, closure_snapshot=closure_snapshot, run_context=run_context)
    official_release_state = _build_official_release_state_rolled_back(task_id=task_name, release_record=release_record, rollback_record=rollback_record)
    official_release_pipeline_summary = _build_pipeline_summary_rolled_back(task_id=task_name, closure_snapshot=closure_snapshot, release_record=release_record, rollback_record=rollback_record)
    rollback_registry = _build_rollback_registry_after_rollback(rollback_registry=payloads['rollback_registry'], release_record=release_record, rollback_record=rollback_record)
    post_execution_status = {
        'task_id': task_name,
        'status_type': 'post_rollback_registration',
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'release_registered': True,
        'rollback_registered': True,
        'official_release_state': official_release_state.get('official_release_state'),
        'official_release_pipeline_state': official_release_pipeline_summary.get('pipeline_state'),
        'release_version': release_record.get('release_version'),
        'rollback_version': rollback_record.get('rollback_version'),
        'next_step': 'official_release_closed_with_registered_rollback_and_observation',
        'generated_at': _now(),
    }

    manager.write_json('rollback_registration_record.json', rollback_record)
    manager.write_json('official_release_state_placeholder.json', official_release_state)
    manager.write_json('official_release_pipeline_summary.json', official_release_pipeline_summary)
    manager.write_json('rollback_registry_entry.json', rollback_registry)
    manager.write_json('post_rollback_registration_status.json', post_execution_status)
    manager.append_log('manual_release_registration_runtime.log', json.dumps({'time': _now(), 'task_id': task_name, 'batch_id': run_context['batch_id'], 'run_id': run_context['run_id'], 'rollback_version': rollback_version, 'executed_by': executed_by, 'reason': reason}, ensure_ascii=False))
    observation = open_observation_window(task_dir=resolved_task_dir, target='rollback', observed_by=executed_by, note='Rollback registration completed; post-execution observation window opened.')
    sync_all_execution_protocols(resolved_task_dir)

    refreshed = load_release_closure_snapshot(resolved_task_dir)
    return {
        'task_id': task_name,
        'record_state': rollback_record.get('record_state'),
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'rollback_version': rollback_record.get('rollback_version'),
        'rolled_back_release_version': rollback_record.get('rolled_back_release_version'),
        'official_release_state': refreshed.get('official_release_state'),
        'official_release_pipeline_state': refreshed.get('official_release_pipeline_state'),
        'official_release_registered': refreshed.get('official_release_registered'),
        'rollback_registered': refreshed.get('rollback_registered'),
        'observation_state': observation.get('observation_state'),
        'next_step': post_execution_status.get('next_step'),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)

    release_p = sub.add_parser('record-manual-release')
    release_p.add_argument('--task-dir', default='')
    release_p.add_argument('--task-id', default='')
    release_p.add_argument('--jobs-root', default=str(JOBS_ROOT))
    release_p.add_argument('--release-version', required=True)
    release_p.add_argument('--executed-by', default='human')
    release_p.add_argument('--summary', default='')

    rollback_p = sub.add_parser('record-manual-rollback')
    rollback_p.add_argument('--task-dir', default='')
    rollback_p.add_argument('--task-id', default='')
    rollback_p.add_argument('--jobs-root', default=str(JOBS_ROOT))
    rollback_p.add_argument('--rollback-version', required=True)
    rollback_p.add_argument('--executed-by', default='human')
    rollback_p.add_argument('--reason', default='')

    args = parser.parse_args()
    if args.action == 'record-manual-release':
        result = record_manual_release(task_dir=args.task_dir or None, task_id=args.task_id or None, jobs_root=args.jobs_root, release_version=args.release_version, executed_by=args.executed_by, summary=args.summary)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.action == 'record-manual-rollback':
        result = record_manual_rollback(task_dir=args.task_dir or None, task_id=args.task_id or None, jobs_root=args.jobs_root, rollback_version=args.rollback_version, executed_by=args.executed_by, reason=args.reason)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
