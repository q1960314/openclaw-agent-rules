#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal official-release registry helpers.

This layer does not perform real approval or release publication yet.
It only creates structured release-readiness and rollback-entry stubs so
candidate outputs are explicitly separated from future official releases.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from formalization_runtime import build_formalization_gate


CANDIDATE_ROLLBACK_ARTIFACTS = [
    'artifacts/diff.patch',
    'artifacts/changed_files.json',
    'artifacts/worktree_path.txt',
    'artifacts/result_envelope.json',
    'artifacts/delivery_note.md',
]


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _existing_artifacts(task_dir: str | Path, candidates: list[str]) -> list[str]:
    task_dir = Path(task_dir)
    existing: list[str] = []
    for item in candidates:
        if (task_dir / item).exists():
            existing.append(item)
    return existing


def build_release_readiness(task_dir: str | Path, *, boundary: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    task_dir = Path(task_dir)
    rollback_artifacts = _existing_artifacts(task_dir, CANDIDATE_ROLLBACK_ARTIFACTS)
    gate = build_formalization_gate(task_dir, boundary=boundary, review=review)
    return {
        'task_id': task_dir.name,
        'record_type': 'release_readiness',
        'result_tier': boundary.get('result_tier', 'candidate'),
        'approval_state': boundary.get('approval_state', 'technically_validated_candidate'),
        'official_release': False,
        'formalization_pending': True,
        'technical_validation_passed': gate['technical_validation_passed'],
        'requires_human_approval': gate['requires_human_approval'],
        'release_ready': gate['release_ready'],
        'formalization_state': gate['formalization_state'],
        'quality_score': gate.get('quality_score'),
        'quality_grade': gate.get('quality_grade'),
        'rollback_artifacts': rollback_artifacts,
        'note': 'This task is only release-readiness tracked. Human approval and an explicit official release step are still required.',
        'generated_at': _now(),
    }


def build_rollback_stub(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    rollback_artifacts = _existing_artifacts(task_dir, CANDIDATE_ROLLBACK_ARTIFACTS)
    return {
        'task_id': task_dir.name,
        'rollback_supported': bool(rollback_artifacts),
        'rollback_artifacts': rollback_artifacts,
        'official_release': False,
        'candidate_only': True,
        'note': 'Rollback entry is a candidate-level stub only. It identifies potential rollback artifacts but does not imply an official released version exists.',
    }


def build_official_release_stub(task_dir: str | Path, *, boundary: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    task_dir = Path(task_dir)
    readiness = build_release_readiness(task_dir, boundary=boundary, review=review)
    return {
        'task_id': task_dir.name,
        'record_type': 'official_release_stub',
        'result_tier': 'candidate',
        'approval_state': boundary.get('approval_state', 'technically_validated_candidate'),
        'official_release': False,
        'formalization_pending': True,
        'technical_validation_passed': readiness['technical_validation_passed'],
        'requires_human_approval': readiness['requires_human_approval'],
        'release_ready': readiness['release_ready'],
        'formalization_state': readiness.get('formalization_state'),
        'quality_score': readiness.get('quality_score'),
        'quality_grade': readiness.get('quality_grade'),
        'rollback_artifacts': readiness['rollback_artifacts'],
        'note': 'Official release stub created. No official release has been published yet; this is only a structured placeholder for future approval/release flow.',
        'generated_at': _now(),
    }
