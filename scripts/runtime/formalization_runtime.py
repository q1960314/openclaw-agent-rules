#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from evaluation_runtime import load_quality_score


def build_formalization_gate(task_dir: str | Path, *, boundary: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    task_dir = Path(task_dir)
    quality = load_quality_score(task_dir)
    review_decision = review.get('decision')
    quality_score = quality.get('score')
    quality_grade = quality.get('grade')
    blocking_flags = quality.get('blocking_flags', []) if isinstance(quality, dict) else []
    manual_review_required = bool(boundary.get('manual_review_required', False)) or review_decision == 'manual_review_required'
    technical_validation_passed = review_decision == 'passed'
    quality_gate_passed = isinstance(quality_score, int) and quality_score >= 80 and quality_grade in {'A', 'B'} and not blocking_flags

    if not technical_validation_passed:
        state = 'blocked_candidate'
    elif manual_review_required:
        state = 'manual_review_gate'
    elif quality_gate_passed:
        state = 'release_ready_candidate'
    else:
        state = 'candidate_only'

    release_ready = state == 'release_ready_candidate'
    candidate_only = state in {'blocked_candidate', 'manual_review_gate', 'candidate_only'}
    requires_human_approval = state in {'manual_review_gate', 'candidate_only', 'release_ready_candidate'}
    stop_at_manual_gate = state == 'manual_review_gate'

    return {
        'task_id': task_dir.name,
        'formalization_state': state,
        'release_ready': release_ready,
        'candidate_only': candidate_only,
        'requires_human_approval': requires_human_approval,
        'stop_at_manual_gate': stop_at_manual_gate,
        'technical_validation_passed': technical_validation_passed,
        'quality_gate_passed': quality_gate_passed,
        'quality_score': quality_score,
        'quality_grade': quality_grade,
        'review_decision': review_decision,
        'approval_state': boundary.get('approval_state'),
        'summary': f'formalization_state={state} review_decision={review_decision} quality={quality_score}/{quality_grade}',
    }


def load_formalization_snapshot(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    path = task_dir / 'artifacts' / 'formalization_gate.json'
    if not path.exists():
        return {
            'formalization_state': None,
            'release_ready': None,
            'requires_human_approval': None,
        }
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {
            'formalization_state': None,
            'release_ready': None,
            'requires_human_approval': None,
        }
    return {
        'formalization_state': payload.get('formalization_state'),
        'release_ready': payload.get('release_ready'),
        'requires_human_approval': payload.get('requires_human_approval'),
    }
