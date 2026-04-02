#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any


def build_release_artifact_binding(task_id: str, task_dir: str | Path, *, rollback_stub: dict[str, Any]) -> dict[str, Any]:
    task_dir = Path(task_dir)
    release_artifacts = [
        'artifacts/formalization_gate.json',
        'artifacts/release_readiness.json',
        'artifacts/pre_release_gate.json',
        'artifacts/release_closure_consistency.json',
        'artifacts/official_release_rehearsal.json',
        'artifacts/release_execution_guardrail.json',
        'artifacts/official_release_state_placeholder.json',
        'artifacts/approval_recompute_snapshot.json',
    ]
    missing_release = [p for p in release_artifacts if not (task_dir / p).exists()]

    rollback_artifacts = list(rollback_stub.get('rollback_artifacts', []) or [])
    missing_rollback = [p for p in rollback_artifacts if not (task_dir / p).exists()]

    binding_ready = (not missing_release) and bool(rollback_artifacts) and (not missing_rollback)
    return {
        'task_id': task_id,
        'binding_ready': binding_ready,
        'release_artifacts': release_artifacts,
        'rollback_artifacts': rollback_artifacts,
        'missing_release_artifacts': missing_release,
        'missing_rollback_artifacts': missing_rollback,
        'summary': f'binding_ready={binding_ready} release_artifacts={len(release_artifacts)} rollback_artifacts={len(rollback_artifacts)}',
    }
