#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


def build_official_release_rehearsal(task_id: str, *, pre_release_gate: dict[str, Any], closure_consistency: dict[str, Any], approval_outcome: dict[str, Any], release_action: dict[str, Any]) -> dict[str, Any]:
    pre_release_ready = bool(pre_release_gate.get('pre_release_ready'))
    consistency_ready = bool(closure_consistency.get('consistency_ready'))
    approval_status = approval_outcome.get('approval_status')
    baseline_ready = pre_release_ready and consistency_ready

    if baseline_ready and approval_status == 'pending_human_approval':
        rehearsal_state = 'ready_for_rehearsal'
        rehearsal_ready = True
        next_step = 'record_human_approval_then_dry_run_release_checks'
    elif baseline_ready and approval_outcome.get('approved'):
        rehearsal_state = 'rehearsal_confirmed_after_approval'
        rehearsal_ready = True
        next_step = 'use_rehearsal_artifact_in_execution_precheck'
    elif approval_outcome.get('approved'):
        rehearsal_state = 'approved_but_prereq_regressed'
        rehearsal_ready = False
        next_step = 'restore_pre_release_gate_and_consistency_before_execution'
    else:
        rehearsal_state = 'not_eligible'
        rehearsal_ready = False
        next_step = release_action.get('next_step') or 'improve_candidate_before_release_rehearsal'

    rehearsal_findings = [
        {'name': 'pre_release_gate_ready', 'passed': pre_release_ready},
        {'name': 'closure_consistency_ready', 'passed': consistency_ready},
        {'name': 'approval_path_recorded', 'passed': approval_status in {'pending_human_approval', 'approved_by_human'}},
    ]

    return {
        'task_id': task_id,
        'rehearsal_state': rehearsal_state,
        'rehearsal_ready': rehearsal_ready,
        'official_release': False,
        'pre_release_ready': pre_release_ready,
        'closure_consistency_ready': consistency_ready,
        'approval_status': approval_status,
        'rehearsal_findings': rehearsal_findings,
        'next_step': next_step,
        'summary': f'rehearsal_state={rehearsal_state} pre_release_ready={pre_release_ready} consistency_ready={consistency_ready}',
    }
