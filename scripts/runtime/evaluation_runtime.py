#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal evaluation/scoring runtime for worker outputs.

Purpose:
- complement binary review with a structured quality score
- keep scoring deterministic and lightweight
- avoid pretending that a full benchmark suite already exists
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(value)))


def _grade(score: int) -> str:
    if score >= 90:
        return 'A'
    if score >= 80:
        return 'B'
    if score >= 70:
        return 'C'
    if score >= 60:
        return 'D'
    return 'F'


def _has_any(evidence: list[str], needles: list[str]) -> bool:
    joined = '\n'.join(evidence).lower()
    return any(needle.lower() in joined for needle in needles)


def load_quality_score(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    path = task_dir / 'artifacts' / 'quality_score.json'
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def quality_snapshot(task_dir: str | Path) -> dict[str, Any]:
    payload = load_quality_score(task_dir)
    if not payload:
        return {
            'quality_score': None,
            'quality_grade': None,
            'quality_summary': '',
            'quality_blocking_flags': [],
        }
    return {
        'quality_score': payload.get('score'),
        'quality_grade': payload.get('grade'),
        'quality_summary': payload.get('summary', ''),
        'quality_blocking_flags': payload.get('blocking_flags', []),
    }


def evaluate_quality(*, task_id: str, role: str, review_decision: str, issues: list[str] | None = None, evidence: list[str] | None = None, manual_review_required: bool = False) -> dict[str, Any]:
    issues = [str(x).strip() for x in (issues or []) if str(x).strip()]
    evidence = [str(x).strip() for x in (evidence or []) if str(x).strip()]

    missing_count = sum(1 for item in issues if 'missing:' in item or 'missing ' in item)
    schema_issue_count = sum(1 for item in issues if 'schema' in item.lower())
    empty_issue_count = sum(1 for item in issues if 'empty' in item.lower() or 'too short' in item.lower())

    artifact_completeness = 100 - (missing_count * 18) - (empty_issue_count * 8)
    structural_quality = 100 - (schema_issue_count * 20) - (len(issues) * 4)

    if review_decision == 'passed':
        validation_outcome = 100
    elif review_decision == 'manual_review_required':
        validation_outcome = 78
    else:
        validation_outcome = max(20, 75 - len(issues) * 8)

    schema_valid = _has_any(evidence, ['schema valid'])
    analysis_present = _has_any(evidence, ['analysis.json present', 'strategy_analysis.json present', 'parameter_analysis.json present', 'factor_analysis.json present'])
    release_readiness = 55
    if review_decision == 'passed':
        release_readiness += 15
    if schema_valid:
        release_readiness += 15
    if analysis_present:
        release_readiness += 10
    if manual_review_required:
        release_readiness -= 20
    if review_decision == 'rejected':
        release_readiness -= 25

    artifact_completeness = _clamp(artifact_completeness)
    structural_quality = _clamp(structural_quality)
    validation_outcome = _clamp(validation_outcome)
    release_readiness = _clamp(release_readiness)

    score = round((artifact_completeness * 0.30) + (structural_quality * 0.25) + (validation_outcome * 0.30) + (release_readiness * 0.15))
    score = _clamp(score)

    blocking_flags: list[str] = []
    if missing_count:
        blocking_flags.append('missing_artifacts')
    if schema_issue_count:
        blocking_flags.append('schema_invalid')
    if empty_issue_count:
        blocking_flags.append('empty_or_short_outputs')
    if review_decision == 'manual_review_required':
        blocking_flags.append('manual_approval_pending')
    if review_decision == 'rejected':
        blocking_flags.append('review_rejected')

    notes = [
        f'issues={len(issues)}',
        f'evidence_items={len(evidence)}',
        f'schema_valid={schema_valid}',
        f'analysis_present={analysis_present}',
    ]

    summary = f'{role} quality score={score} grade={_grade(score)} review_decision={review_decision}'
    return {
        'task_id': task_id,
        'role': role,
        'review_decision': review_decision,
        'score': score,
        'grade': _grade(score),
        'dimensions': {
            'artifact_completeness': artifact_completeness,
            'structural_quality': structural_quality,
            'validation_outcome': validation_outcome,
            'release_readiness': release_readiness,
        },
        'blocking_flags': blocking_flags,
        'summary': summary,
        'notes': notes,
    }
