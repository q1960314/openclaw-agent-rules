#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_approval_recompute_snapshot(task_id: str, *, human_approval_result: dict[str, Any], pre_release_gate: dict[str, Any], official_release_rehearsal: dict[str, Any], release_execution_guardrail: dict[str, Any], official_release_state: dict[str, Any]) -> dict[str, Any]:
    decision_recorded = bool(human_approval_result.get('decision_recorded'))
    approved = human_approval_result.get('approved')  # Don't use bool() to preserve None state
    pre_release_ready = bool(pre_release_gate.get('pre_release_ready'))
    rehearsal_ready = bool(official_release_rehearsal.get('rehearsal_ready'))
    guardrail_blocked = bool(release_execution_guardrail.get('execution_blocked'))

    if decision_recorded and approved is True:
        state = 'approved_recompute'
        would_unblock_execution = pre_release_ready and rehearsal_ready and not guardrail_blocked
        would_mark_official_release_ready = pre_release_ready and rehearsal_ready
        would_keep_candidate_blocked = not would_unblock_execution
        next_step = 'recompute_guardrails_and_proceed_if_all_clear' if would_unblock_execution else 'address_remaining_block_reasons'
    elif decision_recorded and approved is False:
        state = 'rejected_recompute'
        would_unblock_execution = False
        would_mark_official_release_ready = False
        would_keep_candidate_blocked = True
        next_step = 'keep_candidate_blocked_and_rework'
    elif not decision_recorded:  # When no decision has been recorded, approved should be None
        state = 'awaiting_real_human_decision'
        would_unblock_execution = False
        would_mark_official_release_ready = False
        would_keep_candidate_blocked = True
        next_step = 'wait_for_real_human_decision_then_recompute'
    else:
        # This case handles when decision is recorded but approved is None (invalid state)
        state = 'invalid_approval_state'
        would_unblock_execution = False
        would_mark_official_release_ready = False
        would_keep_candidate_blocked = True
        next_step = 'correct_approval_state_before_continuing'

    return {
        'task_id': task_id,
        'recompute_state': state,
        'would_unblock_execution': would_unblock_execution,
        'would_mark_official_release_ready': would_mark_official_release_ready,
        'would_keep_candidate_blocked': would_keep_candidate_blocked,
        'decision_recorded': decision_recorded,
        'approved': approved,  # Preserve the None/True/False distinction
        'next_step': next_step,
        'summary': f'recompute_state={state} would_unblock_execution={would_unblock_execution} official_release_state={official_release_state.get("official_release_state")}',
    }


def load_approval_recompute_snapshot(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    path = task_dir / 'artifacts' / 'approval_recompute_snapshot.json'
    if not path.exists():
        return {
            'approval_recompute_visible': None,
            'approval_recompute_would_unblock': None,
            'approval_recompute_official_ready': None,
        }
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {
            'approval_recompute_visible': None,
            'approval_recompute_would_unblock': None,
            'approval_recompute_official_ready': None,
        }
    return {
        'approval_recompute_visible': True,
        'approval_recompute_would_unblock': payload.get('would_unblock_execution'),
        'approval_recompute_official_ready': payload.get('would_mark_official_release_ready'),
    }
