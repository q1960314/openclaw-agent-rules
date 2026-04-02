#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_human_approval_input_slot(task_id: str, *, pre_release_gate: dict[str, Any], human_approval_result: dict[str, Any]) -> dict[str, Any]:
    input_recorded = bool(human_approval_result.get('decision_recorded'))
    slot_ready = bool(pre_release_gate.get('pre_release_ready'))
    decision_value = human_approval_result.get('approved')  # Keep as-is to preserve None state
    
    if input_recorded and decision_value is True:
        current_state = 'approved'
        next_step = 'recompute_closure_chain_after_real_human_approval'
    elif input_recorded and decision_value is False:
        current_state = 'rejected'
        next_step = 'recompute_closure_chain_after_real_human_rejection'
    elif input_recorded and decision_value is None:
        # Decision was recorded but value is undetermined (shouldn't normally happen)
        current_state = 'invalid_decision_recorded'
        next_step = 'correct_human_approval_result_record'
    elif slot_ready:
        current_state = 'awaiting'
        next_step = 'accept_human_approval_or_rejection_signal'
    else:
        current_state = 'not_ready_for_external_human_input'
        next_step = 'finish_pre_release_gate_before_requesting_human_input'
    
    return {
        'task_id': task_id,
        'slot_ready': slot_ready,
        'input_recorded': input_recorded,
        'decision_value': decision_value,  # Explicitly expose the decision value
        'accepted_decisions': ['approve', 'reject'],
        'current_state': current_state,
        'next_step': next_step,
        'note': 'Human approval input slot is a placeholder interface only. No real external approval input channel is connected yet.',
    }


def load_human_approval_input_snapshot(task_dir: str | Path) -> dict[str, Any]:
    task_dir = Path(task_dir)
    path = task_dir / 'artifacts' / 'human_approval_input_slot.json'
    if not path.exists():
        return {
            'human_approval_input_slot_visible': None,
            'human_approval_input_slot_ready': None,
            'human_approval_input_recorded': None,
        }
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {
            'human_approval_input_slot_visible': None,
            'human_approval_input_slot_ready': None,
            'human_approval_input_recorded': None,
        }
    return {
        'human_approval_input_slot_visible': True,
        'human_approval_input_slot_ready': payload.get('slot_ready'),
        'human_approval_input_recorded': payload.get('input_recorded'),
    }
