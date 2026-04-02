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
from execution_binding_runtime import ensure_execution_batch, get_execution_run_context
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


def build_official_release_execution_precheck(task_id: str, *, closure_snapshot: dict[str, Any], release_artifact_binding: dict[str, Any], rollback_registry: dict[str, Any], run_context: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []

    if not closure_snapshot.get('human_approval_result_recorded'):
        blockers.append('human_approval_not_recorded')
    elif closure_snapshot.get('human_approval_state') != 'approved':
        blockers.append('human_approval_not_approved')
    if not closure_snapshot.get('pre_release_ready'):
        blockers.append('pre_release_gate_not_ready')
    if not closure_snapshot.get('closure_consistency_ready'):
        blockers.append('closure_consistency_not_ready')
    if not closure_snapshot.get('official_release_rehearsal_ready'):
        blockers.append('official_release_rehearsal_not_ready')
    if not closure_snapshot.get('release_preflight_ready'):
        blockers.append('release_preflight_not_ready')
    if not release_artifact_binding.get('binding_ready'):
        blockers.append('release_artifact_binding_not_ready')
    if not rollback_registry.get('rollback_supported'):
        blockers.append('rollback_not_ready')
    blockers.extend([reason for reason in closure_snapshot.get('release_execution_block_reasons', []) or [] if reason not in blockers])

    precheck_ready = len(blockers) == 0
    return {
        'task_id': task_id,
        'execution_target': 'official_release',
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'precheck_state': 'ready_for_manual_release_execution' if precheck_ready else 'blocked',
        'precheck_ready': precheck_ready,
        'blockers': blockers,
        'blocker_count': len(blockers),
        'human_approval_state': closure_snapshot.get('human_approval_state'),
        'official_release_state': closure_snapshot.get('official_release_state'),
        'next_step': 'manual_release_execution_can_be_requested' if precheck_ready else 'fix_execution_precheck_blockers_before_any_release',
        'note': 'This precheck only confirms whether the execution path is ready to be manually triggered. It does not execute any official release action.',
        'generated_at': _now(),
    }


def build_rollback_execution_precheck(task_id: str, *, rollback_registry: dict[str, Any], release_artifact_binding: dict[str, Any], run_context: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if not rollback_registry.get('rollback_supported'):
        blockers.append('rollback_not_ready')
    missing = list(release_artifact_binding.get('missing_rollback_artifacts', []) or [])
    if missing:
        blockers.append('rollback_artifacts_missing')
    precheck_ready = len(blockers) == 0
    return {
        'task_id': task_id,
        'execution_target': 'rollback',
        'batch_id': run_context['batch_id'],
        'run_id': run_context['run_id'],
        'precheck_state': 'ready_for_manual_rollback_preparation' if precheck_ready else 'blocked',
        'precheck_ready': precheck_ready,
        'blockers': blockers,
        'missing_rollback_artifacts': missing,
        'rollback_artifacts': rollback_registry.get('rollback_artifacts', []),
        'next_step': 'manual_rollback_path_can_be_prepared' if precheck_ready else 'complete_rollback_precheck_requirements',
        'note': 'Rollback precheck confirms candidate-level rollback readiness only. It does not execute rollback.',
        'generated_at': _now(),
    }


def build_official_release_execution_plan(task_id: str, *, execution_precheck: dict[str, Any], rollback_precheck: dict[str, Any], closure_snapshot: dict[str, Any], batch_context: dict[str, Any]) -> dict[str, Any]:
    ready = bool(execution_precheck.get('precheck_ready'))
    paired_rollback_ready = bool(rollback_precheck.get('precheck_ready'))
    execution_blockers = list(execution_precheck.get('blockers', []) or [])
    rollback_blockers = list(rollback_precheck.get('blockers', []) or [])
    gate_snapshot = {
        'human_approval_state': closure_snapshot.get('human_approval_state'),
        'pre_release_ready': closure_snapshot.get('pre_release_ready'),
        'closure_consistency_ready': closure_snapshot.get('closure_consistency_ready'),
        'official_release_rehearsal_ready': closure_snapshot.get('official_release_rehearsal_ready'),
        'release_artifact_binding_ready': closure_snapshot.get('release_artifact_binding_ready'),
        'rollback_supported': closure_snapshot.get('rollback_supported'),
    }

    if ready:
        plan_state = 'manual_execution_plan_ready'
        steps = [
            '再次确认人工审批记录、审批人和审批原因已经固化',
            '复核正式发布前检查结果，确认审批/预演/产物绑定/回滚准备四组信号全部通过',
            '确认回滚预案与回滚产物已经成对准备，并可由人工随时接管',
            '由人工显式触发正式发布动作（当前系统仍不自动执行）',
            '发布后立即登记正式版本记录、执行留痕与回滚入口，并进入执行后观察窗口',
        ]
        next_step = 'wait_for_manual_release_trigger'
    else:
        plan_state = 'blocked'
        steps = [
            '先处理正式发布执行前检查阻塞项',
            '逐项核对 execution_blockers 与 rollback_blockers，确认卡点是否仍在审批/预演/绑定/回滚任一链路',
            '阻塞全部解除后再进入人工执行计划',
        ]
        next_step = 'fix_execution_precheck_blockers_before_any_release'

    return {
        'task_id': task_id,
        'plan_state': plan_state,
        'batch_id': batch_context['batch_id'],
        'run_id': batch_context['release_run_id'],
        'release_run_id': batch_context['release_run_id'],
        'rollback_run_id': batch_context['rollback_run_id'],
        'execution_precheck_ready': ready,
        'rollback_precheck_ready': paired_rollback_ready,
        'official_release_state': closure_snapshot.get('official_release_state'),
        'official_release_pipeline_state': closure_snapshot.get('official_release_pipeline_state'),
        'gate_snapshot': gate_snapshot,
        'execution_blockers': execution_blockers,
        'rollback_blockers': rollback_blockers,
        'steps': steps,
        'next_step': next_step,
        'note': 'This execution plan is manual-only. It exists to make the next human-controlled release/rollback step explicit without enabling automatic release.',
        'generated_at': _now(),
    }


def prepare_execution_path(*, task_dir: str | Path | None = None, task_id: str | None = None, jobs_root: str | Path = JOBS_ROOT) -> dict[str, Any]:
    resolved_task_dir = _resolve_task_dir(task_dir=task_dir, task_id=task_id, jobs_root=jobs_root)
    task_name = resolved_task_dir.name
    artifacts_dir = resolved_task_dir / 'artifacts'
    manager = ArtifactManager(resolved_task_dir)

    release_artifact_binding = _load_json(artifacts_dir / 'release_artifact_binding.json')
    rollback_registry = _load_json(artifacts_dir / 'rollback_registry_entry.json')
    closure_snapshot = load_release_closure_snapshot(resolved_task_dir)
    batch_context = ensure_execution_batch(resolved_task_dir)

    if not release_artifact_binding:
        raise FileNotFoundError('release_artifact_binding.json missing')
    if not rollback_registry:
        raise FileNotFoundError('rollback_registry_entry.json missing')

    execution_precheck = build_official_release_execution_precheck(
        task_name,
        closure_snapshot=closure_snapshot,
        release_artifact_binding=release_artifact_binding,
        rollback_registry=rollback_registry,
        run_context=get_execution_run_context(resolved_task_dir, 'release'),
    )
    rollback_precheck = build_rollback_execution_precheck(
        task_name,
        rollback_registry=rollback_registry,
        release_artifact_binding=release_artifact_binding,
        run_context=get_execution_run_context(resolved_task_dir, 'rollback'),
    )
    execution_plan = build_official_release_execution_plan(
        task_name,
        execution_precheck=execution_precheck,
        rollback_precheck=rollback_precheck,
        closure_snapshot=closure_snapshot,
        batch_context=batch_context,
    )

    manager.write_json('official_release_execution_precheck.json', execution_precheck)
    manager.write_json('rollback_execution_precheck.json', rollback_precheck)
    manager.write_json('official_release_execution_plan.json', execution_plan)
    manager.append_log(
        'official_release_execution_runtime.log',
        json.dumps(
            {
                'time': _now(),
                'task_id': task_name,
                'batch_id': execution_plan.get('batch_id'),
                'release_run_id': execution_plan.get('release_run_id'),
                'rollback_run_id': execution_plan.get('rollback_run_id'),
                'execution_precheck_ready': execution_precheck.get('precheck_ready'),
                'rollback_precheck_ready': rollback_precheck.get('precheck_ready'),
                'plan_state': execution_plan.get('plan_state'),
            },
            ensure_ascii=False,
        ),
    )

    return {
        'task_id': task_name,
        'batch_id': execution_plan.get('batch_id'),
        'release_run_id': execution_plan.get('release_run_id'),
        'rollback_run_id': execution_plan.get('rollback_run_id'),
        'execution_precheck_state': execution_precheck.get('precheck_state'),
        'execution_precheck_ready': execution_precheck.get('precheck_ready'),
        'execution_blockers': execution_precheck.get('blockers'),
        'rollback_precheck_state': rollback_precheck.get('precheck_state'),
        'rollback_precheck_ready': rollback_precheck.get('precheck_ready'),
        'rollback_blockers': rollback_precheck.get('blockers'),
        'plan_state': execution_plan.get('plan_state'),
        'next_step': execution_plan.get('next_step'),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)

    prepare_p = sub.add_parser('prepare-execution')
    prepare_p.add_argument('--task-dir', default='')
    prepare_p.add_argument('--task-id', default='')
    prepare_p.add_argument('--jobs-root', default=str(JOBS_ROOT))

    args = parser.parse_args()
    if args.action == 'prepare-execution':
        result = prepare_execution_path(
            task_dir=args.task_dir or None,
            task_id=args.task_id or None,
            jobs_root=args.jobs_root,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
