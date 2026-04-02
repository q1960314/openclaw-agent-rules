#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_release_closure_consistency(task_id: str, *, approval_record: dict[str, Any], approval_checklist: dict[str, Any], approval_outcome: dict[str, Any], release_action: dict[str, Any], release_preflight: dict[str, Any], pre_release_gate: dict[str, Any], rollback_registry: dict[str, Any]) -> dict[str, Any]:
    contradictions: list[str] = []

    approval_required = bool(approval_record.get('approval_required'))
    checklist_ready = bool(approval_checklist.get('checklist_ready'))
    approval_status = approval_outcome.get('approval_status')
    action_allowed = bool(release_action.get('action_allowed'))
    preflight_ready = bool(release_preflight.get('preflight_ready'))
    pre_release_ready = bool(pre_release_gate.get('pre_release_ready'))
    rollback_supported = bool(rollback_registry.get('rollback_supported'))
    gate_state = pre_release_gate.get('gate_state')

    if approval_status == 'pending_human_approval' and not checklist_ready:
        contradictions.append('approval_status_pending_but_checklist_not_ready')
    if pre_release_ready and not checklist_ready:
        contradictions.append('pre_release_ready_but_checklist_not_ready')
    if pre_release_ready and not preflight_ready:
        contradictions.append('pre_release_ready_but_preflight_not_ready')
    if pre_release_ready and not rollback_supported:
        contradictions.append('pre_release_ready_but_rollback_not_supported')
    if pre_release_ready and gate_state != 'ready_for_human_release_review':
        contradictions.append('pre_release_ready_but_gate_state_mismatch')
    if action_allowed and approval_required:
        contradictions.append('release_action_allowed_before_human_approval')
    if approval_status == 'not_ready_for_approval' and pre_release_ready:
        contradictions.append('approval_not_ready_but_pre_release_ready')

    return {
        'task_id': task_id,
        'consistency_ready': len(contradictions) == 0,
        'contradictions': contradictions,
        'summary': f"consistency_ready={len(contradictions) == 0} contradictions={len(contradictions)}",
    }


def load_closure_consistency_snapshot(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    path = task_dir / 'artifacts' / 'release_closure_consistency.json'
    if not path.exists():
        return {
            'closure_consistency_ready': None,
            'closure_contradiction_count': None,
        }
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {
            'closure_consistency_ready': None,
            'closure_contradiction_count': None,
        }
    return {
        'closure_consistency_ready': payload.get('consistency_ready'),
        'closure_contradiction_count': len(payload.get('contradictions', [])),
    }
